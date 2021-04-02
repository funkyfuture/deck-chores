import json
import logging
import os
import sys
from datetime import datetime, timedelta
from signal import signal, SIGINT, SIGTERM, SIGUSR1
from typing import Optional

from apscheduler.schedulers import SchedulerNotRunningError
from docker.models.containers import Container
from fasteners import InterProcessLock

from deck_chores import __version__, jobs
from deck_chores.config import cfg, generate_config, ConfigurationError
from deck_chores.indexes import (
    container_name,
    lock_service,
    reassign_service_lock,
    unlock_service,
    service_locks_by_service_id,
    service_locks_by_container_id,
)
from deck_chores.parsers import job_config_validator, parse_labels
from deck_chores.utils import DEBUG, log, log_handler


####


lock = InterProcessLock('/tmp/deck-chores.lock')


def there_is_another_deck_chores_container() -> bool:
    matched_containers = 0
    for container in cfg.client.containers.list(ignore_removed=True, sparse=True):
        if container.image.labels.get('org.label-schema.name', '') == 'deck-chores':
            matched_containers += 1
        if matched_containers > 1:
            return True

    return False


####


def sigint_handler(signum, frame):  # pragma: nocover
    log.info("Keyboard interrupt.")
    raise SystemExit(0)


def sigterm_handler(signum, frame):  # pragma: nocover
    log.info("Received SIGTERM.")
    raise SystemExit(0)


def sigusr1_handler(signum, frame):
    log.info("SIGUSR1 received, echoing all jobs.")
    for job in jobs.scheduler.get_jobs():
        log.info(f"ID: {job.id}   Next execution: {job.next_run_time}   Configuration:")
        log.info(job.kwargs)


signal(SIGINT, sigint_handler)
signal(SIGTERM, sigterm_handler)
signal(SIGUSR1, sigusr1_handler)


####


def process_started_container_labels(container_id: str, paused: bool = False) -> None:
    service_id, flags, definitions = parse_labels(container_id)

    if not definitions:
        return

    if service_id and 'service' in flags:
        other_container_id = service_locks_by_service_id.get(service_id)
        if other_container_id:
            log.debug(
                f'Service id {service_id} is locked by container {other_container_id}.'
            )
            if cfg.client.containers.get(other_container_id).status == "paused":
                assert reassign_jobs(other_container_id, consider_paused=False)
            return

        lock_service(service_id, container_id)

    jobs.add(container_id, definitions, paused=paused)


def inspect_running_containers() -> datetime:
    log.info("Inspecting running containers.")
    last_event_time = datetime.utcnow()
    containers = cfg.client.containers.list(ignore_removed=True, sparse=True)

    for container in containers:
        container_id = container.id
        started_at = cfg.client.api.inspect_container(container_id)['State'][
            'StartedAt'
        ]
        last_event_time = max(
            last_event_time,
            datetime.fromisoformat(started_at[: 23 if len(started_at) < 26 else 26]),
        )
        process_started_container_labels(
            container_id, paused=container.status == 'paused'
        )

    log.debug('Finished inspection of running containers.')
    return last_event_time


def reassign_jobs(container_id: str, consider_paused: bool) -> Optional[str]:
    other_service_container = find_other_container_for_service(
        container_id, consider_paused
    )

    if other_service_container is None:
        return None

    new_id = other_service_container.id
    container_is_paused = other_service_container.status == "paused"
    log.info(f"{container_name(container_id)}: Reassigning jobs to {new_id}.")

    for job in jobs.get_jobs_for_container(container_id):
        log.debug(f"Handling job: {job.kwargs}")
        job_is_paused = not bool(job.next_run_time)

        if container_is_paused and not job_is_paused:
            job.pause()
            log.debug("Paused job.")
        elif not container_is_paused and job_is_paused:
            job.resume()
            log.debug("Resumed job.")

        job.modify(kwargs={**job.kwargs, "container_id": new_id})

    reassign_service_lock(container_id, new_id)

    return new_id


def find_other_container_for_service(
    container_id: str, consider_paused: bool
) -> Optional[Container]:
    service_id = service_locks_by_container_id.get(container_id)
    if service_id is None:
        return None

    for status in (
        ("running", "restarting", "paused", "created")
        if consider_paused
        else ("running", "restarting")
    ):
        candidates = [
            c
            for c in cfg.client.containers.list(
                all=True,
                ignore_removed=True,
                # TODO don't cast service_id to list when this patch is incorporated:
                #      https://github.com/docker/docker-py/pull/2445
                filters={"status": status, "label": list(service_id)},
            )
            if c.id != container_id
        ]

        if len(candidates):
            return candidates[0]

    return None


