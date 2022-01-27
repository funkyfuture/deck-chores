from datetime import datetime

from docker.models.containers import Container
from pytest import mark

from deck_chores.main import parse_iso_timestamp
from deck_chores.parsers import (
    parse_flags,
    parse_labels,
    CronTrigger,
    DateTrigger,
    IntervalTrigger,
    JobConfigValidator,
)


@mark.parametrize(
    "sample",
    (
        "2021-05-05T16:42:18.488227566+00:00",
        "2021-05-17T20:07:58.54095Z",
        "2021-05-19T19:07:31.118260683Z",
    ),
)
def test_from_iso_timetamp(sample):
    """This test is to be used to test concrete manifestations of timestamps that Docker
    daemons produced in the wild."""
    assert isinstance(parse_iso_timestamp(sample), datetime)


def test_parse_labels(cfg, mocker):
    labels = {
        'project_id': 'test_project',
        'service_id': 'ham_machine',
        'deck-chores.backup.interval': 'daily',
        'deck-chores.backup.command': '/usr/local/bin/backup.sh',
        'deck-chores.backup.user': 'www-data',
        'deck-chores.backup.workdir': '/backups',
        'deck-chores.pull-data.date': '1945-05-08 00:01:00',
        'deck-chores.pull-data.command': '/usr/local/bin/pull.sh',
        'deck-chores.pull-data.env.BASE_URL': 'https://foo.org/records/',
        'deck-chores.pull-data.env.TIMEOUT': '120',
        'deck-chores.gen-thumbs.cron': '*/10 * * * *',
        'deck-chores.gen-thumbs.command': 'python /scripts/gen_thumbs.py',
        'deck-chores.gen-thumbs.jitter': '600',
        'deck-chores.gen-thumbs.max': '3',
    }
    container = mocker.MagicMock(Container)
    container.labels = labels
    container.image.labels = {}
    cfg.client.containers.get.return_value = container

    expected_jobs = {
        'backup': {
            'trigger': (IntervalTrigger, (0, 1, 0, 0, 0)),
            'name': 'backup',
            'command': '/usr/local/bin/backup.sh',
            'user': 'www-data',
            'max': 1,
            'environment': {},
            'workdir': '/backups',
        },
        'pull-data': {
            'trigger': (DateTrigger, ('1945-05-08 00:01:00',)),
            'name': 'pull-data',
            'command': '/usr/local/bin/pull.sh',
            'user': '',
            'max': 1,
            'environment': {'BASE_URL': 'https://foo.org/records/', 'TIMEOUT': '120'},
        },
        'gen-thumbs': {
            'trigger': (CronTrigger, ('*', '*', '*', '*/10', '*', '*', '*', '*')),
            'name': 'gen-thumbs',
            'command': 'python /scripts/gen_thumbs.py',
            'user': '',
            'max': 3,
            'environment': {},
            'jitter': 600,
        },
    }
    _, _, job_definitions = parse_labels('test_parse_labels')
    assert len(job_definitions) == len(expected_jobs)
    for name, job_config in job_definitions.items():
        job_config.pop('service_id')
        assert job_config.pop('timezone') == 'UTC'
        assert job_config == expected_jobs[name]


