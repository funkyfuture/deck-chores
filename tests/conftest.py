from docker.api import APIClient
from docker.client import DockerClient
import pytest

from deck_chores.utils import split_string


@pytest.fixture
def cfg(mocker):
    from deck_chores.config import cfg

    cfg.client = mocker.MagicMock(DockerClient)
    cfg.client.api = mocker.MagicMock(APIClient)
    cfg.debug = True
    cfg.default_max = 1
    cfg.default_flags = split_string('image,service', sort=True)
    cfg.default_user = 'root'
    cfg.label_ns = 'deck-chores.'
    cfg.service_identifiers = split_string(
        'com.docker.compose.project,com.docker.compose.service'
    )
    cfg.timezone = 'UTC'
    yield cfg
