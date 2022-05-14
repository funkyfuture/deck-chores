import logging
import os
import sys
from functools import lru_cache
from types import SimpleNamespace
from typing import Optional, Tuple
from uuid import NAMESPACE_DNS, uuid5


TIME_UNIT_MULTIPLIERS = {
    's': 1,
    'm': 1 * 60,
    'h': 1 * 60 * 60,
    'd': 1 * 60 * 60 * 24,
    'w': 1 * 60 * 60 * 24 * 7,
}
UUID_NAMESPACE = uuid5(NAMESPACE_DNS, "deck-chores.readthedocs.io")


class ExcludeErrorsFilter(logging.Filter):
    def __init__(self, stderr_level: int):
        self.threshold = stderr_level

    def filter(self, record):
        return record.levelno < self.threshold


@lru_cache(maxsize=64)
def generate_id(*args) -> str:
    return str(uuid5(UUID_NAMESPACE, ''.join(args)))


@lru_cache(maxsize=64)
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


@lru_cache(maxsize=64)
def seconds_as_interval_tuple(value: int) -> Tuple[int, int, int, int, int]:
    weeks, value = divmod(value, TIME_UNIT_MULTIPLIERS['w'])
    days, value = divmod(value, TIME_UNIT_MULTIPLIERS['d'])
    hours, value = divmod(value, TIME_UNIT_MULTIPLIERS['h'])
    minutes, value = divmod(value, TIME_UNIT_MULTIPLIERS['m'])
    return weeks, days, hours, minutes, value


def configure_logging(cfg: SimpleNamespace):  # pragma: nocover
    log_formatter = logging.Formatter(cfg.logformat, style='{')
    stdout_log_handler.setFormatter(log_formatter)

    if not cfg.stderr_level:
        return

    stderr_log_handler = logging.StreamHandler(sys.stderr)
    stderr_log_handler.setLevel(cfg.stderr_level)
    stderr_log_handler.setFormatter(log_formatter)
    log.addHandler(stderr_log_handler)
    stdout_log_handler.addFilter(ExcludeErrorsFilter(cfg.stderr_level))


def split_string(
    value: str, delimiter: str = ',', sort: bool = False
) -> Tuple[str, ...]:
    result = [x.strip() for x in value.split(delimiter)]
    if sort:
        result.sort()
    return tuple(result)


def trueish(value: str) -> bool:
    return value.strip().lower() in ('1', 'on', 'true', 'yes')


DEBUG = trueish(os.getenv('DEBUG', 'no'))

log = logging.getLogger('deck_chores')
stdout_log_handler = logging.StreamHandler(sys.stdout)
log.addHandler(stdout_log_handler)
log.setLevel(logging.DEBUG if DEBUG else logging.INFO)


# TODO remove ignore when this issue is solved:
#      https://github.com/python/mypy/issues/1317
__all__ = (
    'log',
    parse_time_from_string_with_units.__name__,  # type: ignore
    seconds_as_interval_tuple.__name__,  # type: ignore
    split_string.__name__,  # type: ignore
    trueish.__name__,
)
