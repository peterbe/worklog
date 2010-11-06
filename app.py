#!/usr/bin/env python
#
import httplib
from pprint import pprint
from collections import defaultdict
from pymongo.objectid import InvalidId, ObjectId
from time import mktime, sleep, time
from types import ClassType
import cStringIO
import datetime
import os.path
import re
from mongokit import Connection
import tornado.auth
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata

from tornado.options import define, options

from models import Event, User, UserSettings, Share
from utils import parse_datetime, encrypt_password, niceboolean, \
  DatetimeParseError, valid_email
from utils.routes import route
from utils.git import get_git_revision
from utils.decorators import login_required
from utils.datatoxml import dict_to_xml

import ui_modules
################################################################################

define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=8000, help="run on the given port", type=int)
define("database_name", default="worklog", help="mongodb database name")
define("prefork", default=False, help="pre-fork across all CPUs", type=bool)
define("showurls", default=False, help="Show all routed URLs", type=bool)
define("dont_combine", default=False, help="Don't combine static resources", type=bool)

MAX_TITLE_LENGTH = 500

class Application(tornado.web.Application):
    def __init__(self, 
                 database_name=None, 
                 xsrf_cookies=True, 
                 optimize_static_content=None):
        ui_modules_map = {} 
        for name in [x for x in dir(ui_modules) if re.findall('[A-Z]\w+', x)]:
            thing = getattr(ui_modules, name)
            try:
                if issubclass(thing, tornado.web.UIModule):
                    ui_modules_map[name] = thing
            except TypeError:
                # most likely a builtin class or something
                pass
            
        if options.dont_combine:
            ui_modules_map['Static'] = ui_modules_map['PlainStatic']
            ui_modules_map['StaticURL'] = ui_modules_map['PlainStaticURL']
            
        # unless explicitly set, then if in debug mode, disable optimization
        # of static content
        if optimize_static_content is None:
            optimize_static_content = not options.debug
            
        handlers = route.get_routes()
        settings = dict(
            title=u"DoneCal",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules=ui_modules_map,
            xsrf_cookies=xsrf_cookies,
            cookie_secret="11oETzKsXQAGaYdkL5gmGeJJFuYh7EQnp2XdTP1o/Vo=",
            login_url="/auth/login",
            debug=options.debug,
            optimize_static_content=optimize_static_content,
            git_revision=get_git_revision(),
            CLOSURE_LOCATION=os.path.join(os.path.dirname(__file__), 
                                      "static", "compiler.jar"),
            YUI_LOCATION=os.path.join(os.path.dirname(__file__), 
                                      "static", "yuicompressor-2.4.2.jar"),
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        
        #print database_name and database_name or options.database_name
        # Have one global connection to the blog DB across all handlers
        self.database_name = database_name and database_name or options.database_name
        self.con = Connection()
        self.con.register([Event, User, UserSettings, Share])
        #self.db = Connection()
        

class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.con[self.application.database_name]

    def get_current_user(self):
        guid = self.get_secure_cookie("guid")
        if guid:
            return self.db.users.User.one({'guid': guid})
        
    def get_current_user_settings(self, user=None):
        if user is None:
            user = self.get_current_user()
            
        if not user:
            raise ValueError("Can't get settings when there is no user")
        return self.db.user_settings.UserSettings.one({'user.$id': user._id})
    
    def write_json(self, struct, javascript=False):
        if javascript:
            self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        else:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(tornado.escape.json_encode(struct))
        
    def write_xml(self, struct):
        self.set_header("Content-Type", "text/xml; charset=UTF-8")
        self.write(dict_to_xml(struct))
    
    def write_txt(self, str_):
        self.set_header("Content-Type", "text/plain; charset=UTF-8") # doesn;t seem to work
        self.write(str_)
        
        
    def transform_fullcalendar_event(self, item, serialize=False, **kwargs):
        data = dict(title=item['title'],
                    start=item['start'],
                    end=item['end'],
                    allDay=item['all_day'],
                    id=str(item['_id']))
            
        data.update(**kwargs)
        if 'external_url' in item:
            data['external_url'] = item['external_url']
            
        if serialize:
            for key, value in data.items():
                if isinstance(value, (datetime.datetime, datetime.date)):
                    #time_tuple = (2008, 11, 12, 13, 59, 27, 2, 317, 0)
                    timestamp = mktime(value.timetuple())
                    data[key] = timestamp
            
        return data
    
    def case_correct_tags(self, tags, user):
        # the new correct case for these tags is per the parameter 'tags'
        # We need to change all other tags that are spelled with a different
        # case to this style 
        base_search = {
          'user.$id': user._id,
        }
        for tag in tags:
            search = dict(base_search, 
                          tags=re.compile(re.escape(tag), re.I))
            
            for event in self.db.events.find(search):
                checked_tags = []
                for t in event['tags']:
                    if t != tag and t.lower() == tag.lower():
                        checked_tags.append(tag)
                    else:
                        checked_tags.append(t)
                if event['tags'] != checked_tags:
                    event['tags'] = checked_tags
                    # because 'event' is just a dict, we need to turn it into an object
                    # before we can save it
                    event_obj = self.db.events.Event(event)
                    event_obj.save()
        
        
    def find_user(self, email):
        return self.db.users.User.one(dict(email=\
         re.compile(re.escape(email), re.I)))
         
    def has_user(self, email):
        return bool(self.find_user(email))
    
    def get_base_options(self):
        options = {}
        # default settings
        settings = dict(hide_weekend=False,
                        monday_first=False,
                        disable_sound=False,
                        offline_mode=False)

        user = self.get_secure_cookie('user')
        user_name = None
        
        if user:
            user = self.db.users.User.one(dict(guid=user))
            if user.first_name:
                user_name = user.first_name
            elif user.email:
                user_name = user.email
            else:
                user_name = "Someonewithoutaname"
                
            # override possible settings
            user_settings = self.get_current_user_settings(user)
            if user_settings:
                settings['hide_weekend'] = user_settings.hide_weekend
                settings['monday_first'] = user_settings.monday_first
                settings['disable_sound'] = user_settings.disable_sound
                settings['offline_mode'] = getattr(user_settings, 'offline_mode', False)
                
        options['user'] = user
        options['user_name'] = user_name
        options['settings'] = settings
        
        options['git_revision'] = self.application.settings['git_revision']
        options['total_no_events'] = self.db.events.find().count()
        
        return options
    
    def share_keys_to_share_objects(self, shares):
        if not shares: 
            shares = ''
        keys = [x for x in shares.split(',') if x]
        return self.db.shares.find({'key':{'$in':keys}})
            

class APIHandlerMixin(object):
    
    def check_guid(self):
        guid = self.get_argument('guid', None)
        if guid:
            user = self.db.users.one({'guid':guid})
            if user:
                return user
            else:
                self.set_status(403)
                self.write("guid not recognized")
        else:
            self.set_status(404)
            self.write("guid not supplied")
            
        self.set_header('Content-Type', 'text/plain')

    def check_xsrf_cookie(self):
        """use this to check the guid"""
        if not self.check_guid():
            raise tornado.web.HTTPError(403, "guid not right")
        
    def get_error_html(self, status_code, **kwargs):
        return "ERROR: %(code)d: %(message)s\n" % \
         dict(code=status_code, 
              message=httplib.responses[status_code])


@route('/')
class HomeHandler(BaseHandler):
    
    def get(self):
        
        if self.get_argument('share', None):
            shared_keys = self.get_secure_cookie('shares')
            if not shared_keys:
                shared_keys = []
            else:
                shared_keys = [x.strip() for x in shared_keys.split(',')
                               if x.strip() and self.db.shares.Share.one(dict(key=x))]
            
            key = self.get_argument('share')
            share = self.db.shares.Share.one(dict(key=key))
            if share.key not in shared_keys:
                shared_keys.append(share.key)
                
            self.set_secure_cookie("shares", ','.join(shared_keys), expires_days=70)
            return self.redirect('/')

        # default settings
        options = self.get_base_options()
        
        user = options['user']
        
        hidden_shares = self.get_secure_cookie('hidden_shares')
        if not hidden_shares: 
            hidden_shares = ''
        hidden_keys = [x for x in hidden_shares.split(',') if x]
        hidden_shares = []
        for share in self.db.shares.find({'key':{'$in':hidden_keys}}):
            className = 'share-%s' % share['user'].id
            hidden_shares.append(dict(key=share['key'],
                                      className=className))

        options['settings']['hidden_shares'] = hidden_shares
        
        self.render("calendar.html", 
          #
          **options
        )

        
         
@route(r'/events(\.json|\.js|\.xml|\.txt)?')
class EventsHandler(BaseHandler):
    
    def get(self, format=None):
        user = self.get_current_user()
        shares = self.get_secure_cookie('shares')
        
        data = self.get_events_data(user, shares)
        self.write_events_data(data, format)
        
        
    def get_events_data(self, user, shares):
        events = []
        sharers = []
        tags = set()

        start = parse_datetime(self.get_argument('start'))
        end = parse_datetime(self.get_argument('end'))
        search = {}
        search['start'] = {'$gte': start}
        search['end'] = {'$lte': end}

        if user:
            search['user.$id'] = user['_id']
            for event in self.db.events.find(search):
                events.append(self.transform_fullcalendar_event(event, True))
                tags.update(event['tags'])
                
        for share in self.share_keys_to_share_objects(shares):
            share_user = self.db.users.one(dict(_id=share['user'].id))
            search['user.$id'] = share_user['_id']
            className = 'share-%s' % share_user['_id']
            full_name = u"%s %s" % (share_user['first_name'], share_user['last_name'])
            full_name = full_name.strip()
            if not full_name:
                full_name = share_user['email']
            sharers.append(dict(className=className,
                                full_name=full_name,
                                key=share['key']))
                                
            for event in self.db.events.find(search):
                events.append(
                  self.transform_fullcalendar_event(
                    event, 
                    True,
                    className=className,
                    editable=False))
                tags.update(event['tags'])
                
        tags = list(tags)
        tags.sort(lambda x, y: cmp(x.lower(), y.lower()))
        tags = ['@%s' % x for x in tags]
        data = dict(events=events,
                    tags=tags)
                    
                    
        if sharers:
            sharers.sort(lambda x,y: cmp(x['full_name'], y['full_name']))
            data['sharers'] = sharers
            
        return data
            
    def write_events_data(self, data, format):
        if format in ('.json', '.js', None):
            self.write_json(data, javascript=format=='.js')
        elif format == '.xml':
            self.write_xml(data)
        elif format == '.txt':
            out = cStringIO.StringIO()
            out.write('ENTRIES\n')
            for event in data['events']:
                pprint(event, out)
                out.write("\n")
            out.write('TAGS\n')
            out.write('\n'.join(data['tags']))
            out.write("\n")
            self.write_txt(out.getvalue())
        
        
    def post(self, format=None):#, *args, **kwargs):
        user = self.get_current_user()
        
        if not user:
            user = self.db.users.User()
            user.save()
        event, created = self.create_event(user)
        
        if not self.get_secure_cookie('user'):
            # if you're not logged in, set a cookie for the user so that
            # this person can save the events without having a proper user
            # account.
            self.set_secure_cookie("guid", str(user.guid), expires_days=14)
        
        self.write_event(event, format)
        
           
    def create_event(self, user):
        title = self.get_argument("title")
        
        all_day = niceboolean(self.get_argument("all_day", False))
        if self.get_argument("date", None):
            date = self.get_argument("date")
            try:
                date = parse_datetime(date)
            except DatetimeParseError:
                raise tornado.web.HTTPError(400, "Invalid date")
            start = end = date
            if self.get_argument('all_day', -1) == -1:
                # it wasn't specified
                if date.hour + date.minute + date.second == 0:
                    all_day = True
                else:
                    all_day = False
            if not all_day:
                # default is to make it one hour 
                end += datetime.timedelta(hours=1)
        elif self.get_argument('start', None) and self.get_argument('end', None):
            start = parse_datetime(self.get_argument('start'))
            end = parse_datetime(self.get_argument('end'))
            if end <= start:
                raise tornado.web.HTTPError(400, "'end' must be greater than 'start'")
        elif self.get_argument('start', None) or self.get_argument('end', None):
            raise tornado.web.HTTPError(400, "Need both 'start' and 'end'")
        else:
            # if no date of any kind was specified, assume that it was an all day
            # event unless it explicitely set all_day=False
            if self.get_argument('all_day', -1) != -1 and not all_day:
                start = datetime.datetime.now()
                end = start + datetime.timedelta(hours=1)
                all_day = False
            else:
                date = datetime.date.today()
                date = datetime.datetime(date.year, date.month, date.day, 0, 0, 0)
                start = end = date
                all_day = True
        
        tags = list(set([x[1:] for x in re.findall(r'\B@[\w\-\.]+', title)]))
        self.case_correct_tags(tags, user)
        
        event = self.db.events.Event.one({
          'user.$id': user._id,
          'title': title,
          'start': start,
          'end': end
        })
        if event:
            return event, False
            
        event = self.db.events.Event()
        event.user = self.db.users.User(user)
        event.title = title
        event.tags = tags
        event.all_day = all_day
        event.start = start
        event.end = end
        event.save()
        
        return event, True
    
    def write_event(self, event, format):
        fullcalendar_event = self.transform_fullcalendar_event(event, serialize=True)
        
        result = dict(event=fullcalendar_event,
                      tags=['@%s' % x for x in event.tags],
                      )
        if format == '.xml':
            self.set_header("Content-Type", "text/xml; charset=UTF-8")
            self.write(dict_to_xml(result))
        else:
            # default is json
            self.set_header("Content-Type", "application/json")
            self.write(tornado.escape.json_encode(result))

        
@route(r'/api/events(\.json|\.js|\.xml|\.txt)?')
class APIEventsHandler(APIHandlerMixin, EventsHandler):
    
    def get(self, format=None):
        user = self.check_guid()
        if not user:
            return 
            
        start = self.get_argument('start', None) 
        if not start:
            self.set_status(404)
            return self.write("start timestamp not supplied")
        
        end = self.get_argument('end', None) 
        if not end:
            self.set_status(404)
            return self.write("end timestamp not supplied")        
        
        shares = self.get_argument('shares', u'')#self.get_secure_cookie('shares')
        
        data = self.get_events_data(user, shares)
        self.write_events_data(data, format)
        
        
    def post(self, format):
        
        if not self.application.settings.get('xsrf_cookies'):
            if not self.check_guid():
                return
            
        def get(key):
            return self.get_argument(key, None)
            
        if not get('title'):
            self.set_status(400)
            return self.write("Missing 'title'")
        
            #self.set_status(404)
            #return self.write("title not supplied")
        elif len(get('title')) > MAX_TITLE_LENGTH:
            self.set_status(400)
            return self.write(
             "Title too long (max %s)" % MAX_TITLE_LENGTH)

        #if not (get('date') or (get('start') and get('end'))):
        #    self.set_status(404)
        #    return self.write("date or (start and end) not supplied")
        
        guid = self.get_argument('guid')
        user = self.db.users.User.one({'guid': guid})
        
        event, created = self.create_event(user)
        self.write_event(event, format)
        self.set_status(created and 201 or 200) # Created
            
#@route(r'/events(\.json|\.js|\.xml|\.txt)?')
        
class BaseEventHandler(BaseHandler):
    
    def write_event_data(self, data, format):
        if format in ('.json', '.js', None):
            self.write_json(data, javascript=format=='.js')
        elif format == '.xml':
            self.write_xml(data)
        elif format == '.txt':
            out = cStringIO.StringIO()
            out.write('EVENT\n')
            pprint(data, out)
            out.write("\n")
            self.write_txt(out.getvalue())
        elif format == '.html':
            ui_module = ui_modules.EventPreview(self)
            self.write(ui_module.render(data))
        else:
            raise NotImplementedError

    def find_event(self, _id, user, shares):
        try:
            search = {
              '_id': ObjectId(_id),
            }
        except InvalidId:
            raise tornado.web.HTTPError(404, "Invalid ID")
        
        event = self.db.events.Event.one(search)
        if not event:
            raise tornado.web.HTTPError(404, "Can't find the event")
        
        if event.user == user:
            pass
        elif shares:
            # Find out if for any of the shares we have access to the owner of
            # the share is the same as the owner of the event
            for share in self.share_keys_to_share_objects(shares):
                if share['user'].id == event['user']['_id']:
                    if share['users']:
                        if user['_id'] in [x.id for x in share['users']]:
                            break
                    else:
                        break
            else:
                raise tornado.web.HTTPError(403, "Not your event (not shared either)")
        else:
            raise tornado.web.HTTPError(403, "Not your event")
            
        return event
    
@route(r'/event(\.json|\.js|\.xml|\.txt|\.html)?')
class EventHandler(BaseEventHandler):
    def get(self, format):
        #if action == '':
        #    action = 'preview'
        #assert action in ('edit', 'preview')
        
        _id = self.get_argument('id')
       
        user = self.get_current_user()
        if not user:
            return self.write(dict(error="Not logged in (no cookie)"))
        
        shares = self.get_secure_cookie('shares')
        event = self.find_event(_id, user, shares)
        
        if format == '.html':
            data = event
        else:
            data = self.transform_fullcalendar_event(event, True)
        self.write_event_data(data, format)
        
        #if 0 and action == 'edit':
        #    external_url = getattr(event, 'external_url', None)
        #    self.render('event/edit.html', event=event, url=external_url)
        #elif format == 'html':
        #    ui_module = ui_modules.EventPreview(self)
        #    self.write(ui_module.render(event))
        #elif format == '
    
@route(r'/event/(edit|resize|move|delete|)')
class EditEventHandler(BaseEventHandler):
    
    def post(self, action):
        _id = self.get_argument('id')

        if action in ('move', 'resize'):
            days = int(self.get_argument('days'))
            minutes = int(self.get_argument('minutes'))
            if action == 'move':
                all_day = niceboolean(self.get_argument('all_day', False))
        elif action == 'delete':
            pass
        else:
            assert action == 'edit'
            title = self.get_argument('title')
            external_url = self.get_argument('external_url', u"")
            if external_url == u"URL: (optional)":
                external_url = u""
            if external_url:
                # check that it's valid
                from urlparse import urlparse
                parsed = urlparse(external_url)
                if not (parsed.scheme and parsed.netloc):
                    raise tornado.web.HTTPError(400, "Invalid URL (%s)" % external_url)

        user = self.get_current_user()
        if not user:
            return self.write(dict(error="Not logged in (no cookie)"))
            #raise tornado.web.HTTPError(403)
            
        try:
            search = {
              'user.$id': user._id,
              '_id': ObjectId(_id),
            }
        except InvalidId:
            raise tornado.web.HTTPError(404, "Invalid ID")
        
        event = self.db.events.Event.one(search)
        if not event:
            raise tornado.web.HTTPError(404, "Can't find the event")
        
        if action == 'resize':
            if event.all_day and not days and minutes:
                return self.write_json(dict(error=\
              "Can't resize an all-day event in minutes"))
            elif not event.all_day and days and not minutes:
                return self.write_json(dict(error=\
              "Can't resize an hourly event in days"))
            event.end += datetime.timedelta(days=days, minutes=minutes)
            event.save()
        elif action == 'move':
            event.start += datetime.timedelta(days=days, minutes=minutes)
            event.end += datetime.timedelta(days=days, minutes=minutes)
            event.all_day = all_day
            event.save()
        elif action == 'edit':
            tags = list(set([x[1:] for x in re.findall('@\w+', title)]))
            event.title = title
            event.external_url = external_url
            event.tags = tags
            if getattr(event, 'url', -1) != -1:
                # NEED MIGRATION SCRIPTS!
                del event['url']
            event.save()
        elif action == 'delete':
            event.delete()
            return self.write("Deleted")
        else:
            raise NotImplementedError
        
        return self.write_json(dict(event=self.transform_fullcalendar_event(event, True)))
    
        
            
@route('/events/stats(\.json|\.xml|\.txt)?')
class EventStatsHandler(BaseHandler):
    def get(self, format):
        days_spent = defaultdict(float)
        hours_spent = defaultdict(float)
        user = self.get_current_user()
        if user:
            search = {'user.$id': user._id}
            
            if self.get_argument('start', None):
                start = parse_datetime(self.get_argument('start'))
                search['start'] = {'$gte': start}
            if self.get_argument('end', None):
                end = parse_datetime(self.get_argument('end'))
                search['end'] = {'$lte': end}
                
            for entry in self.db.events.find(search):
                if entry['all_day']:
                    days = 1 + (entry['end'] - entry['start']).days
                    if entry['tags']:
                        for tag in entry['tags']:
                            days_spent[tag] += days
                    else:
                        days_spent[u''] += days
                    
                else:
                    hours = (entry['end'] - entry['start']).seconds / 60.0 / 60
                    if entry['tags']:
                        for tag in entry['tags']:
                            hours_spent[tag] += hours
                    else:
                        hours_spent[u''] += hours
                     
        if '' in days_spent:
            days_spent['<em>Untagged</em>'] = days_spent.pop('')
        if '' in hours_spent:
            hours_spent['<em>Untagged</em>'] = hours_spent.pop('')
        
        # flatten as a list
        days_spent = sorted(days_spent.items())
        hours_spent = sorted([(x,y) for (x, y) in hours_spent.items() if y])
        stats = dict(days_spent=days_spent,
                     hours_spent=hours_spent)
                
        if format == '.json':
            self.write_json(stats)
        elif format == '.xml':
            self.write_xml(stats)
        elif format == '.txt':
            out = cStringIO.StringIO()
            for key, values in stats.items():
                out.write('%s:\n' % key.upper().replace('_', ' '))
                
                for tag, num in values:
                    tag = re.sub('</?em>', '*', tag)
                    out.write('  %s%s\n' % (tag.ljust(40), num))
                out.write('\n')
                
            self.write_txt(out.getvalue())
        
            
@route('/user/settings(.js|/)')
class UserSettingsHandler(BaseHandler):
    def get(self, format=None):
        # default initials
        hide_weekend = False
        monday_first = False
        disable_sound = False
        offline_mode = False
        
        user = self.get_current_user()
        if user:
            user_settings = self.get_current_user_settings(user)
            if user_settings:
                hide_weekend = user_settings.hide_weekend
                monday_first = user_settings.monday_first
                disable_sound = user_settings.disable_sound
                offline_mode = getattr(user_settings, 'offline_mode', False)
            else:
                user_settings = self.db.user_settings.UserSettings()
                user_settings.user = user
                user_settings.save()

        if format == '.js':
            data = dict(hide_weekend=hide_weekend,
                        monday_first=monday_first,
                        disable_sound=disable_sound,
                        offline_mode=offline_mode)
            self.set_header("Content-Type", "text/javascript; charset=UTF-8")
            self.set_header("Cache-Control", "public,max-age=0")
            self.write('var SETTINGS=%s;' % tornado.escape.json_encode(data))
        else:
            _locals = locals()
            _locals.pop('self')
            self.render("user/settings.html", **_locals)
        
    def post(self, format=None):
        user = self.get_current_user()
        if not user:
            user = self.db.users.User()
            user.save()
            self.set_secure_cookie("guid", str(user.guid), expires_days=100)
            
        user_settings = self.get_current_user_settings(user)
        if user_settings:
            hide_weekend = user_settings.hide_weekend
            monday_first = user_settings.monday_first
            disable_sound = user_settings.disable_sound
            offline_mode = getattr(user_settings, 'offline_mode', False)
        else:
            user_settings = self.db.user_settings.UserSettings()
            user_settings.user = user
            user_settings.save()
                
        for key in ('monday_first', 'hide_weekend', 'disable_sound', 'offline_mode'):
            user_settings[key] = bool(self.get_argument(key, None))
        user_settings.save()
        self.redirect("/")
        #self.render("user/settings-saved.html")
        
@route('/share/$')
class SharingHandler(BaseHandler):
    
    def get(self):
        user = self.get_current_user()
        if not user:
            return self.write("You don't have anything in your calendar yet")
        
        if not (user.email or user.first_name or user.last_name):
            self.render("sharing/cant-share-yet.html")
            return 
        
        shares = self.db.shares.Share.find({'user.$id': user._id})
        count = shares.count()
        if count:
            if count == 1:
                share = list(shares)[0]
            else:
                raise NotImplementedError
        else:
            share = self.db.shares.Share()
            share.user = user
            # might up this number in the future
            share.key = Share.generate_new_key(self.db.shares, min_length=7)
            share.save()
            
        share_url = "/?share=%s" % share.key
        full_share_url = '%s://%s%s' % (self.request.protocol, 
                                        self.request.host,
                                        share_url)
        self.render("sharing/share.html", full_share_url=full_share_url, shares=shares)
        
    def post(self):
        """toggle the hiding of a shared key"""
        key = self.get_argument('key')
        shares = self.get_secure_cookie('shares')
        if not shares: 
            shares = ''
        keys = [x for x in shares.split(',') if x]
        if keys:
            keys = [x.key for x in self.db.shares.Share.find({'key':{'$in':keys}})]
        if key not in keys:
            raise tornado.web.HTTPError(404, "Not a key that has been shared with you")
        
        hidden_shares = self.get_secure_cookie('hidden_shares')
        if not hidden_shares: 
            hidden_shares = ''
        hidden_keys = [x for x in hidden_shares.split(',') if x]
        if key in hidden_keys:
            hidden_keys.remove(key)
        else:
            hidden_keys.insert(0, key)
        self.set_secure_cookie('hidden_shares', ','.join(hidden_keys), expires_days=70)
        
        self.write('Ok')

        
@route('/user/account/')
class AccountHandler(BaseHandler):
    def get(self):
        if self.get_secure_cookie('user'):
            user = self.db.users.User.one(dict(guid=self.get_secure_cookie('user')))
            if not user:
                return self.write("Error. User does not exist")
            options = dict(
              email=user.email,
              first_name=user.first_name,
              last_name=user.last_name,
            )
    
            self.render("user/change-account.html", **options)
        else:
            self.render("user/account.html")
            
    @login_required
    def post(self):
        email = self.get_argument('email').strip()
        first_name = self.get_argument('first_name', u"").strip()
        last_name = self.get_argument('last_name', u"").strip()
        
        if not valid_email(email):
            raise tornado.web.HTTPError(400, "Not a valid email address")

        guid = self.get_secure_cookie('user')
        user = self.db.users.User.one(dict(guid=guid))
        
        existing_user = self.find_user(email)
        if existing_user and existing_user != user:
            raise tornado.web.HTTPError(400, "Email address already used by someone else")

        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        self.redirect('/')
        
@route('/user/signup/')
class SignupHandler(BaseHandler):
          
    def get(self):
        if self.get_argument('validate_email', None):
            # some delay to make brute-force testing boring
            sleep(0.5) # XXX This needs to be converted into an async call!
            
            email = self.get_argument('validate_email').strip()
            if self.has_user(email):
                result = dict(error='taken')
            else:
                result = dict(ok=True)
            self.write_json(result)
        else:
            raise tornado.web.HTTPError(404, "Nothing to check")
            
    def post(self):
        email = self.get_argument('email')
        password = self.get_argument('password')
        first_name = self.get_argument('first_name', u'')
        last_name = self.get_argument('last_name', u'')
        
        if not email:
            return self.write("Error. No email provided")
        elif not valid_email(email):
            raise tornado.web.HTTPError(400, "Not a valid email address")
        if not password:
            return self.write("Error. No password provided")
        
        if self.has_user(email):
            return self.write("Error. Email already taken")
        
        if len(password) < 4:
            return self.write("Error. Password too short")
        
        user = self.get_current_user()
        if not user:
            user = self.db.users.User()
            user.save()
        user.email = email
        user.password = encrypt_password(password)
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        self.set_secure_cookie("guid", str(user.guid), expires_days=100)
        self.set_secure_cookie("user", str(user.guid), expires_days=100)
            
        self.redirect('/')

        
#class FeedHandler(BaseHandler):
#    def get(self):
#        entries = self.db.query("SELECT * FROM entries ORDER BY published "
#                                "DESC LIMIT 10")
#        self.set_header("Content-Type", "application/atom+xml")
#        self.render("feed.xml", entries=entries)




@route('/auth/login/')
class AuthLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    
#    @tornado.web.asynchronous
#    def get(self):
#        if self.get_argument("openid.mode", None):
#            self.get_authenticated_user(self.async_callback(self._on_auth))
#            return
#        self.authenticate_redirect()
#    
#    def _on_auth(self, user):
#        if not user:
#            raise tornado.web.HTTPError(500, "Google auth failed")
#        author = self.db.get("SELECT * FROM authors WHERE email = %s",
#                             user["email"])
#        if not author:
#            # Auto-create first author
#            any_author = self.db.get("SELECT * FROM authors LIMIT 1")
#            if not any_author:
#                author_id = self.db.execute(
#                    "INSERT INTO authors (email,name) VALUES (%s,%s)",
#                    user["email"], user["name"])
#            else:
#                self.redirect("/")
#                return
#        else:
#            author_id = author["id"]
#        self.set_secure_cookie("user", str(author_id))
#        self.redirect(self.get_argument("next", "/"))
        
    def post(self):
        email = self.get_argument('email')
        password = self.get_argument('password')
        user = self.find_user(email)
        if not user:
            # The reason for this sleep is that if a hacker tries every single
            # brute-force email address he can think of he would be able to 
            # get quick responses and test many passwords. Try to put some break
            # on that. 
            sleep(0.5)
            return self.write("Error. No user by that email address")
        
        if not user.check_password(password):
            return self.write("Error. Incorrect password")
            
        self.set_secure_cookie("guid", str(user.guid), expires_days=100)
        self.set_secure_cookie("user", str(user.guid), expires_days=100)
        
        self.redirect("/")
        


@route(r'/auth/logout/')
class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.clear_cookie("shares")
        self.clear_cookie("guid")
        self.clear_cookie("hidden_shares")
        self.redirect(self.get_argument("next", "/"))


@route(r'/help/(\w*)')
class HelpHandler(BaseHandler):
    
    def get(self, page):
        options = self.get_base_options()
        self.application.settings['template_path']
        if page == '':
            page = 'index'
        filename = "help/%s.html" % page.lower()
        if os.path.isfile(os.path.join(self.application.settings['template_path'],
                                       filename)):
            if page == 'API':
                self._extend_api_options(options)
            elif page == 'Bookmarklet':
                self._extend_bookmarklet_options(options)
                
            return self.render(filename, **options)
        raise tornado.web.HTTPError(404, "Unknown page")

    def _extend_bookmarklet_options(self, options):
        url = '/static/bookmarklet.js'
        url = '%s://%s%s' % (self.request.protocol, 
                             self.request.host,
                             url)
        options['full_bookmarklet_url'] = url
    
    def _extend_api_options(self, options):
        """get all the relevant extra variables for the API page"""
        user = self.get_current_user()
        options['base_url'] = '%s://%s' % (self.request.protocol, 
                                           self.request.host)
        options['sample_guid'] = '6a971ed0-7105-49a4-9deb-cf1e44d6c718'
        options['guid'] = None
        if user:
            options['guid'] = user.guid
            options['sample_guid'] = user.guid
        
        t = datetime.date.today()
        first = datetime.date(t.year, t.month, 1)
        if t.month == 12:
            last = datetime.date(t.year + 1, 1, 1)
        else:
            last = datetime.date(t.year, t.month + 1, 1)
        last -= datetime.timedelta(days=1)
        options['sample_start_timestamp'] = int(mktime(first.timetuple()))
        options['sample_end_timestamp'] = int(mktime(last.timetuple()))        
    
        code = """
        >>> import datetime
        >>> from donecal import DoneCal
        >>> dc = DoneCal('XXXXXX-XXXX-XXXX-XXXX-XXXXXX')
        >>> data = dc.get_events(datetime.date(2010, 10, 1),
        ...                      datetime.datetime.now())
        >>> print data['tags']
        ['@ProjectX', '@ProjectY']
        >>> from pprint import pprint
        >>> pprint(data['events'][0])
        {'all_day': True,
        'end': datetime.datetime(2010, 10, 20, 0, 0),
        'id': '4cb086b06da6812276000001',
        'start': datetime.datetime(2010, 10, 20, 0, 0),
        'title': "Testing stuff on @ProjectX"}
        >>> # Now to post something
        >>> event, created = dc.add_event("Testing more stuff",
        ...    date=datetime.datetime(2010, 11, 1))
        >>> print "Created?", created and "yes" or "no"
        yes
        """
        code = '\n'.join(x.lstrip() for x in code.splitlines())
        options['code_pythondonecal_1'] = code.strip()

@route(r'/bookmarklet/')
class Bookmarklet(BaseHandler):
    
    def get(self):
        external_url = self.get_argument('external_url', u'')
        
        user = self.get_current_user()
        
        title = u""
        doc_title = self.get_argument('doc_title', u'')
        if doc_title:
            tags = self._suggest_tags(user, doc_title)
            if tags:
                title = ' '.join(tags) + ' '
        self.render("bookmarklet.html", 
                    external_url=external_url, 
                    title=title)
        
    def _suggest_tags(self, user, title):
        """given a user and a title (e.g. 'Tra the la [Foo]') return a list of
        tags that are in that string. Disregard English stopwords."""
        tags = []
        
        
        return ['@%s' % x for x in tags]
        
    
def main():
    tornado.options.parse_command_line()
    if options.showurls:
        for path, class_ in route.get_routes():
            print path
        return
    http_server = tornado.httpserver.HTTPServer(Application())
    print "Starting tornado on port", options.port
    if options.prefork:
        print "\tpre-forking"
        http_server.bind(options.port)
        http_server.start()
    else:
        http_server.listen(options.port)
    
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

    