import logging
from typing import List, Tuple

from apscheduler import events  # type: ignore
from apscheduler.job import Job  # type: ignore
from apscheduler.jobstores.base import JobLookupError  # type: ignore
from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore

from deck_chores.config import cfg
from deck_chores.utils import generate_id


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
    log.info('Not running %s in %s, maximum instances of %s are still running.'
             '' % (job_name, container_name, max_inst))


def on_executed(event: events.JobExecutionEvent) -> None:
    job = scheduler.get_job(event.job_id)
    if job is None or job.id == 'container_inspection':
        return

    definition = job.kwargs
    exit_code, response_lines = event.retval
    response_lines = response_lines.decode().splitlines()

    log.log(
        logging.INFO if exit_code == 0 else logging.CRITICAL,
        'Command {command} in {container_name} finished with exit code {exit_code}'
        .format(command=definition['command'],
                container_name=definition['container_name'],
                exit_code=exit_code)
    )
    if response_lines:
        longest_line = max(len(x) for x in response_lines)
        b = '== BEGIN of output =='
        e = '== END of output ===='
        log.info(b + '=' * (longest_line - len(b)))
        for line in response_lines:
            log.info(line)
        log.info(e + '=' * (longest_line - len(e)))


def on_error(event: events.JobExecutionEvent) -> None:
    job = scheduler.get_job(event.job_id)
    job_name = job.kwargs['job_name']
    container_name = job.kwargs['container_name']
    log.warning('An exception occured while executing %s in %s:' % (job_name, container_name))
    log.exception(event.exception)


def on_missed(event: events.JobExecutionEvent) -> None:
    job = scheduler.get_job(event.job_id)
    job_name = job.kwargs['job_name']
    container_name = job.kwargs['container_name']
    run_time = event.scheduled_run_time
    log.warning('Missed execution of %s in %s at %s' % (job_name, container_name, run_time))


####


def exec_job(**definition) -> Tuple[int, bytes]:
    job_id = definition['job_id']

    container_id = definition['container_id']
    command = definition['command']

    log.info("Executing '%s' in %s" % (definition['job_name'], definition['container_name']))

    # some sanity checks, to be removed eventually
    assert scheduler.get_job(job_id) is not None
    if cfg.client.containers(filters={'id': container_id, 'status': 'paused'}):
        raise AssertionError('Container is paused.')
    if not cfg.client.containers(filters={'id': container_id, 'status': 'running'}):
        scheduler.remove_job(job_id)
        assert scheduler.get_job(job_id) is None
        raise AssertionError('Container is not running.')

    exec_id = cfg.client.exec_create(container_id, command, user=definition['user'])['Id']
    response = cfg.client.exec_start(exec_id)
    exit_code = cfg.client.exec_inspect(exec_id)['ExitCode']

    return exit_code, response or b''


####


def add(container_id: str, definitions: dict) -> None:
    container_name = cfg.client.inspect_container(container_id)['Name']
    log.debug('Adding jobs for %s.' % container_name)
    for job_name, definition in definitions.items():
        job_id = generate_id(container_id, job_name)
        trigger = definition['trigger']
        definition.update({
            'job_name': job_name, 'job_id': job_id,
            'container_id': container_id, 'container_name': container_name}
        )
        scheduler.add_job(func=exec_job,
                          trigger=trigger[0](*trigger[1],
                                             timezone=definition['timezone']),
                          kwargs=definition,
                          id=job_id,
                          max_instances=definition['max'],
                          replace_existing=True)
        log.info("Added '%s' for %s" % (job_name, container_name))


def remove(job_id: str) -> None:
    try:
        scheduler.remove_job(job_id)
    except JobLookupError as e:
        log.critical(str(e))


####


# TODO make that an index
def get_jobs_for_container(container_id: str) -> List[Job]:
    result = []
    for job in scheduler.get_jobs():
        if job.kwargs['container_id'] == container_id:
            result.append(job)
    return result
