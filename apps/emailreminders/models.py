import datetime
from pymongo.objectid import ObjectId
from mongokit import ValidationError
from apps.main.models import BaseDocument, register


@register
class EmailReminder(BaseDocument):
    __collection__ = 'email_reminders'
    structure = {
      'user': ObjectId,
      'weekdays': [unicode],
      'time': (int, int),
      'tz_offset': float,
      'disabled': bool,
      'include_instructions': bool,
      'include_summary': bool,
      '_next_send_date': datetime.datetime,
    }

    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = \
      (u'Monday', u'Tuesday', u'Wednesday', u'Thursday', u'Friday',
       u'Saturday', u'Sunday')

    WEEKDAYS = MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY

    required_fields = [
      'user', 'weekdays', 'time', 'tz_offset',
    ]

    default_values = {
      'disabled': False,
      'include_summary': False,
      'include_instructions': True,
      'tz_offset': 0.0,
      'weekdays': [MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY],
    }

    validators = {
      'tz_offset': lambda x: x > -12 and x < 12, #?????
      'time': lambda x: 0 <= x[0] <= 23 and 0 <= x[1] <= 59,
    }

    @property
    def user(self):
        return self.db.User.find_one({'_id': self['user']})

    def validate(self, *args, **kwargs):
        if isinstance(self['tz_offset'], int):
            self['tz_offset'] = float(self['tz_offset'])
        not_weekdays = set(self['weekdays']) - \
                                 set((self.MONDAY,
                                     self.TUESDAY,
                                     self.WEDNESDAY,
                                     self.THURSDAY,
                                     self.FRIDAY,
                                     self.SATURDAY,
                                     self.SUNDAY))
        if not_weekdays:
            raise ValidationError("Unrecognized weekdays %r" % not_weekdays)

        super(EmailReminder, self).validate(*args, **kwargs)

    def set_next_send_date(self, utcnow=None):
        if utcnow is None:
            utcnow = datetime.datetime.utcnow()
        _next_send_date = utcnow

        # first create the time with any random date
        start = datetime.datetime(2000,01,01, self.time[0], self.time[1], 0)
        result = start - datetime.timedelta(hours=self.tz_offset)

        h = result.hour
        m = result.minute
        if result > start:
            day_diff = (result - start).days
        else:
            day_diff = (start - result).days

        _next_send_date = datetime.datetime(_next_send_date.year,
                                            _next_send_date.month,
                                            _next_send_date.day,
                                            h, m)
        if day_diff:
            _next_send_date += datetime.timedelta(days=day_diff)

        assert self.weekdays
        # iterate until we hit the next weekday that is in this list
        while _next_send_date.strftime('%A') not in self.weekdays or _next_send_date <= utcnow:
            _next_send_date += datetime.timedelta(days=1)

        if day_diff:
            _next_send_date += datetime.timedelta(days=day_diff)

        assert _next_send_date > utcnow, _next_send_date
        self._next_send_date = _next_send_date


@register
class EmailReminderLog(BaseDocument):
    __collection__ = 'email_reminders_log'
    structure = {
      'email_reminder': EmailReminder,
      'replies': int,
    }
    # remember, every BaseDocument has add_date and modify_date

    default_values = {
      'replies': 0,
    }
