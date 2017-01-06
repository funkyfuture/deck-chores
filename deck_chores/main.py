# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import os
import sys
from signal import signal, SIGINT, SIGTERM

from apscheduler.schedulers import SchedulerNotRunningError  # type: ignore
from apscheduler.triggers.date import DateTrigger  # type: ignore
from fasteners import InterProcessLock  # type: ignore

from deck_chores import __version__
from deck_chores.caches import get_image_labels_for_container
from deck_chores.config import cfg, generate_config
from deck_chores.exceptions import ConfigurationError
from deck_chores.indexes import locking_container_to_services_map
from deck_chores import jobs
import deck_chores.parsers as parse
from deck_chores.utils import from_json, generate_id, trueish


####


lock = InterProcessLock('/tmp/deck-chores.lock')


def there_is_another_deck_chores_container() -> bool:
    matched_containers = 0
    for container in cfg.client.containers():
        if container['State'] in 'created,exited':
            continue
        labels = get_image_labels_for_container(container['Id'])
        if labels.get('org.label-schema.name', '') == 'deck-chores':
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


log = logging.getLogger('deck_chores')
log_handler = logging.StreamHandler(sys.stdout)
log.addHandler(log_handler)
log.setLevel(logging.DEBUG if trueish(os.getenv('DEBUG', 'no')) else logging.INFO)


####


def process_running_container_labels(container_id: str) -> None:
    service_id, options, definitions = parse.labels(container_id)
    if not definitions:
        return
    if service_id and 'service' in options:
        if locking_container_to_services_map.values():
            log.debug('Service id has a registered job: %s' % service_id)
            return
        log.info('Locking service id: %s' % service_id)
        locking_container_to_services_map[container_id] = service_id
    jobs.add(container_id, definitions)


def inspect_running_containers() -> datetime:
    log.debug('Fetching running containers')
    containers = cfg.client.containers(filters={'status': 'running'})
    inspection_time = datetime.utcnow()
    jobs.scheduler.add_job(exec_inspection, trigger=DateTrigger(), args=(containers,),
                           id='container_inspection')
    return inspection_time


def exec_inspection(containers: dict) -> None:
    log.info('Inspecting running containers.')
    for container in containers:
        process_running_container_labels(container['Id'])


def listen(since: datetime = datetime.utcnow()) -> None:
    log.info('Listening to events.')
    for event_json in cfg.client.events(since=since):
        if b'container' not in event_json:
            continue
        if not any((x in event_json) for x in (b'start', b'die', b'pause', b'unpause')):
            continue

        event = from_json(event_json)
        log.debug('Daemon event: %s' % event)
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
    service_id, options, definitions = parse.labels(container_id)
    if not definitions:
        return

    if service_id and 'service' in options:
        if container_id in locking_container_to_services_map:
            log.info('Unlocking service id: %s' % service_id)
            del locking_container_to_services_map[container_id]
        else:
            return

    container_name = cfg.client.inspect_container(container_id)['Name']
    for job_name in definitions:
        log.info("Removing job '%s' for %s" % (job_name, container_name))
        jobs.remove(generate_id(container_id, job_name))


def handle_pause(event: dict) -> None:
    log.debug('Handling pause.')
    container_id = event['Actor']['ID']
    for job in jobs.get_jobs_for_container(container_id):
        log.info('Pausing job %s for %s' % (job.kwargs['job_name'], job.kwargs['container_name']))
        job.pause()


def handle_unpause(event: dict) -> None:
    log.debug('Handling unpause.')
    container_id = event['Actor']['ID']
    for job in jobs.get_jobs_for_container(container_id):
        log.info('Resuming job %s for %s' % (job.kwargs['job_name'], job.kwargs['container_name']))
        job.resume()


def shutdown() -> None:
    try:
        jobs.scheduler.shutdown()
    except SchedulerNotRunningError:
        pass


####


def main() -> None:
    if not lock.acquire(blocking=False):
        print("Couldn't acquire lock file at %s, exiting." % lock.path)
        sys.exit(1)
    log.info('Deck Chores %s started.' % __version__)
    try:
        generate_config()
        log_handler.setFormatter(logging.Formatter(cfg.logformat, style='{'))
        log.debug('Config: %s' % cfg.__dict__)
        if there_is_another_deck_chores_container():
            log.error("There's another container running deck-chores, maybe paused or restarting.")
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
        log.exception(e)  # type: ignore
        exit_code = 3
    else:
        exit_code = 0
    finally:
        shutdown()
        lock.release()
        sys.exit(exit_code)


if __name__ == '__main__':
    main()