def test_parse_labels_with_time_units(cfg, mocker):
    labels = {
        'project_id': 'test_project',
        'service_id': 'time_machine',
        'deck-chores.backup.interval': '2 weeks',
        'deck-chores.backup.jitter': '0.5 day',
        'deck-chores.backup.command': '/usr/local/bin/backup.sh',
        'deck-chores.backup.user': 'www-data',
        'deck-chores.backup.workdir': '/backups',
        'deck-chores.pull-data.interval': '42 secs 1 day',
        'deck-chores.pull-data.command': '/usr/local/bin/pull.sh',
        'deck-chores.pull-data.env.BASE_URL': 'https://foo.org/records/',
        'deck-chores.pull-data.env.TIMEOUT': '120',
        'deck-chores.gen-thumbs.interval': '3 xongs',
        'deck-chores.gen-thumbs.command': 'python /scripts/gen_thumbs.py',
        'deck-chores.gen-thumbs.jitter': '600',
        'deck-chores.gen-thumbs.max': '3',
    }
    container = mocker.MagicMock(Container)
    container.labels = labels
    container.image.labels = {}
    cfg.client.containers.get.return_value = container

    expected_jobs = {
        'backup': {
            'trigger': (IntervalTrigger, (2, 0, 0, 0, 0)),
            'name': 'backup',
            'command': '/usr/local/bin/backup.sh',
            'user': 'www-data',
            'max': 1,
            'environment': {},
            'workdir': '/backups',
            'jitter': 0.5 * 24 * 60 * 60,
        },
        'pull-data': {
            'trigger': (IntervalTrigger, (0, 1, 0, 0, 42)),
            'name': 'pull-data',
            'command': '/usr/local/bin/pull.sh',
            'user': '',
            'max': 1,
            'environment': {'BASE_URL': 'https://foo.org/records/', 'TIMEOUT': '120'},
        },
    }
    _, _, job_definitions = parse_labels('test_parse_labels_with__time_units')

    assert len(job_definitions) == len(expected_jobs), job_definitions
    for name, job_config in job_definitions.items():
        job_config.pop('service_id')
        assert job_config.pop('timezone') == 'UTC'
        assert job_config == expected_jobs[name]


def test_parse_labels_with_user_option(cfg, mocker):
    labels = {
        'deck-chores.options.user': 'c_options_user',
        'deck-chores.job.command': 'a_command',
        'deck-chores.job.interval': 'hourly',
    }
    image_labels = {'deck-chores.options.user': 'l_options_user'}
    container = mocker.MagicMock(Container)
    container.labels = labels
    container.image.labels = image_labels
    cfg.client.containers.get.return_value = container

    expected_jobs = {
        'job': {
            'trigger': (IntervalTrigger, (0, 0, 1, 0, 0)),
            'name': 'job',
            'command': 'a_command',
            'user': 'c_options_user',
            'max': 1,
            'timezone': 'UTC',
            'environment': {},
        }
    }

    _, _, job_definitions = parse_labels('test_parse_labels_with_user_option')
    assert job_definitions == expected_jobs, job_definitions


def test_parse_labels_with_user_option_from_image(cfg, mocker):
    labels = {
        'deck-chores.job.command': 'a_command',
        'deck-chores.job.interval': 'hourly',
    }
    image_labels = {'deck-chores.options.user': 'l_options_user'}
    container = mocker.MagicMock(Container)
    container.labels = labels
    container.image.labels = image_labels
    cfg.client.containers.get.return_value = container

    expected_jobs = {
        'job': {
            'trigger': (IntervalTrigger, (0, 0, 1, 0, 0)),
            'name': 'job',
            'command': 'a_command',
            'user': 'l_options_user',
            'max': 1,
            'timezone': 'UTC',
            'environment': {},
        }
    }

    _, _, job_definitions = parse_labels(
        'test_parse_labels_with_user_option_from_image'
    )
    assert job_definitions == expected_jobs, job_definitions


def test_interval_trigger():
    validator = JobConfigValidator({'trigger': {'coerce': 'interval'}})
    result = validator.validated({'trigger': '15'})['trigger']
    assert result == (IntervalTrigger, (0, 0, 0, 0, 15))


@mark.parametrize(
    'default,value,result',
    (
        (('image', 'service'), '', 'image,service'),
        (('image', 'service'), 'noservice', 'image'),
        (('image', 'service'), 'noimage', 'service'),
        (('service',), 'image', 'image,service'),
    ),
)
def test_flags(cfg, mocker, default, value, result):
    cfg.default_flags = default
    container = mocker.MagicMock(Container)
    container.labels = {'deck-chores.options.flags': value}
    cfg.client.containers.get.return_value = container
    assert parse_flags(value) == result
