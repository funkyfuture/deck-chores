import json
from typing import Tuple, Union
from uuid import NAMESPACE_OID, uuid5


def split_string(value: str, delimiter: str = ',', strip: bool = True,
                 sort: bool = False) -> Tuple[str, ...]:
    result = []
    for part in value.split(delimiter):
        if strip:
            result.append(part.strip())
        else:
            result.append(part)
    if sort:
        result.sort()
    return tuple(result)


def from_json(s: Union[bytes, str]) -> dict:
    if isinstance(s, bytes):
        s = s.decode()
    return json.loads(s)


def trueish(value: str) -> bool:
    return value.strip().lower() in ('1', 'on', 'true', 'yes')


def generate_id(*args) -> str:
    return str(uuid5(NAMESPACE_OID, ''.join(args)))
