from pprint import pprint
import datetime
from time import mktime
from dateutil import relativedelta
from pymongo.objectid import InvalidId, ObjectId
import tornado.web
from utils.routes import route, route_redirect
from apps.main.handlers import BaseHandler, AuthLoginHandler, \
  CredentialsError, EventsHandler, EventHandler
from apps.main.models import Event
from apps.eventlog import log_event, actions, contexts
from utils import niceboolean, title_to_tags

class XSRFIgnore(object):
    def check_xsrf_cookie(self):
        print "Ignoring XSRF"
        return

route_redirect('/smartphone$', '/smartphone/')
@route('/smartphone/$')
class SmartphoneHandler(BaseHandler):
    def get(self):
        options = self.get_base_options()
        template = 'smartphone/index.html'
        self.render(template, **options)


@route('/smartphone/auth/login/$')
class SmartphoneAuthLoginHandler(XSRFIgnore, AuthLoginHandler):
    def post(self):
        # if this works it will set a cookie. Is that needed???
        # if not, consider rewriting AuthLoginHandler so that it can
        # check but not set a cookie or something
        try:
            user = self.check_credentials(self.get_argument('email'),
                                          self.get_argument('password'))
        except CredentialsError, msg:
            return self.write_json(dict(error="Error: %s" % msg))
        self.write_json(dict(guid=self.create_signed_value('guid', user.guid)))


class SmartphoneAPIMixin(object):

    def get_user(self):
        guid = self.get_argument('guid')
        if guid.count('|') == 2:
            guid = self.get_secure_cookie('guid', value=guid)
        if guid:
            return self.db.User.one({'guid': guid})

    def must_get_user(self):
        """hack to wrap get_user() and raise a 401 or 403"""
        user = self.get_user()
        if not user:
            raise tornado.web.HTTPError(403, "guid not valid")
        return user

class APIBaseHandler(XSRFIgnore, BaseHandler):

    def describe_length(self, item):
        if item['all_day']:
            days = (item['end'] - item['start']).days
            if days > 1:
                return "%s days" % days
            return "All day"
        else:
            seconds = (item['end'] - item['start']).seconds
            minutes = seconds / 60
            hours = minutes / 60
            if hours:
                minutes = minutes % 60
                if hours == 1:
                    if minutes:
                        return "1 hour %s minutes" % minutes
                    else:
                        return "1 hour"
                else:
                    if minutes:
                        return "%s hours %s minutes" % (hours, minutes)
                    else:
                        return "%s hours" % hours
            else:
                return "%s minutes" % minutes

@route('/smartphone/checkguid/$')
class CheckGUIDHandler(APIBaseHandler, SmartphoneAPIMixin):

    def get(self):
        user = self.get_user()
        self.write_json(dict(ok=bool(user)))


@route('/smartphone/api/months.json$')
class APIMonthsHandler(APIBaseHandler, SmartphoneAPIMixin):

    def get(self):
        user = self.must_get_user()
        timestamp_only = niceboolean(self.get_argument('timestamp_only', False))
        _search = {'user.$id':user._id}
        for event in self.db.Event.collection\
          .find(_search).sort('start', 1).limit(1):
            first_date = event['start']
            break
        else:
            # No events
            first_date = datetime.date.today()
            first_date = datetime.datetime(
              first_date.year, first_date.month, 1, 0, 0, 0)

        #for event in self.db[Event.__collection__].find(_search).sort('start', -1).limit(1):
        #    last_date = event['start']
        #    break
        #else:
        last_date = datetime.date.today()
        last_date = datetime.datetime(
              last_date.year, last_date.month, 1, 0, 0, 0)

        today = datetime.date.today()

        months = []
        date = first_date
        timestamp = 0
        while date <= last_date:
            first_of_date = datetime.datetime(
              date.year, date.month, 1, 0, 0, 0)

            next_date = first_of_date + relativedelta.relativedelta(months=1)

            for event in self.db.Event.collection\
              .find(dict(_search,
                         start={'$gte': first_of_date, '$lt':next_date}))\
              .limit(1).sort('add_date', -1):
                tmp_timestamp = mktime(event['add_date'].timetuple())
                if tmp_timestamp > timestamp:
                    timestamp = tmp_timestamp
                    break

            if not timestamp_only:
                # becomes 28 for February for example
                # Haven't tested for all years :)
                count_events = self.db.Event.collection\
                  .find(dict(_search,
                             start={'$gte': first_of_date, '$lt':next_date}))\
                             .count()
                month_name = first_of_date.strftime('%B')
                #if first_of_date.year == today.year and first_of_date.month == today.month:
                #    month_name += " (today)"
                months.append(dict(month_name=month_name,
                                   year=first_of_date.year,
                                   month=first_of_date.month,
                                   count=count_events,
                                   #no_days=no_days,
                                   ))
            date = next_date

        if timestamp_only:
            self.write_json(dict(timestamp=timestamp))
        else:
            self.write_json(dict(months=months, timestamp=timestamp))

