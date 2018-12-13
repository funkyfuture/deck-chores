import logging
from typing import Dict, List, Mapping, Tuple

from apscheduler import events
from apscheduler.job import Job
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.util import undefined as undefined_runtime

from deck_chores.config import cfg
from deck_chores.utils import generate_id


####

CAPTURED_OPENER = '== BEGIN of captured stdout & stderr =='
CAPTURED_CLOSER = '== END of captured stdout & stderr ===='
CAPTURED_SURROUNDING_LENGTH = len(CAPTURED_OPENER)


####


log = logging.getLogger('deck_chores')


####


scheduler = BackgroundScheduler()


def start_scheduler():
    logger = log if cfg.debug else None
    scheduler.configure(logger=logger, timezone=cfg.timezone)
    scheduler.add_listener(on_error, events.EVENT_JOB_ERROR)
    scheduler.add_listener(on_executed, events.EVENT_JOB_EXECUTED)
    scheduler.add_listener(on_max_instances, events.EVENT_JOB_MAX_INSTANCES)
    scheduler.add_listener(on_missed, events.EVENT_JOB_MISSED)
    scheduler.start()


####


def on_max_instances(event: events.JobSubmissionEvent) -> None:
    job = scheduler.get_job(event.job_id)
    job_name = job.kwargs['job_name']
    container_name = job.kwargs['container_name']
    max_inst = job.max_instances
    log.info(
        f'Not running {job_name} in {container_name}, '
        f'maximum instances of {max_inst} are still running.'
    )


def on_executed(event: events.JobExecutionEvent) -> None:
    job = scheduler.get_job(event.job_id)
    if job is None or job.id == 'container_inspection':
        return

    definition = job.kwargs
    exit_code, response_lines = event.retval
    response_lines = response_lines.decode().splitlines()

    log.log(
        logging.INFO if exit_code == 0 else logging.CRITICAL,
        f'Command {definition["command"]} in {definition["container_name"]} '
        f'finished with exit code {exit_code}',
    )
    if response_lines:
        longest_line = max(len(x) for x in response_lines)
        log.info(CAPTURED_OPENER + '=' * (longest_line - CAPTURED_SURROUNDING_LENGTH))
        for line in response_lines:
            log.info(line)
        log.info(CAPTURED_CLOSER + '=' * (longest_line - CAPTURED_SURROUNDING_LENGTH))


def on_error(event: events.JobExecutionEvent) -> None:
    definition = scheduler.get_job(event.job_id).kwargs
    log.critical(
        f'An exception in deck-chores occured while executing {definition["job_name"]} '
        f'in {definition["container_name"]}:'
    )
    log.exception(event.exception)


def on_missed(event: events.JobExecutionEvent) -> None:
    definition = scheduler.get_job(event.job_id).kwargs
    log.warning(
        f'Missed execution of {definition["job_name"]} in '
        f'{definition["container_name"]} at {event.scheduled_run_time}'
    )


####


def exec_job(**definition) -> Tuple[int, bytes]:
    job_id = definition['job_id']
    container_id = definition['container_id']
    log.info(f"Executing '{definition['job_name']}' in {definition['container_name']}")

    # some sanity checks, to be removed eventually
    assert scheduler.get_job(job_id) is not None
    if cfg.client.containers.list(filters={'id': container_id, 'status': 'paused'}):
        raise AssertionError('Container is paused.')

    if not cfg.client.containers.list(
        filters={'id': container_id, 'status': 'running'}
    ):
        scheduler.remove_job(job_id)
        assert scheduler.get_job(job_id) is None
        raise AssertionError('Container is not running.')
    # end of sanity checks

    return cfg.client.containers.get(container_id).exec_run(
        cmd=definition['command'],
        user=definition.get('user', ''),
        environment=definition['environment'],
        workdir=definition.get('workdir'),
    )


####


def add(
    container_id: str, definitions: Mapping[str, Dict], paused: bool = False
) -> None:
    container = cfg.client.containers.get(container_id)
    container_name = container.name
    log.debug(f'Adding jobs for {container_name}.')
    for job_name, definition in definitions.items():
        job_id = generate_id(container_id, job_name)

        definition.update(
            {
                'job_name': job_name,
                'job_id': job_id,
                'container_id': container_id,
                'container_name': container_name,
            }
        )

        trigger_class, trigger_config = definition['trigger']

        scheduler.add_job(
            func=exec_job,
            trigger=trigger_class(
                *trigger_config,
                timezone=definition['timezone'],
                jitter=definition['jitter'],
            ),
            kwargs=definition,
            id=job_id,
            max_instances=definition['max'],
            next_run_time=None if paused else undefined_runtime,
            replace_existing=True,
        )
        log.info(
            "Added "
            + ("paused " if paused else "")
            + f"'{job_name}' for {container_name}"
        )


def remove(job_id: str) -> None:
    try:
        scheduler.remove_job(job_id)
    except JobLookupError as e:
        log.critical(str(e))


####


def get_jobs_for_container(container_id: str) -> List[Job]:
    # TODO make that an index
    result = []
    for job in scheduler.get_jobs():
        if job.kwargs['container_id'] == container_id:
            result.append(job)
    return result
