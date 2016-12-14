from os import chdir, getenv
from subprocess import check_call, DEVNULL

import pytest

from tests.utils import PROJECT_DIR, ComposeProject


def nada(*args, **kwargs):
    pass


@pytest.fixture(autouse=True)
def config(mocker):
    mocker.patch('deck_chores.config.Client.__init__', nada)
    mocker.patch('deck_chores.config._setup_tls_config', lambda: None)
    mocker.patch('deck_chores.config._test_daemon_socket', lambda x: x)
    from deck_chores.config import generate_config
    generate_config()


if getenv('TRAVIS') != 'true':

    chdir(str(PROJECT_DIR))
    check_call(['make', 'build-dev'], stdout=DEVNULL, stderr=DEVNULL)

    @pytest.fixture
    def deck_chores():
        dc = ComposeProject('deck-chores')
        yield dc
        dc.down()
