import logging
import json
import os
import sys
from functools import lru_cache
from typing import Tuple, Union
from uuid import NAMESPACE_OID, uuid5


def from_json(s: Union[bytes, str]) -> dict:
    if isinstance(s, bytes):
        s = s.decode()
    return json.loads(s)


@lru_cache(128)
def generate_id(*args) -> str:
    return str(uuid5(NAMESPACE_OID, ''.join(args)))


def split_string(
    value: str, delimiter: str = ',', strip: bool = True, sort: bool = False
) -> Tuple[str, ...]:
    result = []
    for part in value.split(delimiter):
        if strip:
            result.append(part.strip())
        else:
            result.append(part)
    if sort:
        result.sort()
    return tuple(result)


def trueish(value: str) -> bool:
    return value.strip().lower() in ('1', 'on', 'true', 'yes')


log = logging.getLogger('deck_chores')
log_handler = logging.StreamHandler(sys.stdout)
log.addHandler(log_handler)
log.setLevel(logging.DEBUG if trueish(os.getenv('DEBUG', 'no')) else logging.INFO)


__all__ = [
    from_json.__name__, 'log', 'log_handler', split_string.__name__, trueish.__name__
]
