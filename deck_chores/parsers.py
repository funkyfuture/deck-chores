from functools import lru_cache
from collections import defaultdict
import logging
from typing import Tuple, Union

from apscheduler.triggers.cron import CronTrigger  # type: ignore
from apscheduler.triggers.date import DateTrigger  # type: ignore
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
import cerberus  # type: ignore
from pytz import all_timezones

from deck_chores.config import cfg
from deck_chores.exceptions import ParsingError
from deck_chores.utils import generate_id, lru_dict_arg_cache, split_string


####


Trigger = Union[CronTrigger, DateTrigger, IntervalTrigger]


####


NAME_INTERVAL_MAP = {
    'weekly':       (1, 0, 0, 0, 0),
    'daily':        (0, 1, 0, 0, 0),
    'hourly':       (0, 0, 1, 0, 0),
    'every minute': (0, 0, 0, 1, 0),
    'every second': (0, 0, 0, 0, 1)
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

    def _instantiate_trigger(self, value: str, cls: type, args) -> Union[Trigger, None]:
        try:
            return cls(*args, timezone=self.document.get('timezone', cfg.timezone))
        except Exception as e:
            message = "Error while instantiating a {trigger} with '{value}'.".format(
                trigger=cls.__name__, value=value)
            if cfg.debug:
                message += " Parsed arguments: %s" % args
                message += "\n%s" % e
            raise ParsingError(message)

    def _normalize_coerce_cron(self, value: str) -> CronTrigger:
        args = self._fill_args(value, len(CronTrigger.FIELD_NAMES), '*')
        return self._instantiate_trigger(value, CronTrigger, args)

    def _normalize_coerce_date(self, value: str) -> DateTrigger:
        return self._instantiate_trigger(value, DateTrigger, (value,))

    def _normalize_coerce_interval(self, value: str) -> IntervalTrigger:
        args = NAME_INTERVAL_MAP.get(value)
        if args is None:
            for c in '.:/':
                value = value.replace(c, ' ')
            args = self._fill_args(value, 5, '0')  # type: ignore
            args = tuple(int(x) for x in args)  # type: ignore
        return self._instantiate_trigger(value, IntervalTrigger, args)

    @staticmethod
    def _validate_type_cron_trigger(value):
        return isinstance(value, CronTrigger)

    @staticmethod
    def _validate_type_date_trigger(value):
        return isinstance(value, DateTrigger)

    @staticmethod
    def _validate_type_interval_trigger(value):
        return isinstance(value, IntervalTrigger)


job_def_validator = JobConfigValidator({
    'command': {'required': True},
    'cron': {'coerce': 'cron', 'type': 'cron_trigger',
             'required': True, 'excludes': ['date', 'interval']},
    'date': {'coerce': 'date', 'type': 'date_trigger',
             'required': True, 'excludes': ['cron', 'interval']},
    'interval': {'coerce': 'interval', 'type': 'interval_trigger',
                 'required': True, 'excludes': ['cron', 'date']},
    'max': {'coerce': int, 'default_setter': lambda x: cfg.default_max},
    'name': {'regex': r'[a-z0-9.-]+'},
    'timezone': {'allowed': all_timezones},
    'user': {'default_setter': lambda x: cfg.default_user}
})


####


def labels(*args, **kwargs) -> Tuple[str, str, dict]:
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


def _parse_labels(_labels: dict) -> Tuple[str, str, dict]:
    log.debug('Parsing labels: %s' % _labels)
    options = _parse_options(_labels)
    service_id = _parse_service_id(_labels)
    job_definitions = _parse_job_defintion(_labels)
    if service_id:
        log.debug('Assigning service id: %s' % service_id)
        for definition in job_definitions.values():
            # this is informative, not functional
            definition['service_id'] = service_id
    return service_id, options, job_definitions


def _parse_options(_labels: dict) -> str:
    options = _labels.pop(cfg.label_ns + 'options', None)
    result = set(cfg.default_options)
    if options is not None:
        for option in split_string(options):
            if option.startswith('no'):
                result.remove(option[2:])
            else:
                result.add(option)
    result_string = ','.join(sorted(x for x in result if x))
    log.debug('Parsed options: %s' % result_string)
    return result_string


def _parse_service_id(_labels: dict) -> str:
    filtered_labels = {k: v for k, v in _labels.items() if k in cfg.service_identifiers}
    log.debug('Considering labels for service id: %s' % filtered_labels)
    if not filtered_labels:
        return ''
    if len(filtered_labels) != len(cfg.service_identifiers):
        log.critical('Missing service identity labels: {}'
                     .format(', '.join(set(cfg.service_identifiers) - set(filtered_labels))))
        return ''
    identifiers = tuple(filtered_labels[x] for x in cfg.service_identifiers)
    return generate_id(*identifiers)


def _parse_job_defintion(_labels: dict) -> dict:
    filtered_labels = {k: v for k, v in _labels.items()
                       if k.startswith(cfg.label_ns)}
    log.debug('Considering labels for job definitions: %s' % filtered_labels)

    name_grouped_definitions = defaultdict(dict)  # type: ignore
    for key, value in filtered_labels.items():
        name, attribute = key[len(cfg.label_ns):].rsplit('.', 1)
        name_grouped_definitions[name][attribute] = value

    log.debug('Definitions: %s' % name_grouped_definitions)

    result = {}
    for name, definition in name_grouped_definitions.items():
        log.debug('Processing %s' % name)
        definition['name'] = name
        if not job_def_validator(definition):
            log.error('Misconfigured job definition: %s' % definition)
            log.error('Errors: %s' % job_def_validator.errors)
        else:
            job = job_def_validator.document
            trigger = None
            for trigger_name in ('cron', 'date', 'interval'):
                trigger = trigger or job.pop(trigger_name, None)
            job['trigger'] = trigger
            log.debug('Normalized definition: %s' % job)
            result[name] = job

    return result


####


__all__ = [labels.__name__]
