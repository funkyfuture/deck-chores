from pathlib import Path

from docker.api import APIClient
from docker.client import DockerClient
import pytest

from deck_chores.indexes import (
    _service_locks_by_container_id,
    _service_locks_by_service_id,
)
from deck_chores.parsers import job_config_validator
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
    cfg.service_identifiers = split_string('project_id,service_id')
    cfg.timezone = 'UTC'

    job_config_validator.set_defaults(cfg)

    yield cfg


@pytest.fixture
def fixtures():
    return Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def sanitize_indexes():
    _service_locks_by_container_id.clear()
    _service_locks_by_service_id.clear()
