import logging
from typing import Dict, Iterator, Mapping, Tuple

from apscheduler import events
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.util import undefined as undefined_runtime

from deck_chores.config import cfg
from deck_chores.indexes import container_name
from deck_chores.utils import generate_id, log


####


scheduler = BackgroundScheduler()


def start_scheduler():
    job_executors = {"default": ThreadPoolExecutor(cfg.job_executor_pool_size)}
    logger = log if cfg.debug else None
    scheduler.configure(executors=job_executors, logger=logger, timezone=cfg.timezone)
    scheduler.add_listener(on_error, events.EVENT_JOB_ERROR)
    scheduler.add_listener(on_executed, events.EVENT_JOB_EXECUTED)
    scheduler.add_listener(on_max_instances, events.EVENT_JOB_MAX_INSTANCES)
    scheduler.add_listener(on_missed, events.EVENT_JOB_MISSED)
    scheduler.start()


####


def on_max_instances(event: events.JobSubmissionEvent) -> None:
    job = scheduler.get_job(event.job_id)
    definition = job.kwargs
    log.info(
        f"{container_name(definition['container_id'])}: "
        f"Not running {definition['job_name']},  "
        f"maximum instances of {job.max_instances} are still running."
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
        f'Command {definition["command"]} in container {definition["container_id"]} '
        f'finished with exit code {exit_code}.',
    )
    if response_lines:
        log.info("== BEGIN of captured stdout & stderr ==")
        for line in response_lines:
            log.info(line)
        log.info("== END of captured stdout & stderr ====")


def on_error(event: events.JobExecutionEvent) -> None:
    definition = scheduler.get_job(event.job_id).kwargs
    log.critical(
        f'An exception in deck-chores occurred while executing'
        f' {definition["job_name"]} in container {definition["container_id"]}:'
    )
    log.error(str(event.exception))


def on_missed(event: events.JobExecutionEvent) -> None:
    definition = scheduler.get_job(event.job_id).kwargs
    log.warning(
        f'Missed execution of {definition["job_name"]} in container '
        f'{definition["container_id"]} at {event.scheduled_run_time}.'
    )


####


def exec_job(**definition) -> Tuple[int, bytes]:
    job_id = definition['job_id']
    container_id = definition['container_id']
    log.info(f"{container_name(container_id)}: Executing '{definition['job_name']}'.")

    # some sanity checks, to be removed eventually
    assert scheduler.get_job(job_id) is not None
    if cfg.client.containers.list(filters={'id': container_id, 'status': 'paused'}):
        raise AssertionError('Container is paused.')

    if not cfg.client.containers.list(
        filters={'id': container_id, 'status': 'running'}
    ):
        assert scheduler.get_job(job_id) is None
        raise AssertionError('Container is not running.')
    # end of sanity checks

    return cfg.client.containers.get(container_id).exec_run(
        cmd=definition['command'],
        user=definition['user'],
        environment=definition['environment'],
        workdir=definition.get('workdir'),
    )


####


def add(
    container_id: str, definitions: Mapping[str, Dict], paused: bool = False
) -> None:
    log.debug(f'Adding jobs to container {container_id}.')

    for job_name, definition in definitions.items():
        job_id = generate_id(*definition.get("service_id") or (container_id,), job_name)

        definition.update(
            {'job_name': job_name, 'job_id': job_id, 'container_id': container_id}
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
            name=job_name,
            max_instances=definition['max'],
            next_run_time=None if paused else undefined_runtime,
            replace_existing=True,
        )
        log.info(
            f"{container_name(container_id)}: Added "
            + ("paused " if paused else "")
            + f"'{job_name}' ({job_id})."
        )


####


def get_jobs_for_container(container_id: str) -> Iterator[Job]:
    assert container_id, container_id
    for job in scheduler.get_jobs():
        if job.kwargs['container_id'] == container_id:
            yield job


__all__ = (
    "scheduler",
    "start_scheduler",
    add.__name__,
    get_jobs_for_container.__name__,
)
