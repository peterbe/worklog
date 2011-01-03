import tornado.web
from apps.main.models import User, Event
from models import EventLog
import constants

class VerboseEventLog(tornado.web.UIModule):
    def render(self, entry, what):
        if what == 'action':
            return constants.ACTIONS_HUMAN_READABLE.get(entry.action, "*unknown*")
        elif what == 'date':
            return entry.add_date.strftime('%Y-%m-%d')# %H:%M:%S')
        elif what == 'comment':
            return entry.comment and entry.comment or u''
        elif what == 'event':
            if isinstance(entry.event, dict):
                event = entry.event
            else:
                event = self._get_event(entry.event)
            if event:
                return event['title']
            else:
                return '*deleted*'
        elif what == 'user':
            if isinstance(entry.user, dict):
                user = entry.user
            else:
                user = self._get_user(entry.user)
            if user:
                return self._brief_email(user['email'])
            else:
                return '*deleted*'
        else:
            raise NotImplementedError(what)
        
    def _brief_email(self, email):
        return email
        
    def _get_user(self, ref):
        return self.handler.db[User.__collection__].one({'_id': ref.id})

    def _get_event(self, ref):
        return self.handler.db[Event.__collection__].one({'_id': ref.id})
    
        