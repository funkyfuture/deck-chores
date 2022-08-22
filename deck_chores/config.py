import logging
import ssl
from os import environ
from os.path import exists
from types import SimpleNamespace

import docker
from docker.constants import DEFAULT_TIMEOUT_SECONDS

from deck_chores.utils import split_string, trueish


####


cfg = SimpleNamespace()
local_environment = environ.copy()
log = logging.getLogger('deck_chores')
getenv = local_environment.get


####


CONTAINER_CACHE_SIZE = int(getenv("CONTAINER_CACHE_SIZE", "128"))


class ConfigurationError(Exception):
    pass


def _check_docker_api(client: docker.DockerClient) -> docker.DockerClient:
    try:  # pragma: nocover
        if not client.ping():
            log.error(
                "The Docker daemon replied unexpected content on the /ping endpoint."
            )
            raise SystemExit(1)
    except docker.errors.APIError:  # pragma: nocover
        log.exception("Docker daemon error:")
        raise SystemExit(1)

    return client


def _handle_deprecated():
    if local_environment.pop("SSL_VERSION", None) is not None:
        log.warning(
            "The environment variable `SSL_VERSION` has no effect. "
            "The used protocol is negotiated by the Docker client library. "
            "In a future version this warning will disappear."
        )


def _resolve_tls_version(version: str) -> int:
    return getattr(ssl, 'PROTOCOL_' + version.replace('.', '_'))


def _test_daemon_socket(url: str) -> str:  # pragma: nocover
    if url.startswith("unix:") and not exists(url.removeprefix("unix:/")):
        raise ConfigurationError(f'Docker socket file not found: {url}')

    return url


####


def generate_config() -> None:
    cfg.__dict__.clear()
    _handle_deprecated()
    cfg.assert_hostname = trueish(getenv('ASSERT_HOSTNAME', 'no'))
    cfg.client_timeout = int(getenv('CLIENT_TIMEOUT', DEFAULT_TIMEOUT_SECONDS))
    cfg.default_flags = split_string(
        getenv('DEFAULT_FLAGS', 'image,service'), sort=True
    )
    cfg.docker_host = _test_daemon_socket(
        getenv('DOCKER_HOST', 'unix://var/run/docker.sock')
    )
    cfg.debug = trueish(getenv('DEBUG', 'no'))
    cfg.default_max = int(getenv('DEFAULT_MAX', 1))
    cfg.job_executor_pool_size = int(getenv('JOB_POOL_SIZE', 10))
    cfg.job_name_regex = getenv("JOB_NAME_REGEX", "[a-z0-9-]+")
    cfg.label_ns = getenv('LABEL_NAMESPACE', 'deck-chores') + '.'
    cfg.logformat = getenv('LOG_FORMAT', '{asctime}|{levelname:8}|{message}')
    cfg.service_identifiers = split_string(
        getenv(
            'SERVICE_ID_LABELS', 'com.docker.compose.project,com.docker.compose.service'
        )
    )
    cfg.stderr_level = logging.getLevelName(getenv('STDERR_LEVEL', 'NOTSET'))
    cfg.timezone = getenv('TIMEZONE', 'UTC').replace(' ', '_')
    cfg.client = _check_docker_api(
        docker.from_env(
            version='auto',
            timeout=cfg.client_timeout,
            assert_hostname=cfg.assert_hostname,
            environment=local_environment,
        )
    )


__all__ = ('cfg', generate_config.__name__, ConfigurationError.__name__)
