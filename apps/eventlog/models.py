import datetime
from apps.main.models import BaseDocument, Event, User

class EventLog(BaseDocument):
    __collection__ = 'event_log'
    structure = {
      'event': Event,
      'user': User,
      'action': int,
      'context': unicode,
      'comment': unicode,
    }
    
    ACTION_READ = 0
    ACTION_ADD = 1
    ACTION_EDIT = 2
    ACTION_DELETE = 3
    ACTION_RESTORE = 4
    
    CONTEXT_CALENDAR = u'calendar'
    CONTEXT_API = u'api'
    CONTEXT_BOOKMARKLET = u'bookmarklet'
    CONTEXT_EMAILREMINDER = u'emailreminder'