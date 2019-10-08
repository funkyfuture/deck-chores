from datetime import datetime

from pytest import mark

from apscheduler.triggers.interval import IntervalTrigger
from docker.models.containers import Container

from deck_chores.main import listen, there_is_another_deck_chores_container
from deck_chores.parsers import parse_job_definitions


def test_event_dispatching(cfg, fixtures, mocker):
    cfg.client.events.return_value = (
        (fixtures / "events_00.txt").read_bytes().splitlines()
    )

    definition = parse_job_definitions(
        {'deck-chores.beep.command': '/beep.sh', 'deck-chores.beep.interval': '10m'},
        user="",
    )
    parse_labels = mocker.patch(
        'deck_chores.main.parse_labels',
        return_value=(
            ("com.docker.compose.project=sojus", "com.docker.compose.service=beep"),
            'service',
            definition,
        ),
    )

    call_recorder = mocker.Mock()
    call_recorder.attach_mock(parse_labels, "parse_labels")
    call_recorder.attach_mock(mocker.patch("deck_chores.jobs.add"), "add")
    call_recorder.attach_mock(
        mocker.patch("deck_chores.main.reassign_jobs"), "reassign_jobs"
    )

    listen(datetime.utcnow())

    _ = mocker.call
    expected_calls = [
        # start A
        _.parse_labels(
            "cbac46d62ceec9e1d920ed4eb2dcb18f7426ab7ae8e5e8f7b7b0a01cacdce5ed"
        ),
        _.add(
            'cbac46d62ceec9e1d920ed4eb2dcb18f7426ab7ae8e5e8f7b7b0a01cacdce5ed',
            {
                'beep': {
                    'command': '/beep.sh',
                    'name': 'beep',
                    'environment': {},
                    'jitter': None,
                    'max': 1,
                    'timezone': 'UTC',
                    'trigger': (IntervalTrigger, (0, 0, 0, 10, 0)),
                    'user': '',
                }
            },
            paused=False,
        ),
        # start B
        _.parse_labels(
            "278ed6f4ebac945e50fda4266d3d6bafef47a09fd874127902a20684e9c57b91"
        ),
        # pause A
        _.reassign_jobs(
            "cbac46d62ceec9e1d920ed4eb2dcb18f7426ab7ae8e5e8f7b7b0a01cacdce5ed",
            consider_paused=False,
        ),
        # unpause A
        # stop B
        _.reassign_jobs(
            "278ed6f4ebac945e50fda4266d3d6bafef47a09fd874127902a20684e9c57b91",
            consider_paused=True,
        ),
        # start B
        _.parse_labels(
            "278ed6f4ebac945e50fda4266d3d6bafef47a09fd874127902a20684e9c57b91"
        ),
        # stop A
        _.reassign_jobs(
            "cbac46d62ceec9e1d920ed4eb2dcb18f7426ab7ae8e5e8f7b7b0a01cacdce5ed",
            consider_paused=True,
        ),
        # pause B
        _.reassign_jobs(
            "278ed6f4ebac945e50fda4266d3d6bafef47a09fd874127902a20684e9c57b91",
            consider_paused=False,
        ),
        # start A
        _.parse_labels(
            "cbac46d62ceec9e1d920ed4eb2dcb18f7426ab7ae8e5e8f7b7b0a01cacdce5ed"
        ),
        # stop A
        _.reassign_jobs(
            "cbac46d62ceec9e1d920ed4eb2dcb18f7426ab7ae8e5e8f7b7b0a01cacdce5ed",
            consider_paused=True,
        ),
    ]

    # actual_calls = call_recorder.mock_calls
    # for i, (act, exp) in enumerate(zip(actual_calls, expected_calls)):
    #     assert act == exp, (i, act, exp)
    # if len(expected_calls) < len(actual_calls):
    #     raise AssertionError(f"Unexpected call: {actual_calls[len(expected_calls)]}")
    # elif len(actual_calls) < len(expected_calls):
    #     raise AssertionError(f"Missed call: {expected_calls[len(actual_calls)]}")

    assert call_recorder.mock_calls == expected_calls


@mark.parametrize(
    'has_label_seq, exp_result', (([True, False, True], True), ([True, False], False))
)
def test_deck_chores_container_check(cfg, mocker, has_label_seq, exp_result):
    containers = []
    for x in has_label_seq:
        containers.append(mocker.MagicMock(Container))
        containers[-1].image.labels = (
            {'org.label-schema.name': 'deck-chores'} if x else {}
        )
    cfg.client.containers.list.return_value = containers

    assert there_is_another_deck_chores_container() == exp_result
