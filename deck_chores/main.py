from datetime import datetime
import logging
import sys
from signal import signal, SIGINT, SIGTERM
from typing import List

from apscheduler.schedulers import SchedulerNotRunningError
from apscheduler.triggers.date import DateTrigger
from docker.models.containers import Container
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
    for container in cfg.client.containers.list():
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


signal(SIGINT, sigint_handler)
signal(SIGTERM, sigterm_handler)


####


def process_running_container_labels(container_id: str) -> None:
    service_id, flags, definitions = parse.labels(container_id)
    if not definitions:
        return

    if service_id and 'service' in flags:
        if service_id in locking_container_to_services_map.values():
            log.debug(f'Service id has a registered job: {service_id}')
            return

        log.info(f'Locking service id: {service_id}')
        locking_container_to_services_map[container_id] = service_id
    jobs.add(container_id, definitions)


def inspect_running_containers() -> datetime:
    log.debug('Fetching running containers')
    containers = cfg.client.containers.list(ignore_removed=True, sparse=True)
    inspection_time = datetime.utcnow()  # FIXME get last eventtime
    jobs.scheduler.add_job(
        exec_inspection,
        trigger=DateTrigger(),
        args=(containers,),
        id='container_inspection',
    )
    return inspection_time


def exec_inspection(containers: List[Container]) -> None:
    # TODO handle paused containers
    log.info('Inspecting running containers.')
    for container in containers:
        process_running_container_labels(container.id)
    log.debug('Finished inspection of running containers.')


def listen(since: datetime = None) -> None:
    if since is None:
        since = datetime.utcnow()
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
    process_running_container_labels(container_id)


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
            'Resuming job {job.kwargs["job_name"]} for {job.kwargs["container_name"]}'
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
        print(f"Couldn't acquire lock file at {lock.path}, exiting.")
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

        jobs.start_scheduler()
        inspection_time = inspect_running_containers()
        listen(since=inspection_time)
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
