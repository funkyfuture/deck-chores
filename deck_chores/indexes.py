from functools import lru_cache
from types import MappingProxyType
from typing import Dict, Tuple

from deck_chores.config import cfg, CONTAINER_CACHE_SIZE
from deck_chores.utils import log


####


@lru_cache(maxsize=CONTAINER_CACHE_SIZE)
def container_name(container_id: str) -> str:
    return cfg.client.containers.get(container_id).name


####


_service_locks_by_container_id: Dict[str, Tuple[str, ...]] = {}
service_locks_by_container_id = MappingProxyType(_service_locks_by_container_id)
_service_locks_by_service_id: Dict[Tuple[str, ...], str] = {}
service_locks_by_service_id = MappingProxyType(_service_locks_by_service_id)


def lock_service(service_id: Tuple[str, ...], container_id: str):
    assert service_id not in service_locks_by_service_id
    _service_locks_by_service_id[service_id] = container_id
    assert container_id not in service_locks_by_container_id
    _service_locks_by_container_id[container_id] = service_id
    log.debug(f"Added lock for service {service_id} on container {container_id}.")


def reassign_service_lock(old_container_id: str, new_container_id: str):
    service_id = _service_locks_by_container_id.pop(old_container_id)
    assert old_container_id not in service_locks_by_container_id
    assert new_container_id not in service_locks_by_container_id
    _service_locks_by_container_id[new_container_id] = service_id
    assert service_id in service_locks_by_service_id
    _service_locks_by_service_id[service_id] = new_container_id
    log.debug(
        f"Reassigned lock for service {service_id} from container {old_container_id} "
        f"to {new_container_id}."
    )


def unlock_service(container_id: str):
    service_id = _service_locks_by_container_id.pop(container_id, None)
    if service_id is None:
        return
    _service_locks_by_service_id.pop(service_id)
    log.debug(f"Removed lock for service {service_id} on container {container_id}.")


__all__ = (
    "service_locks_by_container_id",
    "service_locks_by_service_id",
    lock_service.__name__,
    reassign_service_lock.__name__,
    unlock_service.__name__,
)
