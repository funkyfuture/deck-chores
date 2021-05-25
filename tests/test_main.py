from datetime import datetime
from types import SimpleNamespace

from apscheduler.job import Job
from apscheduler.triggers.interval import IntervalTrigger
from docker.models.containers import Container
from pytest import mark

from deck_chores.indexes import lock_service
from deck_chores.main import (
    find_other_container_for_service,
    inspect_running_containers,
    listen,
    reassign_jobs,
    there_is_another_deck_chores_container,
    handle_die,
    handle_pause,
    handle_unpause,
)
from deck_chores.parsers import parse_job_definitions


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


def test_find_other_container_for_service(cfg, mocker):
    lock_service(("project_id=foo", "service_id=bar"), "a")
    cfg.client.containers.list.side_effect = [
        [],
        [],
        [
            SimpleNamespace(id="a", status="paused"),
            SimpleNamespace(id="b", status="paused"),
        ],
    ]

    result = find_other_container_for_service("a", consider_paused=True)
    assert result.id == "b"
    assert result.status == "paused"

    cfg.client.containers.list.assert_has_calls(
        [
            mocker.call(
                all=True,
                ignore_removed=True,
                filters={
                    "status": "running",
                    "label": ["project_id=foo", "service_id=bar"],
                },
            ),
            mocker.call(
                all=True,
                ignore_removed=True,
                filters={
                    "status": "restarting",
                    "label": ["project_id=foo", "service_id=bar"],
                },
            ),
            mocker.call(
                all=True,
                ignore_removed=True,
                filters={
                    "status": "paused",
                    "label": ["project_id=foo", "service_id=bar"],
                },
            ),
        ]
    )


def test_handle_die(mocker):
    mocker.patch("deck_chores.main.reassign_jobs", mocker.Mock(return_value=None))
    job = mocker.MagicMock(spec_set=Job)
    mocker.patch(
        "deck_chores.jobs.get_jobs_for_container", mocker.Mock(return_value=[job])
    )

    handle_die({"Actor": {"ID": "a"}})

    job.remove.assert_called_once()


def test_handle_pause(mocker):
    mocker.patch("deck_chores.main.reassign_jobs", mocker.Mock(return_value=None))
    job = mocker.MagicMock(spec_set=Job)
    mocker.patch(
        "deck_chores.jobs.get_jobs_for_container", mocker.Mock(return_value=[job])
    )

    handle_pause({"Actor": {"ID": "a"}})

    job.pause.assert_called_once()


def test_handle_unpause(cfg, mocker):
    service_id = ("project_id=foo", "service_id=bar")

    lock_service(service_id, "a")
    mocker.patch(
        "deck_chores.main.parse_labels",
        mocker.Mock(return_value=(service_id, None, None)),
    )
    cfg.client.containers.get.return_value = SimpleNamespace(id="a", status="paused")
    mocker.patch("deck_chores.main.reassign_jobs", mocker.Mock(return_value="b"))
    get_jobs_for_container = mocker.Mock(return_value=[])
    mocker.patch("deck_chores.jobs.get_jobs_for_container", get_jobs_for_container)

    handle_unpause({"Actor": {"ID": "b"}})

    cfg.client.containers.get.assert_called_once_with("a")
    get_jobs_for_container.assert_called_once_with("b")


def test_inspect_running_containers(cfg, mocker):
    container = SimpleNamespace(id="a", status="running")
    cfg.client.containers.list.return_value = [container]
    cfg.client.api.inspect_container.return_value = {
        "State": {"StartedAt": "3000-01-02T01:02:03.456789Z"}
    }

    process_started_container_labels = mocker.MagicMock()
    mocker.patch(
        "deck_chores.main.process_started_container_labels",
        process_started_container_labels,
    )

    assert inspect_running_containers() == datetime(
        year=3000, month=1, day=2, hour=1, minute=2, second=3, microsecond=456789
    )

    process_started_container_labels.assert_called_once_with("a", paused=False)


@mark.parametrize(
    ("container_status", "job_next_run_time", "expected_job_call"),
    (
        ("running", None, "resume"),
        ("paused", None, ""),
        ("paused", datetime(year=1, month=2, day=3), "pause"),
    ),
)
def test_reassign_jobs(
    cfg, mocker, container_status, job_next_run_time, expected_job_call
):
    container = mocker.MagicMock(spec_set=Container)
    container.status = container_status
    container.id = "b"

    find_other_container_for_service = mocker.MagicMock(return_value=container)
    mocker.patch(
        "deck_chores.main.find_other_container_for_service",
        find_other_container_for_service,
    )

    job = mocker.MagicMock(spec_set=Job)
    job.next_run_time = job_next_run_time
    get_jobs_for_container = mocker.Mock(return_value=(job,))
    mocker.patch("deck_chores.jobs.get_jobs_for_container", get_jobs_for_container)

    lock_service(("project_id=foo", "service_id=bar"), "a")

    assert reassign_jobs("a", consider_paused=True) == "b"
    find_other_container_for_service.assert_called_once_with("a", True)

    get_jobs_for_container.assert_called_once_with("a")
    if expected_job_call:
        getattr(job, expected_job_call).assert_called_once()
    job.modify.assert_called_once_with(kwargs={"container_id": "b"})
