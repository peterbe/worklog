import tornado.web

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
        else:
            raise NotImplementedError(what)