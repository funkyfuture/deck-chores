import json
from typing import Union
from uuid import NAMESPACE_OID, uuid5


def from_json(s: Union[bytes, str]) -> dict:
    if isinstance(s, bytes):
        s = s.decode()
    return json.loads(s)


def trueish(value: str) -> bool:
    return value.strip().lower() in ('1', 'on', 'true', 'yes')


def generate_job_id(container_id: str, job_name: str) -> str:
    return str(uuid5(NAMESPACE_OID, container_id + job_name))
