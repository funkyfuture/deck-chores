from os import getenv
from os.path import exists, isfile
import ssl
from types import SimpleNamespace

from docker import Client  # type: ignore
from docker.tls import TLSConfig  # type: ignore

from deck_chores.exceptions import ConfigurationError
from deck_chores.utils import trueish


####


cfg = SimpleNamespace()


####


def _register_exsiting_files() -> None:
    for name, filename in (('ca_cert', 'ca.pem'), ('client_cert', 'cert.pem'),
                           ('client_key', 'key.pem')):
        path = '/config/' + filename
        setattr(cfg, name, path if isfile(path) else None)


def _resolve_tls_version(version: str) -> int:
    return getattr(ssl, 'PROTOCOL_' + version.replace('.', '_'))


def _setup_tls_config() -> None:
    # https://docker-py.readthedocs.io/en/stable/tls/#TLSConfig
    if cfg.client_cert is not None or cfg.ca_cert is not None:
        cfg.tls_config = TLSConfig(client_cert=(cfg.client_cert, cfg.client_key),
                                   ca_cert=cfg.ca_cert,
                                   verify=True if cfg.ca_cert else False,
                                   ssl_version=cfg.ssl_version,
                                   assert_hostname=cfg.assert_hostname,
                                   assert_fingerprint=cfg.assert_fingerprint)
    else:
        cfg.tls_config = None


def _test_daemon_socket(url: str) -> str:
    if url.startswith('unix:') and not exists(url[len('unix:/'):]):
        raise ConfigurationError('Docker socket file not found: %s' % url)
    return url


####


def generate_config() -> None:
    cfg.assert_fingerprint = trueish(getenv('ASSERT_FINGERPRINT', 'no'))
    cfg.assert_hostname = trueish(getenv('ASSERT_HOSTNAME', 'no'))
    cfg.client_timeout = int(getenv('CLIENT_TIMEOUT', '120'))
    cfg.daemon_url = _test_daemon_socket(getenv('DOCKER_DAEMON', 'unix://var/run/docker.sock'))
    cfg.debug = trueish(getenv('DEBUG', 'no'))
    cfg.default_max = int(getenv('DEFAULT_MAX', '1'))
    cfg.default_user = getenv('DEFAULT_USER', 'root')
    cfg.label_ns = getenv('LABEL_NAMESPACE', 'deck-chores') + '.'
    cfg.ssl_version = _resolve_tls_version(getenv('SSL_VERSION', 'TLS'))
    cfg.timezone = getenv('TIMEZONE', 'UTC').replace(' ', '_')

    _register_exsiting_files()
    _setup_tls_config()
    cfg.client = Client(base_url=cfg.daemon_url,
                        version='auto',
                        timeout=cfg.client_timeout,
                        tls=cfg.tls_config)


__all__ = ['cfg', generate_config.__name__]
