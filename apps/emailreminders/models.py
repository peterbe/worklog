from mongokit import ValidationError
from apps.main.models import BaseDocument, User

class EmailReminder(BaseDocument):
    __collection__ = 'email_reminders'
    structure = {
      'user': User, 
      'weekdays': [unicode],
      'time': (int, int),
      'tz_offset': int,
    }
    
    MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = \
      (u'Monday', u'Tuesday', u'Wednesday', u'Thursday', u'Friday', 
       u'Saturday', u'Sunday')
      
    
    required_fields = [
      'user', 'weekdays', 'time', 'tz_offset',
    ]
    
    default_values = {
      'tz_offset': 0,
      'weekdays': [MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY],
    }
    
    validators = {
      'tz_offset': lambda x: x > -12 and x < 12, #?????
      'time': lambda x: 0 <= x[0] <= 23 and 0 <= x[1] <= 59,
    }
    
    def validate(self, *args, **kwargs):
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
        

        