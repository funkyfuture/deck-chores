import ssl

import docker.client
from docker.constants import DEFAULT_TIMEOUT_SECONDS

import deck_chores.config


cfg, generate_config = deck_chores.config.cfg, deck_chores.config.generate_config


def test_default_config(monkeypatch):
    def docker_api_version(self):
        return '1.37'

    def every_file_exists(*args, **kwargs):
        return True

    monkeypatch.setenv('DEBUG', '0')
    monkeypatch.setattr(deck_chores.config, 'exists', every_file_exists)
    monkeypatch.setattr(
        docker.client.APIClient, '_retrieve_server_version', docker_api_version
    )

    generate_config()
    result = cfg.__dict__.copy()
    assert isinstance(result.pop('client'), docker.client.DockerClient)
    assert result == {
        'assert_hostname': False,
        'client_timeout': DEFAULT_TIMEOUT_SECONDS,
        'docker_host': 'unix://var/run/docker.sock',
        'debug': False,
        'default_max': 1,
        'default_flags': ('image', 'service'),
        'label_ns': 'deck-chores.',
        'logformat': '{asctime}|{levelname:8}|{message}',
        'service_identifiers': (
            'com.docker.compose.project',
            'com.docker.compose.service',
        ),
        'ssl_version': ssl.PROTOCOL_TLS,
        'timezone': 'UTC',
    }
