from time import sleep

from apscheduler.triggers.interval import IntervalTrigger
from docker.models.containers import Container

from deck_chores.jobs import add, scheduler, start_scheduler


# TODO silence logger
def test_job_execution(capsys, cfg, mocker):
    container = mocker.MagicMock(Container)
    container.name = 'foo_0'
    container.exec_run.return_value = (0, b'')
    cfg.client.containers.get.return_value = container

    def docker_containers(filters=None):
        if filters['status'] == 'paused':
            return []

        if filters['status'] == 'running':
            return [container]

    def docker_exec_start(id):
        sleep(2)

    start_scheduler()

    cfg.client.containers.list = docker_containers
    cfg.client.api.exec_start = docker_exec_start

    definitions = {
        'foo': {
            'command': 'sleep 2',
            'environment': {},
            'max': 2,
            'timezone': 'UTC',
            'trigger': (IntervalTrigger, (0, 0, 0, 0, 1)),
            'jitter': None,
            'user': 'test',
        }
    }
    add('void', definitions)
    sleep(2.5)

    scheduler.shutdown(wait=False)

    container.exec_run.assert_has_calls(
        2 * [mocker.call(cmd='sleep 2', user='test', environment={}, workdir=None)]
    )
