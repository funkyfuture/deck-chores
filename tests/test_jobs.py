from time import sleep

from apscheduler.triggers.interval import IntervalTrigger

from deck_chores.jobs import add, scheduler, start_scheduler


def test_job_execution(mocker):
    def docker_containers(self, filters={}):
        if filters['status'] == 'paused':
            return False
        if filters['status'] == 'running':
            return True

    def docker_exec_start(self, id):
        sleep(2)
        return b'boo'

    start_scheduler()
    mocker.patch('deck_chores.config.Client.containers', docker_containers)
    exec_create = mocker.patch('deck_chores.config.Client.exec_create')
    exec_create.return_value = {'Id': 'id'}
    mocker.patch('deck_chores.config.Client.exec_inspect',
                 return_value={'ExitCode': 0})
    mocker.patch('deck_chores.config.Client.exec_start', docker_exec_start)
    mocker.patch('deck_chores.config.Client.inspect_container',
                 return_value={'Name': 'foo_0'})
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
