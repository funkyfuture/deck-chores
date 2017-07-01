from os import chdir, getenv
from subprocess import check_call, DEVNULL

from docker.api import APIClient
from docker.client import DockerClient
import pytest

from deck_chores.utils import split_string
from tests.utils import PROJECT_DIR, ComposeProject


@pytest.fixture
def cfg(mocker):
    from deck_chores.config import cfg
    cfg.client = mocker.MagicMock(DockerClient)
    cfg.client.api = mocker.MagicMock(APIClient)
    cfg.debug = True
    cfg.default_max = 1
    cfg.default_options = 'image,service'
    cfg.default_user = 'root'
    cfg.label_ns = 'deck-chores.'
    cfg.service_identifiers = split_string('com.docker.compose.project,com.docker.compose.service')
    cfg.timezone = 'UTC'
    yield cfg


if getenv('TRAVIS') != 'true':

    chdir(str(PROJECT_DIR))
    check_call(['make', 'build-dev'], stdout=DEVNULL, stderr=DEVNULL)

    @pytest.fixture
    def deck_chores():
        dc = ComposeProject('deck-chores')
        yield dc
        dc.down()
