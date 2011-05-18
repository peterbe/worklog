import datetime
from pymongo import ASCENDING, DESCENDING
from pprint import pprint
from utils.decorators import login_required
from apps.main.handlers import BaseHandler
from utils.routes import route, route_redirect
import constants

route_redirect('/log$', '/log/')
@route('/log/$')
class EventLogHandler(BaseHandler):
    DEFAULT_BATCH_SIZE = 100

    @login_required
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        superuser = user.email == 'peterbe@gmail.com'

        search = {'user.$id': user._id}
        if superuser:
            search = {}

        event_logs = self.db.EventLog.find(search)
        options['count_event_logs'] = event_logs.count()
        options['superuser'] = superuser

        page = int(self.get_argument('page', 1))
        batch_size = self.DEFAULT_BATCH_SIZE
        skip = (page - 1) * batch_size
        options['page'] = page
        options['skip'] = skip
        options['pages'] = range(1, 1 + options['count_event_logs'] / batch_size)
        options['event_logs'] = list(event_logs.sort('add_date', DESCENDING).skip(skip).limit(batch_size))

        self.render("eventlog/index.html", **options)

@route('/log/stats\.json$')
class StatsEventLogHandler(BaseHandler):

    def get(self):
        data = dict(actions=self.get_action_stats(),
                    contexts=self.get_context_stats())
        self.write_json(data)

    def get_action_stats(self):
        actions = list()
        action_keys = constants.ACTIONS_HUMAN_READABLE.keys()
        action_keys.remove(0) # skip the "READ" action since it's not in use
        for key in sorted(action_keys):
            #pprint(self.db.EventLog.find({'action': key}).explain())
            actions.append((constants.ACTIONS_HUMAN_READABLE[key],
                            self.db.EventLog.find({'action': key}).count()))
        return actions

    def get_context_stats(self):
        contexts = list()
        context_keys = [getattr(constants, x) for x in dir(constants) if x.startswith('CONTEXT_')]
        #context_keys.remove(0) # skip the "READ" context since it's not in use
        for key in sorted(context_keys):
            label = key
            contexts.append((label,
                            self.db.EventLog.find({'context': key}).count()))
        return contexts


@route('/log/activity/$')
class EventLogActivityHandler(BaseHandler):

    #@login_required ## doesn't work with positional arguments
    def get(self):
        options = self.get_base_options()
        if not options['user']:
            self.redirect('/log/')
            return
        self.render('eventlog/activity.html', **options)

@route('/log/activity.json$')
class EventLogActivityJSONHandler(BaseHandler):

    #@login_required ## doesn't work with positional arguments
    def get(self):
        first_event = list(self.db.EventLog.find().sort('add_date').limit(1))[0]
        first_event_date = first_event.add_date
        last_event = list(self.db.EventLog.find().sort('add_date', -1).limit(1))[0]
        last_event_date = last_event.add_date

        while first_event_date.strftime('%A') != 'Monday':
            first_event_date -= datetime.timedelta(days=1)
        while last_event_date.strftime('%A') != 'Monday':
            last_event_date -= datetime.timedelta(days=1)

        #print first_event_date, last_event_date
        users = []
        events = []
        date = first_event_date
        while date < last_event_date:
            #print "\t", date
            next = date + datetime.timedelta(days=7)
            search = {'add_date': {'$gte': date, '$lt': next}}
            user_ids = set()
            event_ids = set()
            for each in self.db.EventLog.collection.find(search):
                if isinstance(each['user'], dict):
                    user_ids.add(each['user']['_id'])
                else:
                    user_ids.add(each['user'].id)
                if isinstance(each['event'], dict):
                    event_ids.add(each['event']['_id'])
                else:
                    event_ids.add(each['event'].id)
            users.append([date.strftime('%Y-%m-%d'), len(user_ids)])
            events.append([date.strftime('%Y-%m-%d'), len(event_ids)])
            date = next

        self.write_json(dict(users=users, events=events))
