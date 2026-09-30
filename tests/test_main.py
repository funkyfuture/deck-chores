from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from apscheduler.job import Job
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from docker.models.containers import Container
from pytest import fixture, mark

from deck_chores.indexes import (
    container_name,
    lock_service,
    service_locks_by_container_id,
    service_locks_by_service_id,
)
from deck_chores.main import (
    find_other_container_for_service,
    inspect_running_containers,
    listen,
    process_started_container_labels,
    reassign_jobs,
    there_is_another_deck_chores_container,
    handle_die,
    handle_pause,
    handle_unpause,
)
from deck_chores.parsers import parse_job_definitions, parse_labels


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


@fixture
def replacement_service(cfg, mocker):
    scheduler = BackgroundScheduler(timezone="UTC")
    mocker.patch("deck_chores.jobs.scheduler", scheduler)
    containers = {}
    for container_id in ("old", "replacement"):
        containers[container_id] = SimpleNamespace(
            id=container_id,
            name=container_id,
            status="running",
            image=SimpleNamespace(labels={}),
            labels={
                "project_id": "foo",
                "service_id": "bar",
                "deck-chores.backup.command": "env",
                "deck-chores.backup.interval": "every minute",
            },
        )

    cfg.client.containers.get.side_effect = containers.__getitem__
    cfg.client.containers.list.side_effect = lambda **kwargs: [
        c for c in containers.values() if c.status == kwargs["filters"]["status"]
    ]
    container_name.cache_clear()
    parse_labels.cache_clear()
    scheduler.start(paused=True)
    yield scheduler, containers["old"], containers["replacement"]
    scheduler.shutdown()
    container_name.cache_clear()
    parse_labels.cache_clear()


@mark.parametrize("old_paused", (False, True))
@mark.parametrize("replacement_status", ("running", "paused"))
def test_reassign_jobs(replacement_service, old_paused, replacement_status):
    scheduler, old, replacement = replacement_service
    replacement.status = replacement_status
    process_started_container_labels(old.id, paused=old_paused)
    job = scheduler.get_jobs()[0]
    next_run_time = job.next_run_time

    assert reassign_jobs(old.id, consider_paused=True) == replacement.id

    assert scheduler.get_jobs() == [job]
    assert job.kwargs["container_id"] == replacement.id
    if replacement_status == "paused":
        assert job.next_run_time is None
    elif old_paused:
        assert job.next_run_time is not None
    else:
        assert job.next_run_time == next_run_time
    service_id = ("project_id=foo", "service_id=bar")
    assert service_locks_by_service_id[service_id] == replacement.id
    assert old.id not in service_locks_by_container_id

    assert reassign_jobs(replacement.id, consider_paused=True) == old.id
    assert scheduler.get_jobs() == [job]
    assert job.kwargs["container_id"] == old.id


@mark.parametrize("replacement_status", ("running", "paused"))
def test_reassign_jobs_uses_replacement_labels(replacement_service, replacement_status):
    scheduler, old, replacement = replacement_service
    process_started_container_labels(old.id)
    job_id = scheduler.get_jobs()[0].id
    old.status = "exited"
    replacement.status = replacement_status
    replacement.labels.update(
        {
            "deck-chores.backup.command": "echo changed",
            "deck-chores.backup.interval": "daily",
            "deck-chores.backup.user": "worker",
            "deck-chores.backup.workdir": "/backups",
            "deck-chores.backup.env.MODE": "daily",
            "deck-chores.backup.max": "2",
        }
    )

    handle_die({"Actor": {"ID": old.id}})
    if replacement_status == "running":
        process_started_container_labels(replacement.id)

    job = scheduler.get_job(job_id)
    assert job.kwargs["container_id"] == replacement.id
    assert job.kwargs["command"] == "echo changed"
    assert job.kwargs["user"] == "worker"
    assert job.kwargs["workdir"] == "/backups"
    assert job.kwargs["environment"] == {"MODE": "daily"}
    assert job.max_instances == 2
    assert job.trigger.interval == timedelta(days=1)
    assert (job.next_run_time is None) == (replacement_status == "paused")
    assert len(scheduler.get_jobs()) == 1


@mark.parametrize("add_replacement_job", (False, True))
def test_reassign_jobs_removes_old_definitions(
    replacement_service, add_replacement_job
):
    scheduler, old, replacement = replacement_service
    process_started_container_labels(old.id)
    job_id = scheduler.get_jobs()[0].id
    replacement.labels.pop("deck-chores.backup.command")
    replacement.labels.pop("deck-chores.backup.interval")
    if add_replacement_job:
        replacement.image.labels = {
            "deck-chores.cleanup.command": "echo cleanup",
            "deck-chores.cleanup.interval": "daily",
        }

    assert reassign_jobs(old.id, consider_paused=True) == replacement.id

    assert scheduler.get_job(job_id) is None
    assert len(scheduler.get_jobs()) == int(add_replacement_job)
    if add_replacement_job:
        job = scheduler.get_jobs()[0]
        assert job.name == "cleanup"
        assert job.kwargs["container_id"] == replacement.id
        assert job.kwargs["command"] == "echo cleanup"


def test_reassign_jobs_keeps_unchanged_schedule(replacement_service):
    scheduler, old, replacement = replacement_service
    process_started_container_labels(old.id)
    original_job = scheduler.get_jobs()[0]
    next_run_time = datetime(2030, 1, 2, tzinfo=timezone.utc)
    original_job.modify(next_run_time=next_run_time)
    replacement.labels.update(
        {
            "deck-chores.cleanup.command": "echo cleanup",
            "deck-chores.cleanup.interval": "daily",
        }
    )

    assert reassign_jobs(old.id, consider_paused=True) == replacement.id

    assert scheduler.get_job(original_job.id) is original_job
    assert original_job.next_run_time == next_run_time
    assert original_job.kwargs["container_id"] == replacement.id
    assert {job.name for job in scheduler.get_jobs()} == {"backup", "cleanup"}