@route('/smartphone/api/month\.json$')
class APIMonthHandler(APIBaseHandler, SmartphoneAPIMixin):

    def get(self):
        user = self.must_get_user()
        year = int(self.get_argument('year'))
        month = int(self.get_argument('month'))
        timestamp_only = niceboolean(self.get_argument('timestamp_only', False))
        _search = {'user.$id':user._id}
        first_day = datetime.datetime(year, month, 1, 0, 0, 0)
        date = first_day
        #no_days = 0
        day_counts = []
        if timestamp_only:
            while date.month == first_day.month:
                date += datetime.timedelta(days=1)
        else:
            while date.month == first_day.month:
                count_events = self.db[Event.__collection__]\
                  .find(dict(_search,
                             start={'$gte': date, '$lt':date + datetime.timedelta(days=1)}))\
                             .count()
                day_counts.append(count_events)
                date += datetime.timedelta(days=1)

        timestamp = 0
        for event in self.db.Event.collection\
          .find(dict(_search,
                     start={'$gte': first_day, '$lt':date}
                     )).limit(1).sort('add_date', -1):
            timestamp = mktime(event['add_date'].timetuple())
            break

        if timestamp_only:
            self.write_json(dict(timestamp=timestamp))
        else:
            self.write_json(dict(month_name=first_day.strftime('%B'),
                                 day_counts=day_counts,
                                 first_day=first_day.strftime('%A'),
                                 timestamp=timestamp))


@route('/smartphone/api/day\.json$')
class APIDayHandler(APIBaseHandler, EventsHandler, SmartphoneAPIMixin):

    def get(self):
        user = self.must_get_user()
        year = int(self.get_argument('year'))
        month = int(self.get_argument('month'))
        day = int(self.get_argument('day'))
        timestamp_only = niceboolean(self.get_argument('timestamp_only', False))
        _search = {'user.$id':user._id}
        date = datetime.datetime(year, month, day, 0, 0, 0)

        timestamp = 0
        for event in self.db.Event.collection\
                  .find(dict(_search,
                             start={'$gte': date, '$lt':date + datetime.timedelta(days=1)}))\
                  .limit(1).sort('modify_date', -1):
            timestamp = mktime(event['modify_date'].timetuple())
            break

        if not timestamp_only:
            events = []
            days_spent = hours_spent = None
            for each in self.db.Event.collection\
                  .find(dict(_search,
                             start={'$gte': date, '$lt':date + datetime.timedelta(days=1)})):
                if days_spent is None:
                    days_spent = hours_spent = 0.0

                event = dict(id=str(each['_id']),
                             all_day=each['all_day'],
                             title=each['title'],
                             #tags=each['tags'],
                             )
                event['description'] = each['description']
                event['external_url'] = each['external_url']
                if each['all_day']:
                    event['days'] = 1 + (each['end'] - each['start']).days
                else:
                    event['hours'] = (each['end'] - each['start']).seconds / 60.0 / 60
                event['length'] = self.describe_length(each)
                events.append(event)
                #if each['all_day']:
                #    days_spent += 1 + (each['end'] - each['start']).days
                #else:
                #    hours_spent += (each['end'] - each['start']).seconds / 60.0 / 60

        data = dict(timestamp=timestamp)
        if not timestamp_only:
            data['events'] = events
            #if days_spent or hours_spent:
            #    data['totals'] = dict()
            #    # there were some events at least
            #    if days_spent:
            #        data['totals']['days_spent'] = days_spent
            #    if hours_spent:
            #        data['totals']['hours_spent'] = '%.2f' % round(hours_spent, 1)
        self.write_json(data)


    def post(self):
        user = self.must_get_user()
        title = self.get_argument('title').strip()
        duration = self.get_argument('duration')
        duration_other = self.get_argument('duration_other', '')

        year = int(self.get_argument('year'))
        month = int(self.get_argument('month'))
        day = int(self.get_argument('day'))

        if duration == 'all_day':
            all_day = True
            start = datetime.datetime(year, month, day, 0, 0, 0)
            end = start
        else:
            all_day = False
            now = datetime.datetime.now()
            start = datetime.datetime(year, month, day, now.hour, now.minute, now.second)
            try:
                if duration == 'other':
                    duration = float(duration_other)
                else:
                    duration = float(duration)
            except ValueError:
                return self.write_json(dict(error="Error! Not a valid other number"))
            if (duration <= 0):
                return self.write_json(dict(error="Error! Duration must be more than zero"))
            end = start + datetime.timedelta(minutes=float(duration) * 60)
        event, created = self.create_event(user, all_day=all_day, start=start, end=end)

        if created:
            log_event(self.db, user, event, actions.ACTION_ADD, contexts.CONTEXT_SMARTPHONE)

        event_json = dict(title=event['title'],
                          id=str(event['_id']),
                          length=self.describe_length(event))
        self.write_json(dict(event=event_json))


