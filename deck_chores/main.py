from datetime import datetime, timedelta
import logging
import sys
from signal import signal, SIGINT, SIGTERM, SIGUSR1

from apscheduler.schedulers import SchedulerNotRunningError
from fasteners import InterProcessLock

from deck_chores import __version__  # noqa: F401  # used only in f-string
from deck_chores.config import cfg, generate_config
from deck_chores.exceptions import ConfigurationError
from deck_chores.indexes import locking_container_to_services_map
from deck_chores import jobs
import deck_chores.parsers as parse
from deck_chores.utils import from_json, generate_id, log, log_handler


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
        if service_id in locking_container_to_services_map.values():
            log.debug(f'Service id has a registered job: {service_id}')
            return

        log.info(f'Locking service: {service_id}')
        locking_container_to_services_map[container_id] = service_id

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


def handle_start(event: dict) -> None:
    log.debug('Handling start.')
    container_id = event['Actor']['ID']
    process_started_container_labels(container_id)


def handle_die(event: dict) -> None:
    log.debug('Handling die.')
    container_id = event['Actor']['ID']
    service_id, flags, definitions = parse.labels(container_id)
    if not definitions:
        return

    if service_id and 'service' in flags:
        if container_id in locking_container_to_services_map:
            log.info(f'Unlocking service id: {service_id}')
            del locking_container_to_services_map[container_id]
        else:
            return

    container_name = cfg.client.containers.get(container_id).name
    for job_name in definitions:
        log.info(f"Removing job '{job_name}' for {container_name}")
        jobs.remove(generate_id(container_id, job_name))


def handle_pause(event: dict) -> None:
    log.debug('Handling pause.')
    container_id = event['Actor']['ID']
    for job in jobs.get_jobs_for_container(container_id):
        log.info(
            f'Pausing job {job.kwargs["job_name"]} for {job.kwargs["container_name"]}'
        )
        job.pause()


def handle_unpause(event: dict) -> None:
    log.debug('Handling unpause.')
    container_id = event['Actor']['ID']
    for job in jobs.get_jobs_for_container(container_id):
        log.info(
            f'Resuming job {job.kwargs["job_name"]} for {job.kwargs["container_name"]}'
        )
        job.resume()


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
    log.info('Deck Chores {__version__} started.')
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
