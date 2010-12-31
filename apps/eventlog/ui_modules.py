import tornado.web
from apps.main.models import User, Event
from models import EventLog    
class VerboseEventLog(tornado.web.UIModule):
    def render(self, entry, what):
        if what == 'action':
            return {EventLog.ACTION_READ: "Read",
                    EventLog.ACTION_ADD: "Add",
                    EventLog.ACTION_EDIT: "Edit",
                    EventLog.ACTION_DELETE: "Delete",
                    EventLog.ACTION_RESTORE: "Restore",
                   }.get(entry.action, "*unknown*")
        elif what == 'date':
            return entry.add_date.strftime('%Y-%m-%d %H:%M:%S')
        elif what == 'comment':
            return entry.comment and entry.comment or u''
        elif what == 'event':
            event = self._get_event(entry.event)
            if event:
                return event['title']
            else:
                return '*deleted*'
        elif what == 'user':
            user = self._get_user(entry.user)
            if user:
                return user['email']
            else:
                return '*deleted*'
        else:
            raise NotImplementedError(what)
        
    def _get_user(self, ref):
        return self.handler.db[User.__collection__].one({'_id': ref.id})

    def _get_event(self, ref):
        return self.handler.db[Event.__collection__].one({'_id': ref.id})
    
        