####


def listen(since: datetime) -> None:
    log.info("Listening to events.")
    for event_json in cfg.client.events(since=since):
        if b'container' not in event_json:
            continue

        if not any((x in event_json) for x in (b'start', b'die', b'pause', b'unpause')):
            continue

        event = json.loads(event_json)
        log.debug(f'Daemon event: {event}')
        if event['Type'] != 'container':
            continue

        action = event['Action']
        if action == 'start':
            handle_start(event)
        elif action == 'die':
            handle_die(event)
        elif action == 'pause':
            handle_pause(event)
        elif action == 'unpause':
            handle_unpause(event)


def handle_start(event: dict):
    container_id = event['Actor']['ID']
    log.debug(f'Handling start of {container_id}.')
    process_started_container_labels(container_id, paused=False)


def handle_die(event: dict):
    container_id = event['Actor']['ID']
    log.debug(f'Handling die of {container_id}.')
    if reassign_jobs(container_id, consider_paused=True) is None:
        for job in jobs.get_jobs_for_container(container_id):
            definition = job.kwargs
            log.debug(f"Removing job: {definition}")
            job.remove()
            log.info(
                f"{container_name(container_id)}: Removed '"
                + definition["job_name"]
                + "'."
            )
        unlock_service(container_id)


def handle_pause(event: dict):
    container_id = event['Actor']['ID']
    log.debug(f'Handling pause of {container_id}.')

    if reassign_jobs(container_id, consider_paused=False) is None:
        counter = 0
        for counter, job in enumerate(
            jobs.get_jobs_for_container(container_id), start=1
        ):
            job.pause()
            log.debug(f"Paused job: {job.kwargs}")
        if counter:
            log.info(f"{container_name(container_id)}: Paused {counter} jobs.")


def handle_unpause(event: dict):
    container_id = event['Actor']['ID']
    log.debug(f'Handling unpause of {container_id}.')

    if container_id not in service_locks_by_container_id:
        service_id, _, _ = parse_labels(container_id)
        if service_id:
            other_container_id = service_locks_by_service_id.get(service_id)
            if (
                other_container_id is not None
                and cfg.client.containers.get(other_container_id).status == "paused"
            ):
                container_id = reassign_jobs(other_container_id, consider_paused=False)

    counter = 0
    for counter, job in enumerate(jobs.get_jobs_for_container(container_id), start=1):
        job.resume()
        log.debug(f"Resumed job: {job.kwargs}")
    if counter:
        log.info(f"{container_name(container_id)}: Resumed {counter} jobs.")


def shutdown() -> None:  # pragma: nocover
    try:
        jobs.scheduler.shutdown()
    except SchedulerNotRunningError:
        pass

    if hasattr(cfg, "client"):
        cfg.client.close()


####


def main() -> None:  # pragma: nocover
    if DEBUG and not __debug__:
        log.debug("Replacing process with Python's optimizations off.")
        sys.stdout.flush()
        os.execlpe("deck-chores", "deck-chores", {**os.environ, "PYTHONOPTIMIZE": ""})

    if not lock.acquire(blocking=False):
        log.error(f"Couldn't acquire lock file at {lock.path}, exiting.")
        sys.exit(1)

    log.info(f'Deck Chores {__version__} started.')

    try:
        generate_config()
        log_handler.setFormatter(logging.Formatter(cfg.logformat, style='{'))
        log.debug(f'Config: {cfg.__dict__}')

        if there_is_another_deck_chores_container():
            log.error(
                "There's another container running deck-chores, maybe paused or "
                "restarting."
            )
            raise SystemExit(1)

        job_config_validator.set_defaults(cfg)

        last_event_time = inspect_running_containers()
        jobs.start_scheduler()
        listen(since=last_event_time + timedelta(microseconds=1))

    except SystemExit as e:
        exit_code = e.code
    except ConfigurationError as e:
        log.error(e)
        exit_code = 1
    except Exception:
        log.exception('Caught unhandled exception:')
        exit_code = 3
    else:
        exit_code = 0
    finally:
        shutdown()
        lock.release()
        sys.exit(exit_code)


if __name__ == '__main__':
    main()
