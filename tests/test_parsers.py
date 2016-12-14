from pytest import mark

from deck_chores.parsers import _parse_labels as parse_labels
from deck_chores.parsers import CronTrigger, DateTrigger, IntervalTrigger, JobConfigValidator


def test_parse_labels(mocker):
    labels = {
        'com.docker.compose.project': 'test_project',
        'com.docker.compose.service': 'ham_machine',
        'deck-chores.backup.interval': 'daily',
        'deck-chores.backup.command': '/usr/local/bin/backup.sh',
        'deck-chores.backup.user': 'www-data',
        'deck-chores.pull-data.date': '1945-05-08 00:01:00',
        'deck-chores.pull-data.command': '/usr/local/bin/pull.sh',
        'deck-chores.gen-thumbs.cron': '*/10 * * * *',
        'deck-chores.gen-thumbs.command': 'python /scripts/gen_thumbs.py',
        'deck-chores.gen-thumbs.max': '3'
    }
    mocker.patch('deck_chores.config.Client.inspect_container',
                 return_value={'Image': '', 'Config': {'Labels': labels}})
    mocker.patch('deck_chores.config.Client.inspect_image',
                 return_value={'Config': {'Labels': {}}})

    expected_jobs = \
        {'backup': {'trigger': (IntervalTrigger, (0, 1, 0, 0, 0)), 'name': 'backup',
                    'command': '/usr/local/bin/backup.sh', 'user': 'www-data', 'max': 1},
         'pull-data': {'trigger': (DateTrigger, ('1945-05-08 00:01:00',)), 'name': 'pull-data',
                       'command': '/usr/local/bin/pull.sh', 'user': 'root', 'max': 1},
         'gen-thumbs': {'trigger': (CronTrigger, ('*', '*', '*', '*/10', '*', '*', '*', '*')),
                        'name': 'gen-thumbs', 'command': 'python /scripts/gen_thumbs.py',
                        'user': 'root', 'max': 3}}
    _, _, result = parse_labels('')
    assert len(result) == len(expected_jobs)
    for name, definition in result.items():
        definition.pop('service_id')
        assert definition.pop('timezone') == 'UTC'
        assert len(definition) == 5
        assert definition == expected_jobs[name]


def test_interval_trigger():
    validator = JobConfigValidator({'trigger': {'coerce': 'interval'}})
    result = validator.validated({'trigger': '15'})['trigger']
    assert result == (IntervalTrigger, (0, 0, 0, 0, 15))


@mark.parametrize('default,value,result',
                  ((('image', 'service'), '', 'image,service'),
                   (('image', 'service'), 'noservice', 'image'),
                   (('service',), 'image', 'image,service')))
def test_options(default, value, result, mocker):
    labels = {'deck-chores.options': value}
    mocker.patch('deck_chores.config.Client.inspect_container',
                 return_value={'Image': '', 'Config': {'Labels': labels}})
    mocker.patch('deck_chores.config.cfg.default_options', default)
    assert parse_labels(str(default)+value)[1] == result
