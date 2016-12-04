from os import chdir, environ
from pathlib import Path
from subprocess import check_output

from deck_chores.parsers import CronTrigger, DateTrigger, IntervalTrigger


TEST_DIR = Path(__file__).parent
PROJECT_DIR = TEST_DIR / '..'
COMPOSE_PROJECTS_DIR = TEST_DIR / 'fixtures' / 'compose_projects'


def equal_triggers(a, b):
    if not isinstance(b, (type(a))):
        raise AssertionError('%s != %s ' % (a.__class__, b.__class__))
    if isinstance(a, CronTrigger):
        for i, field in enumerate(a.fields):
            assert field == b.fields[i]
    elif isinstance(a, DateTrigger):
        assert a.run_date == b.run_date
    elif isinstance(a, IntervalTrigger):
        assert a.interval_length == b.interval_length
    return True


def on_travis():
    return


class ComposeProject:
    def __init__(self, project_name: str, env: dict = {}) -> None:
        self.project_path = str(COMPOSE_PROJECTS_DIR / project_name)
        self.env = environ.copy()
        self.env.update(env)
        self.command(['up', '--force-recreate', '-d'])

    def command(self, args: list, call_kwargs: dict = {}):
        _call_kwargs = {'env': self.env.copy()}
        _call_kwargs.update(call_kwargs)
        chdir(self.project_path)
        return check_output(['docker-compose'] + args, **_call_kwargs)

    def down(self):
        self.command(['stop'])
        logs = self.logs
        self.command(['rm'])
        return logs

    @property
    def logs(self):
        logs = self.command(['logs', '--no-color'])
        logs = logs.decode().splitlines()
        result = []
        for line in logs:
            line = line.split('|', 1)
            if len(line) != 2:
                continue
            result.append(line[1].strip())
        return result
