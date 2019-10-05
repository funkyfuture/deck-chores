import logging
import sys
from datetime import datetime, timedelta
from signal import signal, SIGINT, SIGTERM, SIGUSR1
from typing import Optional

from apscheduler.schedulers import SchedulerNotRunningError
from fasteners import InterProcessLock

import deck_chores.parsers as parse
from deck_chores import __version__, jobs, services
from deck_chores.config import cfg, generate_config
from deck_chores.exceptions import ConfigurationError
from deck_chores.utils import from_json, log, log_handler


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


def sigint_handler(signum, frame):
    log.info('Keyboard interrupt.')
    raise SystemExit(0)


def sigterm_handler(signum, frame):
    log.info('Received SIGTERM.')
    raise SystemExit(0)


def sigusr1_handler(signum, frame):
    log.info('SIGUSR1 received, echoing all jobs.')
    for job in jobs.scheduler.get_jobs():
        log.info(f'ID: {job.id}   Next execution: {job.next_run_time}   Configuration:')
        log.info(job.kwargs)


signal(SIGINT, sigint_handler)
signal(SIGTERM, sigterm_handler)
signal(SIGUSR1, sigusr1_handler)


####


def process_started_container_labels(container_id: str, paused: bool = False) -> None:
    service_id, flags, definitions = parse.labels(container_id)

    if not definitions:
        return

    if service_id and 'service' in flags:
        other_container_id = services.service_id_to_container_id.get(service_id)
        if other_container_id:
            log.debug(
                f'Service id {service_id} is locked by container {other_container_id}.'
            )
            if cfg.client.containers.get(other_container_id).status == "paused":
                assert reassign_jobs(other_container_id, consider_paused=False)
            return

        services.assign(service_id, container_id)

    jobs.add(container_id, definitions, paused=paused)


def inspect_running_containers() -> datetime:
    log.info('Inspecting running containers.')
    last_event_time = datetime.utcnow()
    containers = cfg.client.containers.list(ignore_removed=True, sparse=True)

    for container in containers:
        data = cfg.client.api.inspect_container(container.id)
        last_event_time = max(
            last_event_time,
            # not sure why mypy doesn't know about this method:
            datetime.fromisoformat(data['State']['StartedAt'][:26]),  # type: ignore
        )
        process_started_container_labels(
            container.id, paused=container.status == 'paused'
        )

    log.debug('Finished inspection of running containers.')
    return last_event_time


def reassign_jobs(container_id: str, consider_paused: bool) -> Optional[str]:
    other_service_container = services.find_other_container_for_service(
        container_id, consider_paused
    )

    if other_service_container is None:
        return None

    new_id = other_service_container.id
    container_is_paused = other_service_container.status == "paused"
    log.debug(f"Reassigning jobs from container {container_id} to {new_id}.")

    for job in jobs.get_jobs_for_container(container_id):
        log.debug(f"Handling job: {job.kwargs}")
        job_is_paused = not bool(job.next_run_time)

        if container_is_paused and not job_is_paused:
            job.pause()
            log.debug(f"Paused job.")
        elif not container_is_paused and job_is_paused:
            job.resume()
            log.debug(f"Resumed job.")

        job.modify(kwargs={**job.kwargs, "container_id": new_id})

    services.reassign_container(container_id, new_id)

    return new_id


####


def listen(since: datetime) -> None:
    log.info('Listening to events.')
    for event_json in cfg.client.events(since=since):
        if b'container' not in event_json:
            continue

        if not any((x in event_json) for x in (b'start', b'die', b'pause', b'unpause')):
            continue

        event = from_json(event_json)
        log.debug(f'Daemon event: {event}')
        if event['Type'] != 'container':
            continue

        elif event['Action'] == 'start':
            handle_start(event)
        elif event['Action'] == 'die':
            handle_die(event)
        elif event['Action'] == 'pause':
            handle_pause(event)
        elif event['Action'] == 'unpause':
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
            log.debug(f"Removing job: {job.kwargs}")
            job.remove()
        services.remove_by_container_id(container_id)


def handle_pause(event: dict):
    container_id = event['Actor']['ID']
    log.debug(f'Handling pause of {container_id}.')

    if reassign_jobs(container_id, consider_paused=False) is None:
        for job in jobs.get_jobs_for_container(container_id):
            job.pause()
            log.debug(f"Paused job: {job.kwargs}")


def handle_unpause(event: dict):
    container_id = event['Actor']['ID']
    log.debug(f'Handling unpause of {container_id}.')

    if container_id not in services.container_id_to_service_id:
        service_id, _, _ = parse.labels(container_id)
        if service_id:
            other_container_id = services.service_id_to_container_id.get(service_id)
            if (
                other_container_id is not None
                and cfg.client.containers.get(other_container_id).status == "paused"
            ):
                container_id = reassign_jobs(other_container_id, consider_paused=False)

    for job in jobs.get_jobs_for_container(container_id):
        job.resume()
        log.debug(f"Resumed job: {job.kwargs}")


def shutdown() -> None:
    try:
        jobs.scheduler.shutdown()
    except SchedulerNotRunningError:
        pass
    cfg.client.close()


####


def main() -> None:
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

        last_event_time = inspect_running_containers()
        jobs.start_scheduler()
        listen(since=last_event_time + timedelta(microseconds=1))

    except SystemExit as e:
        exit_code = e.code
    except ConfigurationError as e:
        log.error(str(e))
        exit_code = 1
    except Exception as e:
        log.error('Caught unhandled exception:')
        log.exception(e)
        exit_code = 3
    else:
        exit_code = 0
    finally:
        shutdown()
        lock.release()
        sys.exit(exit_code)


if __name__ == '__main__':
    main()
