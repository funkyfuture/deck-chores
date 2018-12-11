from functools import lru_cache
from collections import defaultdict, ChainMap
import logging
from typing import (  # noqa: F401
    DefaultDict,
    Dict,
    Mapping,
    Optional,
    Tuple,
    Type,
    Union,
)

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
import cerberus
from pytz import all_timezones

from deck_chores.config import cfg
from deck_chores.exceptions import ParsingError
from deck_chores.utils import (
    generate_id,
    parse_time_from_string_with_units,
    seconds_as_interval_tuple,
    split_string,
)


####


Trigger = Union[CronTrigger, DateTrigger, IntervalTrigger]


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


log = logging.getLogger('deck_chores')


####


class JobConfigValidator(cerberus.Validator):
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
                args = self._fill_args(value, 5, '0')  # type: ignore
                args = tuple(int(x) for x in args)  # type: ignore
        return IntervalTrigger, args

    def _normalize_coerce_timeunits(self, value: str) -> Optional[int]:
        if any(x.isalpha() for x in value):
            return parse_time_from_string_with_units(value)
        return int(value)

    def _validator_trigger(self, field, value):
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


job_def_validator = JobConfigValidator(
    {
        'command': {'required': True},
        'cron': {
            'coerce': 'cron',
            'validator': 'trigger',
            'required': True,
            'excludes': ['date', 'interval'],
        },
        'date': {
            'coerce': 'date',
            'validator': 'trigger',
            'required': True,
            'excludes': ['cron', 'interval'],
            'dependencies': {'jitter': None},
        },
        'environment': {'type': 'dict', 'default': {}},
        'interval': {
            'coerce': 'interval',
            'validator': 'trigger',
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
        'max': {'coerce': int, 'default_setter': lambda x: cfg.default_max},
        'name': {'regex': r'[a-z0-9.-]+'},
        'timezone': {
            'default_setter': lambda x: cfg.timezone,
            'allowed': all_timezones,
            'required': True,
        },
        'user': {'regex': r'[a-zA-Z0-9_.][a-zA-Z0-9_.-]*'},
        'workdir': {'regex': r'/.*'},
    }
)
# TODO rather update the schema when the config was parsed than using lambdas


####


def labels(*args, **kwargs) -> Tuple[str, str, Mapping[str, Dict]]:
    # don't call this from unittests
    try:
        return _parse_labels(*args, **kwargs)

    except ParsingError as e:
        if isinstance(e.args[0], str):
            lines = e.args[0].splitlines()
        elif isinstance(e.args[0], list):
            lines = e.args[0]
        else:
            raise RuntimeError

        for line in lines:
            if isinstance(line, str):
                log.error(line)
            elif isinstance(line, Exception):
                log.exception(line)
        return '', '', {}

    except Exception as e:
        raise e


@lru_cache()
def _parse_labels(container_id: str) -> Tuple[str, str, Mapping[str, Dict]]:
    _labels = cfg.client.containers.get(container_id).labels
    log.debug(f'Parsing labels: {_labels}')

    service_id = _parse_service_id(_labels)

    filtered_labels = {k: v for k, v in _labels.items() if k.startswith(cfg.label_ns)}
    flags, user = _parse_options(filtered_labels)

    # just for type information
    jobs_labels = {}  # type: Mapping[str, str]

    if 'image' in flags:
        image_labels = _image_definition_labels_of_container(container_id)
        _, image_options_user = _parse_options(image_labels)
        user = user or image_options_user
        jobs_labels = ChainMap(filtered_labels, image_labels)
    else:
        jobs_labels = filtered_labels

    job_definitions = _parse_job_definitions(jobs_labels)

    if user:
        for job_definition in job_definitions.values():
            job_definition.setdefault('user', user)

    if service_id:
        log.debug(f'Assigning service id: {service_id}')
        for job_definition in job_definitions.values():
            # this is informative, not functional
            job_definition['service_id'] = service_id
    return service_id, flags, job_definitions


def _parse_options(_labels: Dict[str, str]) -> Tuple[str, Optional[str]]:
    label_ns = cfg.label_ns

    # backward compatibility
    deprecated_flags_key = label_ns + 'options'
    flags_key = label_ns + 'options.flags'
    if deprecated_flags_key in _labels:
        log.warning(
            'The `options` name in a label is now itself a namespace. It contains its '
            'replacement `options.flags` with the same semantics.'
        )
        if flags_key in _labels:
            log.critical('Container flags are set redundantly.')
        _labels[flags_key] = _labels.pop(deprecated_flags_key)

    flags = _parse_flags(_labels.pop(flags_key, None))

    user_key = label_ns + 'options.user'
    user = _labels.pop(user_key, None)

    return flags, user


@lru_cache(4)
def _parse_flags(options: Optional[str]) -> str:
    result = set(cfg.default_flags)
    if options:
        for option in split_string(options):
            if option.startswith('no'):
                result.discard(option[2:])
            else:
                result.add(option)
    result_string = ','.join(sorted(result))
    log.debug(f'Parsed & resolved container flags: {result_string}')
    return result_string


def _parse_service_id(_labels: Dict[str, str]) -> str:
    filtered_labels = {k: v for k, v in _labels.items() if k in cfg.service_identifiers}
    log.debug(f'Considering labels for service id: {filtered_labels}')
    if not filtered_labels:
        return ''

    if len(filtered_labels) != len(cfg.service_identifiers):
        log.critical(
            'Missing service identity labels: {}'.format(
                ', '.join(set(cfg.service_identifiers) - set(filtered_labels))
            )
        )
        return ''

    identifiers = tuple(filtered_labels[x] for x in cfg.service_identifiers)
    return generate_id(*identifiers)


@lru_cache()
def _image_definition_labels_of_container(container_id: str) -> Dict[str, str]:
    labels = cfg.client.containers.get(container_id).image.labels
    return {k: v for k, v in labels.items() if k.startswith(cfg.label_ns)}


def _parse_job_definitions(_labels: Mapping[str, str]) -> Dict[str, Dict]:
    log.debug(f'Considering labels for job definitions: {_labels}')

    name_grouped_definitions = defaultdict(
        dict
    )  # type: DefaultDict[str, Dict[str, Union[str, Dict]]]

    for key, value in _labels.items():
        key = key[len(cfg.label_ns) :]  # noqa: E203
        if '.env.' in key:
            name, _, variable = key.split('.', 2)
            name_grouped_definitions[name].setdefault('environment', {})
            name_grouped_definitions[name]['environment'][  # type: ignore
                variable
            ] = value
        else:
            name, attribute = key.split('.', 1)
            name_grouped_definitions[name][attribute] = value

    log.debug(f'Job definitions: {name_grouped_definitions}')

    result = {}
    for name, definition in name_grouped_definitions.items():
        log.debug(f'Processing {name}')
        definition['name'] = name

        job = job_def_validator.validated(definition)
        if job is None:
            log.error(f'Misconfigured job definition: {definition}')
            log.error(f'Errors: {job_def_validator.errors}')
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


__all__ = [labels.__name__]
