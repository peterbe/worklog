import logging
def log_event(db, user, event, action, context, comment=None):
    try:
        event_log = db.EventLog()
        event_log.user = user
        event_log.event = event
        event_log.action = action
        event_log.context = context
        if comment is not None:
            event_log.comment = unicode(comment)
        event_log.save()
    except:
        logging.error("Unable to log event", exc_info=True)

class Empty:
    pass
import constants
actions = Empty()
contexts = Empty()
for each in dir(constants):
    if each.startswith('ACTION_'):
        setattr(actions, each, getattr(constants, each))
    if each.startswith('CONTEXT_'):
        setattr(contexts, each, getattr(constants, each))
