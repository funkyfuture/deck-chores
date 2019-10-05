from types import MappingProxyType
from typing import Dict, Optional, Tuple

from docker.models.containers import Container

from deck_chores.config import cfg
from deck_chores.utils import log


ServiceIdentifier = Tuple[str, ...]


_service_id_to_container_id: Dict[ServiceIdentifier, str] = {}
service_id_to_container_id = MappingProxyType(_service_id_to_container_id)
_container_id_to_service_id: Dict[str, ServiceIdentifier] = {}
container_id_to_service_id = MappingProxyType(_container_id_to_service_id)


def assign(service_id: ServiceIdentifier, container_id: str):
    assert service_id not in service_id_to_container_id
    _service_id_to_container_id[service_id] = container_id
    assert container_id not in container_id_to_service_id
    _container_id_to_service_id[container_id] = service_id
    log.debug(f"Added lock for service {service_id} on container {container_id}.")


def find_other_container_for_service(
    container_id: str, consider_paused: bool
) -> Optional[Container]:
    service_id = container_id_to_service_id.get(container_id)
    if service_id is None:
        return None

    for status in (
        ("running", "restarting", "paused", "created")  # type: ignore
        if consider_paused
        else ("running", "restarting")
    ):
        candidates = [
            c
            for c in cfg.client.containers.list(
                all=True,
                ignore_removed=True,
                # TODO don't cast service_id to list when this patch is incorporated:
                #      https://github.com/docker/docker-py/pull/2445
                filters={"status": status, "label": list(service_id)},
            )
            if c.id != container_id
        ]

        if len(candidates):
            return candidates[0]

    return None


def reassign_container(old_container_id: str, new_container_id: str):
    service_id = _container_id_to_service_id.pop(old_container_id)
    assert old_container_id not in container_id_to_service_id
    assert new_container_id not in container_id_to_service_id
    _container_id_to_service_id[new_container_id] = service_id
    assert service_id in service_id_to_container_id
    _service_id_to_container_id[service_id] = new_container_id
    log.debug(
        f"Reassigned lock for service {service_id} from container {old_container_id} "
        f"to {new_container_id}."
    )


def remove_by_container_id(container_id: str):
    service_id = _container_id_to_service_id.pop(container_id, None)
    if service_id is None:
        return
    _service_id_to_container_id.pop(service_id)
    log.debug(f"Removed lock for service {service_id} on container {container_id}.")


__all__ = (
    "container_id_to_service_id",
    "service_id_to_container_id",
    assign.__name__,
    find_other_container_for_service.__name__,
    reassign_container.__name__,
    remove_by_container_id.__name__,
)
