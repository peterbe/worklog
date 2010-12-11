import datetime
from mongokit import ValidationError
from apps.main.models import BaseDocument, User

class EmailReminder(BaseDocument):
    __collection__ = 'email_reminders'
    structure = {
      'user': User, 
      'weekdays': [unicode],
      'time': (int, int),
      'tz_offset': float,
      'disabled': bool,
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
      'tz_offset': 0.0,
      'weekdays': [MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY],
    }
    
    validators = {
      'tz_offset': lambda x: x > -12 and x < 12, #?????
      'time': lambda x: 0 <= x[0] <= 23 and 0 <= x[1] <= 59,
    }
    
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

        # because the tz_offset can be something 1.5, the hour can become a 
        # non-whole number. Eg. (h,m)==(7.5,30)
        # If that's the case turn it into a 
        tz_offset_minutes = self.tz_offset * 60
        tz_offset_h = int(tz_offset_minutes) / 60
        tz_offset_m = int(tz_offset_minutes) % 60
        h, m = self.time[0] - tz_offset_h, self.time[1] - tz_offset_m
        day_diff = 0
        if h < 0:
            h = 24 + h
            day_diff = -1
        elif h > 23:
            h -= 24
            day_diff += 1
        #print "TWO", h, m
            
        
        _next_send_date = datetime.datetime(_next_send_date.year,
                                            _next_send_date.month,
                                            _next_send_date.day,
                                            h, m)
        if day_diff:
            #print "DAY_DIFF", day_diff
            #print "before", _next_send_date
            _next_send_date += datetime.timedelta(days=day_diff)
            #print "after", _next_send_date
            
        assert self.weekdays
        # iterate until we hit the next weekday that is in this list
        #print "_next_send_date", _next_send_date
        #print _next_send_date.strftime('%A'), self.weekdays
        while _next_send_date.strftime('%A') not in self.weekdays or _next_send_date <= utcnow:
            _next_send_date += datetime.timedelta(days=1)
            
        if day_diff:
            #print "SECOND TIME"
            #print "DAY_DIFF", day_diff
            #print "before", _next_send_date
            _next_send_date += datetime.timedelta(days=day_diff)
            #print "after", _next_send_date
            
        assert _next_send_date > utcnow
        self._next_send_date = _next_send_date
        

class EmailReminderLog(BaseDocument):
    __collection__ = 'email_reminders_log'
    structure = {
      'email_reminder': EmailReminder,
    }
    # remember, every BaseDocument has add_date and modify_date