@route('/smartphone/api/event\.json$')
class APIEventHandler(APIBaseHandler, EventsHandler, SmartphoneAPIMixin):

    def get(self):
        user = self.must_get_user()
        event_id = self.get_argument('id')
        timestamp_only = niceboolean(self.get_argument('timestamp_only', False))
        _search = {'user.$id':user._id,
                   '_id': ObjectId(event_id)}

        event = self.db.Event.one(_search)
        if not event:
            self.write_json(dict(error="ERROR: Invalid Event"))
            return

        timestamp = mktime(event['modify_date'].timetuple())
        data = dict(timestamp=timestamp)
        if not timestamp_only:
            event_data = dict(title=event['title'],
                              id=str(event['_id']),
                              all_day=event['all_day'],
                              description=event['description']
                              )
            if event['all_day']:
                event_data['days'] = 1 + (event['end'] - event['start']).days
            else:
                event_data['hours'] = (event['end'] - event['start']).seconds / 60.0 / 60
            data['event'] = self.serialize_dict(event_data)
        self.write_json(data)


    def post(self):
        user = self.must_get_user()
        event_id = self.get_argument('id')
        _search = {'user.$id':user._id,
                   '_id': ObjectId(event_id)}

        event = self.db.Event.one(_search)
        if not event:
            self.write_json(dict(error="ERROR: Invalid Event"))
            return
        if event.user != user:
            self.write_json(dict(error="ERROR: Not your event"))
            return

        title = self.get_argument('title').strip()
        duration = float(self.get_argument('duration'))
        external_url = self.get_argument('external_url', u'').strip()
        description = self.get_argument('description', u'').strip()

        if event.all_day:
            _before = 1 + (event.end - event.start).days
            if _before != duration:
                event.end += datetime.timedelta(days=duration - _before)
                diff = 1 + (event.end - event.start).days
                if diff < 1:
                    self.write_json(dict(error=\
                      "ERROR. Duration can't be less than 1 day"))
                    return
        else:
            _before = (event['end'] - event['start']).seconds / 60.0 / 60
            if _before != duration:
                event.end += datetime.timedelta(hours=duration - _before)
                if event.start >= event.end:
                    self.write_json(dict(error="ERROR. Duration too short"))
                    return

        # all possible validation and checking done, do the save
        event.title = title
        event.external_url = external_url
        event.description = description
        event.tags = title_to_tags(title)
        event.save()

        log_event(self.db, user, event, actions.ACTION_EDIT,
                  contexts.CONTEXT_SMARTPHONE)

        data = dict(timestamp=mktime(event.modify_date.timetuple()))
        event_data = dict(title=title,
                          external_url=external_url,
                          description=description,
                          id=str(event._id),
                          all_day=event.all_day,
                          )
        if event.all_day:
            event_data['days'] = 1 + (event.end - event.start).days
        else:
            event_data['hours'] = (event.end - event.start).seconds / 60.0 / 60
        event_data['length'] = self.describe_length(event)
        data['event'] = self.serialize_dict(event_data)
        self.write_json(data)
