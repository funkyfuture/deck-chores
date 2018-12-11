import logging
import json
import os
import sys
from functools import lru_cache
from typing import Optional, Tuple, Union
from uuid import NAMESPACE_OID, uuid5


TIME_UNIT_MULTIPLIERS = {
    's': 1,
    'm': 1 * 60,
    'h': 1 * 60 * 60,
    'd': 1 * 60 * 60 * 24,
    'w': 1 * 60 * 60 * 24 * 7,
}


def from_json(s: Union[bytes, str]) -> dict:
    if isinstance(s, bytes):
        s = s.decode()
    return json.loads(s)


@lru_cache(128)
def generate_id(*args) -> str:
    return str(uuid5(NAMESPACE_OID, ''.join(args)))


@lru_cache(64)
def parse_time_from_string_with_units(value: str) -> Optional[int]:
    digits: str = ''
    result: float = 0
    ignore: bool = False

    try:
        for char in value:

            if char.isdigit() or char == '.':
                ignore = False
                digits += char
                continue

            if ignore:
                continue

            char = char.lower()
            if char in TIME_UNIT_MULTIPLIERS and digits:
                if digits.startswith('.'):
                    digits = '0' + digits

                result += TIME_UNIT_MULTIPLIERS[char] * float(digits)
                digits, ignore = '', True

            if char.isalpha():
                ignore = True

    except (TypeError, ValueError):
        return None

    return int(result)


@lru_cache(64)
def seconds_as_interval_tuple(value: int) -> Tuple[int, int, int, int, int]:
    weeks, value = divmod(value, TIME_UNIT_MULTIPLIERS['w'])
    days, value = divmod(value, TIME_UNIT_MULTIPLIERS['d'])
    hours, value = divmod(value, TIME_UNIT_MULTIPLIERS['h'])
    minutes, value = divmod(value, TIME_UNIT_MULTIPLIERS['m'])
    return weeks, days, hours, minutes, value


@lru_cache(4)
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
    from_json.__name__,
    'log',
    'log_handler',
    # https://github.com/python/mypy/issues/1317
    parse_time_from_string_with_units.__name__,  # type: ignore
    seconds_as_interval_tuple.__name__,  # type: ignore
    split_string.__name__,  # type: ignore
    trueish.__name__,
]
