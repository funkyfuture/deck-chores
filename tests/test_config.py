import os.path
import ssl

from docker import DockerClient
from docker.constants import DEFAULT_TIMEOUT_SECONDS

import deck_chores.config


cfg, generate_config = deck_chores.config.cfg, deck_chores.config.generate_config


def test_default_config(monkeypatch):
    def every_file_exists(*args, **kwargs):
        return True

    monkeypatch.setenv('DEBUG', '0')
    monkeypatch.setattr(deck_chores.config, 'exists', every_file_exists)
    generate_config()
    result = cfg.__dict__.copy()
    assert isinstance(result.pop('client'), DockerClient)
    assert result == {
        'assert_hostname': False,
        'client_timeout': DEFAULT_TIMEOUT_SECONDS,
        'docker_host': 'unix://var/run/docker.sock',
        'debug': False,
        'default_max': 1,
        'default_options': ('image', 'service'),
        'default_user': 'root',
        'label_ns': 'deck-chores.',
        'logformat': '{asctime}|{levelname:8}|{message}',
        'service_identifiers': ('com.docker.compose.project',
                                'com.docker.compose.service'),
        'ssl_version': ssl.PROTOCOL_TLS,
        'timezone': 'UTC'
    }
