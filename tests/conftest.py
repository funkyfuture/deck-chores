from os import chdir, getenv
from subprocess import check_call, DEVNULL

import pytest

from tests.utils import PROJECT_DIR, ComposeProject


if getenv('TRAVIS') != 'true':

    chdir(str(PROJECT_DIR))
    check_call(['make', 'build-dev'], stdout=DEVNULL, stderr=DEVNULL)

    @pytest.fixture
    def deck_chores():
        dc = ComposeProject('deck-chores')
        yield dc
        dc.down()
