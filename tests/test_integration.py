from pathlib import Path
from time import sleep

import pytest

from tests.utils import ComposeProject


pytestmark = pytest.mark.skipif("os.getenv('TRAVIS') == 'true'",
                                reason='No Docker client available.')


def test_sojus(deck_chores, tmpdir):
    sojus_receiver = Path(str(tmpdir)) / 'receiver.txt'
    sojus_receiver.touch()
    assert sojus_receiver.is_file()
    sojus = ComposeProject('sojus', env={'OUTFILE': str(sojus_receiver)})
    sleep(14)
    sojus.down()

    with sojus_receiver.open() as f:
        beeps = f.readlines()
    assert len(beeps) == 3

    logs = deck_chores.logs
    print('\n'.join(logs))
    while True:
        if logs.pop(0) == "INFO: Locking service id: 77be5c25-c846-5d77-a5b1-863d16b9d0a9":
            break
    assert logs.pop(0) == "INFO: Added 'beep' for /sojus_beep_1"
    assert logs.pop(0) == "INFO: Executing 'beep' in /sojus_beep_1"
    assert logs.pop(0) == "INFO: Command /beep.sh in /sojus_beep_1 finished with exit code 0"
    assert logs.pop(0) == "INFO: == BEGIN of output =="
    assert logs.pop(0) == "INFO: Beeped 3 times"
    assert logs.pop(0) == "INFO: == END of output ===="
    assert logs.pop(0) == "INFO: Unlocking service id: 77be5c25-c846-5d77-a5b1-863d16b9d0a9"
    assert logs.pop(0) == "INFO: Removing job 'beep' for /sojus_beep_1"
