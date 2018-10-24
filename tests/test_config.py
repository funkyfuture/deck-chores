import ssl

from docker import DockerClient
from docker.constants import DEFAULT_TIMEOUT_SECONDS

from deck_chores.config import cfg, generate_config


def test_default_config(monkeypatch):
    monkeypatch.setenv('DEBUG', '0')
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
