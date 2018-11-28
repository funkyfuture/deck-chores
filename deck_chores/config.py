import logging
from os import environ
from os.path import exists
import ssl
from types import SimpleNamespace

import docker
from docker.constants import DEFAULT_TIMEOUT_SECONDS

from deck_chores.exceptions import ConfigurationError
from deck_chores.utils import split_string, trueish


####


cfg = SimpleNamespace()
local_environment = environ.copy()
log = logging.getLogger('deck_chores')
getenv = local_environment.get


####


def _handle_deprecated():
    if 'DEFAULT_OPTIONS' in environ:
        environ['DEFAULT_FLAGS'] = environ.pop('DEFAULT_OPTIONS')
        log.warning(
            'The environment variable `DEFAULT_OPTIONS` was renamed to '
            '`DEFAULT_FLAGS`'
        )


def _resolve_tls_version(version: str) -> int:
    return getattr(ssl, 'PROTOCOL_' + version.replace('.', '_'))


def _test_daemon_socket(url: str) -> str:
    if url.startswith('unix:') and not exists(url[len('unix:/') :]):  # noqa: E203
        raise ConfigurationError(f'Docker socket file not found: {url}')

    return url


####


def generate_config() -> None:
    _handle_deprecated()
    cfg.__dict__.clear()
    cfg.assert_hostname = trueish(getenv('ASSERT_HOSTNAME', 'no'))
    cfg.client_timeout = int(getenv('CLIENT_TIMEOUT', DEFAULT_TIMEOUT_SECONDS))
    cfg.default_flags = split_string(
        getenv('DEFAULT_FLAGS', 'image,service'), sort=True
    )
    cfg.docker_host = _test_daemon_socket(
        getenv('DOCKER_HOST', 'unix://var/run/docker.sock')
    )
    cfg.debug = trueish(getenv('DEBUG', 'no'))
    cfg.default_max = int(getenv('DEFAULT_MAX', '1'))
    cfg.label_ns = getenv('LABEL_NAMESPACE', 'deck-chores') + '.'
    cfg.logformat = getenv('LOG_FORMAT', '{asctime}|{levelname:8}|{message}')
    cfg.service_identifiers = split_string(
        getenv(
            'SERVICE_ID_LABELS', 'com.docker.compose.project,com.docker.compose.service'
        )
    )
    cfg.ssl_version = _resolve_tls_version(getenv('SSL_VERSION', 'TLS'))
    cfg.timezone = getenv('TIMEZONE', 'UTC').replace(' ', '_')
    cfg.client = docker.from_env(
        version='auto',
        timeout=cfg.client_timeout,
        ssl_version=cfg.ssl_version,
        assert_hostname=cfg.assert_hostname,
        environment=local_environment,
    )


__all__ = ['cfg', generate_config.__name__]
