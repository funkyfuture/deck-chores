from collections import defaultdict
from functools import lru_cache
from typing import DefaultDict, Dict, Mapping, Optional, Tuple, Type, Union

import cerberus
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import all_timezones

from deck_chores.config import cfg, CONTAINER_CACHE_SIZE
from deck_chores.utils import (
    log,
    parse_time_from_string_with_units,
    seconds_as_interval_tuple,
    split_string,
)


####


CRON_TRIGGER_FIELDS_COUNT = len(CronTrigger.FIELD_NAMES)
NAME_INTERVAL_MAP = {
    'weekly': (1, 0, 0, 0, 0),
    'daily': (0, 1, 0, 0, 0),
    'hourly': (0, 0, 1, 0, 0),
    'every minute': (0, 0, 0, 1, 0),
    'every second': (0, 0, 0, 0, 1),
}


####


class JobConfigValidator(cerberus.Validator):
    def set_defaults(self, cfg):
        schema = self.schema
        schema["max"]["default"] = cfg.default_max
        schema["timezone"]["default"] = cfg.timezone
        schema.validate()

    @staticmethod
    @lru_cache(128)
    def _fill_args(value: str, length: int, filling: str) -> Tuple[str, ...]:
        value = value.strip()
        while '  ' in value:
            value = value.replace('  ', ' ')
        tokens = value.split(' ')
        return tuple([filling] * (length - len(tokens)) + tokens)

    def _normalize_coerce_cron(self, value: str) -> Tuple[Type, Tuple[str, ...]]:
        args = self._fill_args(value, CRON_TRIGGER_FIELDS_COUNT, '*')
        return CronTrigger, args

    def _normalize_coerce_date(self, value: str) -> Tuple[Type, Tuple[str]]:
        return DateTrigger, (value,)

    def _normalize_coerce_interval(
        self, value: str
    ) -> Tuple[Type, Optional[Tuple[int, int, int, int, int]]]:
        args = NAME_INTERVAL_MAP.get(value)
        if args is None:
            if any(x.isalpha() for x in value):
                parsed_value = parse_time_from_string_with_units(value)
                if parsed_value:
                    args = seconds_as_interval_tuple(parsed_value)
            else:
                for c in '.:/':
                    value = value.replace(c, ' ')
                filled_args = self._fill_args(value, 5, '0')
                args = tuple(int(x) for x in filled_args)  # type: ignore
        return IntervalTrigger, args

    def _normalize_coerce_timeunits(self, value: str) -> Optional[int]:
        if any(x.isalpha() for x in value):
            return parse_time_from_string_with_units(value)
        return int(value)

    def _check_with_trigger(self, field, value):
        if isinstance(value, str):  # normalization failed
            return

        trigger_class, args = value[0], value[1]
        try:
            trigger_class(*args, timezone=self.document.get('timezone', cfg.timezone))
        except Exception as e:
            message = (
                f"Error while instantiating a {trigger_class.__name__} with '{args}'."
            )
            if cfg.debug:
                message += f"\n{e}"
            self._error(field, message)


job_config_validator = JobConfigValidator(
    {
        'command': {'required': True},
        'cron': {
            'coerce': 'cron',
            'check_with': 'trigger',
            'required': True,
            'excludes': ['date', 'interval'],
        },
        'date': {
            'coerce': 'date',
            'check_with': 'trigger',
            'required': True,
            'excludes': ['cron', 'interval'],
        },
        'environment': {'type': 'dict', 'default': {}},
        'interval': {
            'coerce': 'interval',
            'check_with': 'trigger',
            'required': True,
            'excludes': ['cron', 'date'],
        },
        'jitter': {
            'type': 'integer',
            'coerce': 'timeunits',
            'nullable': True,
            'default': None,
            'min': 0,
        },
        'max': {'coerce': int},  # default is set later
        'name': {'regex': r'[a-z0-9-]+', "required": True},
        'timezone': {'allowed': all_timezones},  # default is set later
        'user': {
            "empty": True,
            'regex': r'[a-zA-Z0-9_.][a-zA-Z0-9_.-]*',
            "required": True,
        },
        'workdir': {'regex': r'/.*'},
    }
)


