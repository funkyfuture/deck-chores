from collections import defaultdict
import logging
from typing import Tuple, Union

from apscheduler.triggers.cron import CronTrigger  # type: ignore
from apscheduler.triggers.date import DateTrigger  # type: ignore
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
import cerberus  # type: ignore
from pytz import all_timezones

from deck_chores.config import cfg


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
                trigger=cls.__name__, value=value
            )
            if cfg.debug:
                log.debug(message)
                log.debug("parsed arguments: %s" % args)
                log.exception(e)  # type: ignore

            raise Exception(message)

    def _normalize_coerce_cron(self, value: str) -> CronTrigger:
        args = self._fill_args(value, len(CronTrigger.FIELD_NAMES), '*')
        return self._instantiate_trigger(value, CronTrigger, args)

    def _normalize_coerce_date(self, value: str) -> DateTrigger:
        return self._instantiate_trigger(value, DateTrigger, (value,))

    def _normalize_coerce_interval(self, value: str) -> IntervalTrigger:
        args = NAME_INTERVAL_MAP.get(value)
        if args is None:
            for c in ('.:/'):
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


def labels(_labels: dict) -> dict:
    log.debug('Parsing labels: %s' % _labels)
    filtered_labels = {k: v for k, v in _labels.items()
                       if k.startswith(cfg.label_ns)}
    log.debug('Considering labels: %s' % filtered_labels)

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
            log.debug('Normalized defintion: %s' % job)
            result[name] = job

    return result


####


__all__ = [labels.__name__]
