from pprint import pprint
import datetime
from dateutil import relativedelta
import tornado.web
from utils.routes import route
from apps.main.handlers import BaseHandler, AuthLoginHandler, CredentialsError
from apps.main.models import Event

@route('/(iphone|android)/$')
class SmartphoneHandler(BaseHandler):
    def get(self, device_name):
        options = self.get_base_options()

        template = 'smartphone/index.html'
        #if options.get('user'):
        #    options['available_tags'] = self.get_all_available_tags(options['user'])
        #    template = 'smartphone/logged_in.html'

        self.render(template, **options)


@route('/(iphone|android)/auth/login/$')
class SmartphoneAuthLoginHandler(AuthLoginHandler):
    def post(self, device_name):
        # if this works it will set a cookie. Is that needed???
        # if not, consider rewriting AuthLoginHandler so that it can
        # check but not set a cookie or something
        try:
            user = self.check_credentials(self.get_argument('email'),
                                          self.get_argument('password'))
        except CredentialsError, msg:
            return self.write_json(dict(error="Error: %s" % msg))

        print "SIGNED", repr(self.create_signed_value('guid', user.guid))
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


@route('/(iphone|android)/checkguid/$')
class CheckGUIDHandler(BaseHandler, SmartphoneAPIMixin):

    def get(self, __):
        user = self.get_user()
        self.write_json(dict(ok=bool(user)))


@route('/smartphone/api/months.json$')
class APIMonthsHandler(BaseHandler, SmartphoneAPIMixin):

    def get(self):
        user = self.must_get_user()
        _search = {'user.$id':user._id}
        for event in self.db[Event.__collection__].find(_search).sort('start', 1).limit(1):
            first_date = event['start']
            break
        else:
            # No events
            first_date = datetime.date.today()
            first_date = datetime.datetime(
              first_date.year, first_date.month, 1, 0, 0, 0)

        for event in self.db[Event.__collection__].find(_search).sort('start', -1).limit(1):
            last_date = event['start']
            break
        else:
            last_date = datetime.date.today()
            last_date = datetime.datetime(
              last_date.year, last_date.month, 1, 0, 0, 0)

        today = datetime.date.today()

        months = []
        date = first_date
        while date <= last_date:
            first_of_date = datetime.datetime(
              date.year, date.month, 1, 0, 0, 0)

            next_date = first_of_date + relativedelta.relativedelta(months=1)
            #print first_of_date
            #print next_date
            #print

            # becomes 28 for February for example
            # Haven't tested for all years :)
            #no_days = (next_date - first_of_date).days

            #print first_of_date.strftime('%B'), no_days

            count_events = self.db[Event.__collection__]\
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

        print first_date
        print last_date

        pprint(months)
        self.write_json(dict(months=months))

@route('/smartphone/api/month\.json$')
class APIMonthHandler(BaseHandler, SmartphoneAPIMixin):

    def get(self):
        user = self.must_get_user()
        year = int(self.get_argument('year'))
        month = int(self.get_argument('month'))
        _search = {'user.$id':user._id}
        first_day = datetime.datetime(year, month, 1, 0, 0, 0)
        date = first_day
        #no_days = 0
        day_counts = []
        while date.month == first_day.month:
            #print date,
            count_events = self.db[Event.__collection__]\
              .find(dict(_search,
                         start={'$gte': date, '$lt':date + datetime.timedelta(days=1)}))\
                         .count()
            #print count_events
            #no_days += 1
            day_counts.append(count_events)
            date += datetime.timedelta(days=1)

        #print "No_days", no_days
        self.write_json(dict(month_name=first_day.strftime('%B'),
                             day_counts=day_counts))


@route('/smartphone/api/day\.json$')
class APIDayHandler(BaseHandler, SmartphoneAPIMixin):

    def get(self):
        user = self.must_get_user()
        year = int(self.get_argument('year'))
        month = int(self.get_argument('month'))
        day = int(self.get_argument('day'))
        _search = {'user.$id':user._id}
        date = datetime.datetime(year, month, day, 0, 0, 0)

        events = []
        for each in self.db[Event.__collection__]\
              .find(dict(_search,
                         start={'$gte': date, '$lt':date + datetime.timedelta(days=1)})):
            #print each
            event = dict(id=str(each['_id']),
                         all_day=each['all_day'],
                         title=each['title'],
                         tags=each['tags'])
            if each.get('description'):
                event['description'] = each['description']
            if each.get('external_url'):
                event['external_url'] = each['external_url']
            event['length'] = self._describe_length(each)
            events.append(event)

        #pprint(events)
        self.write_json(dict(events=events))

    def _describe_length(self, item):
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