####


@lru_cache(maxsize=CONTAINER_CACHE_SIZE)
def parse_labels(container_id: str) -> Tuple[Tuple[str, ...], str, Dict[str, Dict]]:
    labels = cfg.client.containers.get(container_id).labels
    log.debug(f'Parsing labels: {labels}')

    service_id = parse_service_id(labels)

    filtered_labels = {k: v for k, v in labels.items() if k.startswith(cfg.label_ns)}
    flags, user = parse_options(filtered_labels)

    if 'image' in flags:
        image_labels = image_definition_labels_of_container(container_id)
        user = user or parse_options(image_labels)[1]
    else:
        image_labels = {}

    job_definitions = parse_job_definitions(image_labels | filtered_labels, user)

    if service_id:
        log.debug(f'Assigning service id: {service_id}')
        for job_definition in job_definitions.values():
            job_definition['service_id'] = service_id
    return service_id, flags, job_definitions


def parse_options(labels: Dict[str, str]) -> Tuple[str, str]:
    flags = parse_flags(labels.pop("options.flags", ""))
    user = labels.pop(cfg.label_ns + "options.user", "")
    return flags, user


@lru_cache(maxsize=16)
def parse_flags(options: str) -> str:
    result = set(cfg.default_flags)
    if options:
        for option in split_string(options):
            if option.startswith("no"):
                result.discard(option.removeprefix("no"))
            else:
                result.add(option)
    result_string = ','.join(sorted(result))
    log.debug(f'Parsed & resolved container flags: {result_string}')
    return result_string


def parse_service_id(labels: Dict[str, str]) -> Tuple[str, ...]:
    filtered_labels = {k: v for k, v in labels.items() if k in cfg.service_identifiers}
    log.debug(f'Considering labels for service id: {filtered_labels}')
    if not filtered_labels:
        return ()

    if len(filtered_labels) != len(cfg.service_identifiers):
        log.critical(
            'Missing service identity labels: {}'.format(
                ', '.join(set(cfg.service_identifiers) - set(filtered_labels))
            )
        )
        return ()

    return tuple(f"{k}={v}" for k, v in filtered_labels.items())


def image_definition_labels_of_container(container_id: str) -> Dict[str, str]:
    labels = cfg.client.containers.get(container_id).image.labels
    return {k: v for k, v in labels.items() if k.startswith(cfg.label_ns)}


def parse_job_definitions(labels: Mapping[str, str], user: str) -> Dict[str, Dict]:
    log.debug(f'Considering labels for job definitions: {dict(labels)}')

    name_grouped_definitions: DefaultDict[
        str, Dict[str, Union[str, Dict]]
    ] = defaultdict(dict)

    for key, value in labels.items():
        key = key.removeprefix(cfg.label_ns)
        if '.env.' in key:
            name, _, variable = key.split('.', 2)
            name_grouped_definitions[name].setdefault('environment', {})
            name_grouped_definitions[name]['environment'][  # type: ignore
                variable
            ] = value
        else:
            name, attribute = key.split('.', 1)
            name_grouped_definitions[name][attribute] = value

    log.debug(f'Job definitions: {dict(name_grouped_definitions)}')

    result = {}
    for name, definition in name_grouped_definitions.items():
        log.debug(f'Processing {name}')
        definition['name'] = name
        definition.setdefault("user", user)

        job = job_config_validator.validated(definition)
        if job is None:
            log.error(f'Misconfigured job definition: {definition}')
            log.error(f'Errors: {job_config_validator.errors}')
            continue

        for trigger_name in ('cron', 'date', 'interval'):
            trigger = job.pop(trigger_name, None)
            if trigger is None:
                continue

            job['trigger'] = trigger

        log.debug(f'Normalized definition: {job}')
        result[name] = job

    return result


####


# TODO remove ignore when this issue is solved:
#      https://github.com/python/mypy/issues/1317
__all__ = (parse_labels.__name__,)  # type: ignore
