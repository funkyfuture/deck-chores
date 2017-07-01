from time import sleep

from apscheduler.triggers.interval import IntervalTrigger
from docker.models.containers import Container

from deck_chores.jobs import add, scheduler, start_scheduler


def test_job_execution(cfg, mocker):
    container = mocker.MagicMock(Container)
    container.name = 'foo_0'
    cfg.client.containers.get.return_value = container

    def docker_containers(filters={}):
        if filters['status'] == 'paused':
            return []
        if filters['status'] == 'running':
            return [container]

    def docker_exec_start(id):
        sleep(2)
        return b'boo'

    start_scheduler()

    cfg.client.containers.list = docker_containers
    exec_create = mocker.MagicMock(return_value={'Id': 'id'})
    cfg.client.api.exec_create = exec_create
    cfg.client.api.exec_inspect.return_value = {'ExitCode': 0}
    cfg.client.api.exec_start = docker_exec_start

    definitions = {
        'foo':
            {'command': 'sleep 2',
             'max': 2, 'timezone': 'UTC',
             'trigger': (IntervalTrigger, (0, 0, 0, 0, 1)),
             'user': 'test'}
    }
    add('void', definitions)
    sleep(3)

    scheduler.shutdown(wait=False)

    assert exec_create.call_count == 2
