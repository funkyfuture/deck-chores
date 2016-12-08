from functools import lru_cache
from collections import defaultdict
import logging
from typing import Tuple, Union

from apscheduler.triggers.cron import CronTrigger  # type: ignore
from apscheduler.triggers.date import DateTrigger  # type: ignore
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
import cerberus  # type: ignore
from pytz import all_timezones

from deck_chores.caches import get_filtered_image_labels_for_container
from deck_chores.config import cfg
from deck_chores.exceptions import ParsingError
from deck_chores.utils import generate_id, split_string


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

    def _normalize_coerce_cron(self, value: str) -> Tuple[object, tuple]:
        args = self._fill_args(value, len(CronTrigger.FIELD_NAMES), '*')
        return CronTrigger, args

    def _normalize_coerce_date(self, value: str) -> Tuple[object, tuple]:
        return DateTrigger, (value,)

    def _normalize_coerce_interval(self, value: str) -> Tuple[object, tuple]:
        args = NAME_INTERVAL_MAP.get(value)
        if args is None:
            for c in '.:/':
                value = value.replace(c, ' ')
            args = self._fill_args(value, 5, '0')  # type: ignore
            args = tuple(int(x) for x in args)  # type: ignore
        return IntervalTrigger, args

    # TODO remove with the next release of cerberus
    def _validate_validator_trigger(self, field, value):
        pass

    def _validator_trigger(self, field, value):
        if isinstance(value, str):  # normalization failed
            return
        cls, args = value[0], value[1]
        try:
            cls(*args, timezone=self.document.get('timezone', cfg.timezone))
        except Exception as e:
            message = "Error while instantiating a {trigger} with '{args}'.".format(
                trigger=cls.__name__, args=args)
            if cfg.debug:
                message += "\n%s" % e
            self._error(field, message)


job_def_validator = JobConfigValidator({
    'command': {'required': True},
    'cron': {'coerce': 'cron', 'validator': 'trigger',
             'required': True, 'excludes': ['date', 'interval']},
    'date': {'coerce': 'date', 'validator': 'trigger',
             'required': True, 'excludes': ['cron', 'interval']},
    'interval': {'coerce': 'interval', 'validator': 'trigger',
                 'required': True, 'excludes': ['cron', 'date']},
    'max': {'coerce': int, 'default_setter': lambda x: cfg.default_max},
    'name': {'regex': r'[a-z0-9.-]+'},
    'timezone': {'default_setter': lambda x: cfg.timezone, 'allowed': all_timezones,
                 'required': True},
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
                log.exception(line)  # type: ignore
        return '', '', {}
    except Exception as e:
        raise e


@lru_cache()
def _parse_labels(container_id: str) -> Tuple[str, str, dict]:
    _labels = cfg.client.inspect_container(container_id)['Config'].get('Labels', {})
    log.debug('Parsing labels: %s' % _labels)
    filtered_labels = {k: v for k, v in _labels.items()
                       if k.startswith(cfg.label_ns)}
    options = _parse_options(_labels.get(cfg.label_ns + 'options', None))
    service_id = _parse_service_id(_labels)
    if 'image' in options:
        _labels = get_filtered_image_labels_for_container(container_id).copy()
        _labels.update(filtered_labels)
    else:
        _labels = filtered_labels

    job_definitions = _parse_job_defintion(_labels)

    if service_id:
        log.debug('Assigning service id: %s' % service_id)
        for definition in job_definitions.values():
            # this is informative, not functional
            definition['service_id'] = service_id
    return service_id, options, job_definitions


@lru_cache(4)
def _parse_options(options: str) -> str:
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
    log.debug('Considering labels for job definitions: %s' % _labels)
    name_grouped_definitions = defaultdict(dict)  # type: ignore
    for key, value in _labels.items():
        if key == cfg.label_ns + 'options':
            continue
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
            for trigger_name in ('cron', 'date', 'interval'):
                trigger = job.pop(trigger_name, None)
                if trigger is None:
                    continue
                job['trigger'] = trigger
            log.debug('Normalized definition: %s' % job)
            result[name] = job

    return result


####


__all__ = [labels.__name__]
