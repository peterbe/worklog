# python
import traceback
import httplib
from hashlib import md5
from cStringIO import StringIO
from urlparse import urlparse
from pprint import pprint
from collections import defaultdict
from pymongo.objectid import InvalidId, ObjectId
from time import mktime, sleep
import datetime
import os.path
import re
import logging

# tornado
import tornado.auth
import tornado.web

# app
from utils.routes import route
from models import *
from utils.datatoxml import dict_to_xml
from utils.send_mail import send_email
from utils.decorators import login_required
from utils import parse_datetime, niceboolean, \
  DatetimeParseError, valid_email, random_string, \
  all_hash_tags, all_atsign_tags

from ui_modules import EventPreview
from config import *
from apps.eventlog import log_event, actions, contexts


def title_to_tags(title):
    return list(set([x[1:] for x in re.findall(r'\B[@#][\w\-\.]+', title, re.U)]))

class HTTPSMixin(object):
    
    def is_secure(self):
        # XXX is this really the best/only way?
        return self.request.headers.get('X-Scheme') == 'https'
    
    def httpify_url(self):
        return self.request.full_url().replace('https://', 'http://')

    def httpsify_url(self):
        return self.request.full_url().replace('http://', 'https://')
    

class BaseHandler(tornado.web.RequestHandler, HTTPSMixin):
    def _handle_request_exception(self, exception):
        if not isinstance(exception, tornado.web.HTTPError) and \
          not self.application.settings['debug']:
            print "About to email"
            # ie. a 500 error
            try:
                self._email_exception(exception)
            except:
                print "** Failing even to email exception **"

        if self.application.settings['debug']:
            # Because of
            # https://groups.google.com/d/msg/python-tornado/Zjv6_3OYaLs/CxkC7eLznv8J
            print "Exception!"
            print exception
        super(BaseHandler, self)._handle_request_exception(exception)
         
    def _log(self):
        """overwritten from tornado.web.RequestHandler because we want to put 
        all requests as logging.debug and keep all normal logging.info()"""
        if self._status_code < 400:
            #log_method = logging.info
            log_method = logging.debug
        elif self._status_code < 500:
            log_method = logging.warning
        else:
            log_method = logging.error
        request_time = 1000.0 * self.request.request_time()
        log_method("%d %s %.2fms", self._status_code,
                   self._request_summary(), request_time)
   
        
    def _email_exception(self, exception): # pragma: no cover
        import sys
        from pprint import pprint
        err_type, err_val, err_traceback = sys.exc_info()
        error = u'%s: %s' % (err_type, err_val)
        out = StringIO()
        subject = "%r on %s" % (err_val, self.request.path)
        print >>out, "TRACEBACK:"
        traceback.print_exception(err_type, err_val, err_traceback, 500, out)
        traceback_formatted = out.getvalue()
        print traceback_formatted
        print >>out, "\nREQUEST ARGUMENTS:"
        arguments = self.request.arguments
        if arguments.get('password') and arguments['password'][0]:
            password = arguments['password'][0]
            arguments['password'] = password[:2] + '*' * (len(password) -2)
        pprint(arguments, out)
        
        print >>out, "\nCOOKIES:"
        for cookie in self.cookies:
            print >>out, "  %s:" % cookie,
            print >>out, repr(self.get_secure_cookie(cookie))
            
        print >>out, "\nREQUEST:"
        for key in ('full_url', 'protocol', 'query', 'remote_ip', 
                    'request_time', 'uri', 'version'):
            print >>out, "  %s:" % key,
            value = getattr(self.request, key)
            if callable(value):
                try:
                    value = value()
                except:
                    pass
            print >>out, repr(value)
            
        print >>out, "\nGIT REVISION: ",
        print >>out, self.application.settings['git_revision']
        
        print >>out, "\nHEADERS:"
        pprint(dict(self.request.headers), out)
        
        send_email(self.application.settings['email_backend'],
                   subject, 
                   out.getvalue(),
                   self.application.settings['webmaster'],
                   self.application.settings['admin_emails'],
                   )
    
    @property
    def db(self):
        return self.application.con[self.application.database_name]
    

    def get_current_user(self):
        # the 'user' cookie is for securely logged in people
        guid = self.get_secure_cookie("user")
        if guid:
            return self.db.User.one({'guid': guid})
        
        # the 'guid' cookie is for people who have posted something but not 
        # logged in
        guid = self.get_secure_cookie("guid")
        if guid:
            return self.db.User.one({'guid': guid})
    
    # shortcut where the user parameter is not optional
    def get_user_settings(self, user, fast=False):
        return self.get_current_user_settings(user=user, fast=fast)
    
    def get_current_user_settings(self, user=None, fast=False):
        if user is None:
            user = self.get_current_user()
            
        if not user:
            raise ValueError("Can't get settings when there is no user")
        _search = {'user.$id': user['_id']}
        if fast:
            return self.db[UserSettings.__collection__].one(_search) # skip mongokit
        else:
            return self.db.UserSettings.one(_search)
        
    def create_user_settings(self, user, **default_settings):
        user_settings = self.db.UserSettings()
        user_settings.user = user
        for key in default_settings:
            setattr(user_settings, key, default_settings[key])
        user_settings.save()
        return user_settings
    
    def get_cdn_prefix(self):
        """return something that can be put in front of the static filename
        E.g. if filename is '/static/image.png' and you return '//cloudfront.com'
        then final URL presented in the template becomes
        '//cloudfront.com/static/image.png'
        """
        return self.application.settings.get('cdn_prefix')
        # at the time of writing, I'm just going to use the CDN if you're running
        # a secure connection. This is because the secure connection is limited
        # to paying customers and they deserve it
        if self.is_secure():
            return self.application.settings.get('cdn_prefix')
    
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
        if item.get('external_url'):
            data['external_url'] = item['external_url']
        if item.get('description'):
            data['description'] = item['description']
        if serialize:
            self.serialize_dict(data)
            #for key, value in data.items():
            #    if isinstance(value, (datetime.datetime, datetime.date)):
            #        #time_tuple = (2008, 11, 12, 13, 59, 27, 2, 317, 0)
            #        timestamp = mktime(value.timetuple())
            #        data[key] = timestamp
            
        return data
    
    def serialize_dict(self, data):
        for key, value in data.items():
            if isinstance(value, (datetime.datetime, datetime.date)):
                data[key] = mktime(value.timetuple())
        return data
        
    
    def case_correct_tags(self, tags, user):
        # the new correct case for these tags is per the parameter 'tags'
        # We need to change all other tags that are spelled with a different
        # case to this style 
        base_search = {
          'user.$id': user._id,
        }
        
        def get_checked_tags(event_tags, new_tag):
            checked_tags = []
            for t in event_tags:
                if t != tag and t.lower() == tag.lower():
                    checked_tags.append(tag)
                else:
                    checked_tags.append(t)
            return checked_tags
        
        for tag in tags:
            search = dict(base_search, 
                          tags=re.compile(re.escape(tag), re.I))
            
            for event in self.db[Event.__collection__].find(search):
                checked_tags = get_checked_tags(event['tags'], tag)
                if event['tags'] != checked_tags:
                    event['tags'] = checked_tags
                    # because 'event' is just a dict, we need to turn it into an object
                    # before we can save it
                    event_obj = self.db.Event(event)
                    event_obj.save()
                    
            for share in self.db[Share.__collection__].find(search):
                checked_tags = get_checked_tags(share['tags'], tag)
                if share['tags'] != checked_tags:
                    share['tags'] = checked_tags
                    obj = self.db.Share(share)
                    obj.save()
        
    def find_user(self, email):
        return self.db.User.one(dict(email=\
         re.compile(re.escape(email), re.I)))
         
    def has_user(self, email):
        return bool(self.find_user(email))
    
    def get_base_options(self):
        # The templates rely on these variables
        options = dict(user=None,
                       user_name=None)
                       
        # default settings
        settings = dict(hide_weekend=False,
                        monday_first=False,
                        disable_sound=False,
                        offline_mode=False,
                        ampm_format=False)

        user = self.get_current_user()
        user_name = None
        
        if user:
            if self.get_secure_cookie('user'):
                options['user'] = user
                if user.first_name:
                    user_name = user.first_name
                elif user.email:
                    user_name = user.email
                else:
                    user_name = "stranger"
                options['user_name'] = user_name
                
            # override possible settings
            user_settings = self.get_current_user_settings(user)
            if user_settings:
                settings['hide_weekend'] = user_settings.hide_weekend
                settings['monday_first'] = user_settings.monday_first
                settings['disable_sound'] = user_settings.disable_sound
                settings['offline_mode'] = getattr(user_settings, 'offline_mode', False)
                settings['ampm_format'] = user_settings.ampm_format
        
        options['settings'] = settings
        
        options['git_revision'] = self.application.settings['git_revision']
        options['total_no_events'] = self._get_total_no_events()
        options['debug'] = self.application.settings['debug']
        
        return options
    
    def _get_total_no_events(self):
        search = dict()
        undoer = self.get_undoer_user()
        if undoer:
            search['user.$id'] = {'$ne': undoer._id}
        return self.db[Event.__collection__].find(search).count()
    
    def share_keys_to_share_objects(self, shares):
        if not shares: 
            shares = ''
        keys = [x for x in shares.split(',') if x]
        return self.db[Share.__collection__].find({'key':{'$in':keys}})
    
    def get_all_available_tags(self, user):
        tags = set()
        search = {'user.$id': user['_id'],
                  'tags': {'$ne': []}}
        for event in self.db[Event.__collection__].find(search):
            for tag in event['tags']:
                tags.add(tag)
        return tags
    
    def get_undoer_user(self, create_if_necessary=False):
        guid = self.application.settings['UNDOER_GUID']
        undoer = self.db.User.one(dict(guid=guid))
        if undoer is None:
            undoer = self.db.User()
            undoer.guid = guid
            undoer.save()
        return undoer

    
            

class APIHandlerMixin(object):
 
    def check_guid(self):
        guid = self.get_argument('guid', None)
        if guid:
            user = self.db[User.__collection__].one({'guid':guid})
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
                               if x.strip() and \
                               self.db[Share.__collection__].one(dict(key=x))]
            
            key = self.get_argument('share')
            share = self.db.Share.one(dict(key=key))
            user = self.get_current_user()
            if user and user == share.user:
                # could flash a message or something here
                pass
            elif share.key not in shared_keys:
                shared_keys.append(share.key)
                
            if shared_keys:
                self.set_secure_cookie("shares", ','.join(shared_keys), expires_days=70)
            return self.redirect('/')

        # default settings
        options = self.get_base_options()
        user = options['user']
        if self.is_secure():
            # but are you allowed to use secure URLs?
            if not user or (user and not user['premium']):
                # not allowed!
                return self.redirect(self.httpify_url())
        else:
            if user and user['premium']:
                # allowed but not using it
                return self.redirect(self.httpsify_url())
            
        hidden_shares = self.get_secure_cookie('hidden_shares')
        if not hidden_shares: 
            hidden_shares = ''
        hidden_keys = [x for x in hidden_shares.split(',') if x]
        hidden_shares = []
        for share in self.db[Share.__collection__].find({'key':{'$in':hidden_keys}}):
            className = 'share-%s' % share['user'].id
            hidden_shares.append(dict(key=share['key'],
                                      className=className))

        options['settings']['hidden_shares'] = hidden_shares
        
        self.render("calendar.html", 
          #
          **options
        )

        
         
@route(r'/events(\.json|\.js|\.xml|\.txt|/)?')
class EventsHandler(BaseHandler):
    
    def get(self, format=None):
        user = self.get_current_user()
        shares = self.get_secure_cookie('shares')
        
        data = self.get_events_data(user, shares, 
                           include_tags=self.get_argument('include_tags', None))
        self.write_events_data(data, format)
        
        
    def get_events_data(self, user, shares, include_tags=False):
        events = list()
        sharers = list()
        data = dict()
        
        if include_tags == 'all':
            if user:
                tags = self.get_all_available_tags(user)
            else:
                tags = set()
        else:
            include_tags = niceboolean(include_tags)
            tags = set()
            
        try:
            start = parse_datetime(self.get_argument('start'))
        except DatetimeParseError, msg:
            raise tornado.web.HTTPError(400, str(msg))
        try:
            end = parse_datetime(self.get_argument('end'))
        except DatetimeParseError, msg:
            raise tornado.web.HTTPError(400, str(msg))
        search = {}
        search['start'] = {'$gte': start}
        search['end'] = {'$lt': end}

        if user:
            search['user.$id'] = user['_id']
            for event in self.db[Event.__collection__].find(search):
                events.append(self.transform_fullcalendar_event(event, True))
                if include_tags and include_tags != 'all':
                    tags.update(event['tags'])

        for share in self.share_keys_to_share_objects(shares):
            share_user = self.db[User.__collection__].one(dict(_id=share['user'].id))
            search['user.$id'] = share_user['_id']
            if share['tags']:
                search['tags'] = {'$in': share['tags']}
            className = 'share-%s' % share_user['_id']
            full_name = u"%s %s" % (share_user['first_name'], share_user['last_name'])
            full_name = full_name.strip()
            if not full_name:
                full_name = share_user['email']
            sharers.append(dict(className=className,
                                full_name=full_name,
                                key=share['key']))
                                
            for event in self.db[Event.__collection__].find(search):
                events.append(
                  self.transform_fullcalendar_event(
                    event, 
                    True,
                    className=className,
                    editable=False))
        
        data['events'] = events
        
        if include_tags:
            tags = list(tags)
            tags.sort(lambda x, y: cmp(x.lower(), y.lower()))
            if tags:
                # if the user prefers to start his tags with a # instead of an @
                # then we need to find that out by interrogating the user settings.b
                user_settings = self.get_current_user_settings(user, fast=True)
                if user_settings and user_settings['hash_tags']:
                    tags = ['#%s' % x for x in tags]
                else:
                    tags = ['@%s' % x for x in tags]
            data['tags'] = tags
            
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
            out = StringIO()
            out.write('ENTRIES\n')
            for event in data['events']:
                pprint(event, out)
                out.write("\n")
            if 'tags' in data:
                out.write('TAGS\n')
                out.write('\n'.join(data['tags']))
                out.write("\n")
            self.write_txt(out.getvalue())
        
        
    def post(self, format=None):#, *args, **kwargs):
        user = self.get_current_user()
        
        if not user:
            user = self.db.User()
            user.save()
            
        event, created = self.create_event(user)
        
        if created:
            log_event(self.db, user, event, actions.ACTION_ADD, contexts.CONTEXT_CALENDAR)
        
        if not self.get_secure_cookie('user'):
            # if you're not logged in, set a cookie for the user so that
            # this person can save the events without having a proper user
            # account.
            self.set_secure_cookie("guid", str(user.guid), expires_days=14)
        
        user_settings = self.get_current_user_settings(user, fast=True)
        if user_settings and user_settings['hash_tags']:
            tag_prefix = '#'
        else:
            tag_prefix = '@'
        self.write_event(event, format, tag_prefix=tag_prefix)
        
           
    def create_event(self, user, title=None, description=None, all_day=None,
                     external_url=None, start=None, end=None):
        if title is None:
            title = self.get_argument("title")
        
        if all_day is None:
            all_day = niceboolean(self.get_argument("all_day", False))
            
        if start is not None:
            # manually setting this
            if not isinstance(start, datetime.datetime):
                raise tornado.web.HTTPError(400, "start must be a datetime instance")
            if end is not None:
                if not isinstance(end, datetime.datetime):
                    raise tornado.web.HTTPError(400, "end must be a datetime instance")
            elif all_day:
                end = start
                
        elif self.get_argument("date", None):
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
                end += datetime.timedelta(seconds=MINIMUM_DAY_SECONDS)
        elif self.get_argument('start', None) and self.get_argument('end', None):
            start = parse_datetime(self.get_argument('start'))
            end = parse_datetime(self.get_argument('end'))
            if end <= start:
                raise tornado.web.HTTPError(400, "'end' must be greater than 'start'")
            if not all_day:
                # then the end must be >= (start + MINIMUM_DAY_SECONDS)
                if end < (start + datetime.timedelta(seconds=MINIMUM_DAY_SECONDS)):
                    raise tornado.web.HTTPError(400, 
                     "End must be at least %s minutes more than the start" % \
                     (MINIMUM_DAY_SECONDS / 60))
                if (end - start).days > 0:
                    raise tornado.web.HTTPError(400,
                      "Event length greater than 24 hours for an hourly event")
        elif self.get_argument('start', None) and \
          not self.get_argument('end', None) and not all_day:
            start = parse_datetime(self.get_argument('start'))
            end = start + datetime.timedelta(seconds=MINIMUM_DAY_SECONDS)
            
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

        tags = title_to_tags(title)
        if tags:
            user_settings = self.get_current_user_settings(user)
            hash_tags_prev = getattr(user_settings, 'hash_tags', None)
            if not hash_tags_prev and all_hash_tags(tags, title):
                # has changed! his mind
                if not user_settings:
                    self.create_user_settings(user, hash_tags=True)
                else:
                    user_settings.hash_tags = True
                    user_settings.save()
            else:
                # the user might have hash_tags on already
                # if that's the case and this one was with @ signs then change back
                if hash_tags_prev and all_atsign_tags(tags, title):
                    user_settings.hash_tags = False
                    user_settings.save()
                
        self.case_correct_tags(tags, user)
        
        event = self.db.Event.one({
          'user.$id': user._id,
          'title': title,
          'start': start,
          'end': end
        })
        if event:
            return event, False
            
        event = self.db.Event()
        event.user = self.db.User(user)
        event.title = title
        event.tags = tags
        event.all_day = all_day
        event.start = start
        event.end = end
        if description is not None:
            assert isinstance(description, unicode), type(description)
            event.description = description.strip()
        if external_url is not None:
            assert isinstance(external_url, unicode), type(external_url)
            event.external_url = external_url.strip()
        event.save()
        
        return event, True
    
    def write_event(self, event, format, tag_prefix='@'):
        fullcalendar_event = self.transform_fullcalendar_event(event, serialize=True)
        
        result = dict(event=fullcalendar_event,
                      tags=['%s%s' % (tag_prefix, x) for x in event.tags],
                      )
        if format == '.xml':
            self.set_header("Content-Type", "text/xml; charset=UTF-8")
            self.write(dict_to_xml(result))
        else:
            # default is json
            self.set_header("Content-Type", "application/json")
            self.write(tornado.escape.json_encode(result))

        
@route('/api/version(\.json|\.xml|\.txt|/)?')
class APIVersionHandler(APIHandlerMixin, BaseHandler):
    def get(self, format=None):
        version = "1.1"
            
        data = dict(version=version)
        if format == '.json':
            self.write_json(data)
        elif format == '.xml':
            self.write_xml(data)
        else:
            self.write_txt(unicode(data['version']))
        
            
@route(r'/api/events(\.json|\.js|\.xml|\.txt|/)?')
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
        
        data = self.get_events_data(user, shares,
            include_tags=self.get_argument('include_tags', None))
            
        if format == '.js':
            # pack the dict into a tuple instead.
            _events = []
            for event in data['events']:
                _events.append((
                  event['title'],
                  event['start'],
                  event['end'],
                  event['allDay'],
                  event['id'],
                  event.get('external_url', u''),
                  event.get('description', u''),
                ))
            data['events'] = _events
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
        user = self.db.User.one({'guid': guid})
        
        description = self.get_argument("description", None)
        external_url = self.get_argument("external_url", None)
        if external_url:
            # check that it's a valid URL
            parsed = urlparse(external_url.strip())
            if not (parsed.scheme and parsed.netloc):
                #raise tornado.web.HTTPError(400, "Invalid URL (%s)" % external_url)
                self.set_status(400)
                return self.write("Invalid URL")

        event, created = self.create_event(
          user,
          description=description,
          external_url=external_url,
        )
        
        if created:
            log_event(self.db, user, event, 
                      actions.ACTION_ADD, contexts.CONTEXT_API)
        
        user_settings = self.get_current_user_settings(user, fast=True)
        if user_settings and user_settings['hash_tags']:
            tag_prefix = '#'
        else:
            tag_prefix = '@'
        
        self.write_event(event, format, tag_prefix=tag_prefix)
        self.set_status(created and 201 or 200) # Created
            
@route(r'/events(\.json|\.js|\.xml|\.txt)?')
class BaseEventHandler(BaseHandler):
    
    def write_event_data(self, data, format):
        if format in ('.json', '.js', None):
            self.write_json(data, javascript=format=='.js')
        elif format == '.xml':
            self.write_xml(data)
        elif format == '.txt':
            out = StringIO()
            out.write('EVENT\n')
            pprint(data, out)
            out.write("\n")
            self.write_txt(out.getvalue())
        elif format == '.html':
            ui_module = EventPreview(self)
            self.write(ui_module.render(data))
        else:
            raise NotImplementedError(format)

    def find_event(self, _id, user, shares):
        try:
            search = {
              '_id': ObjectId(_id),
            }
        except InvalidId:
            raise tornado.web.HTTPError(404, "Invalid ID")
        
        event = self.db.Event.one(search)
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
    
@route(r'/event(\.json|\.js|\.xml|\.txt|\.html|/)?')
class EventHandler(BaseEventHandler):
    def get(self, format):
        if format == '/':
            format = None
            
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
    
@route(r'/event/(edit|resize|move|undodelete|delete|)/')
class EditEventHandler(BaseEventHandler):
    
    def post(self, action):
        _id = self.get_argument('id')

        if action in ('move', 'resize'):
            days = int(self.get_argument('days'))
            minutes = int(self.get_argument('minutes'))
            if action == 'move':
                all_day = niceboolean(self.get_argument('all_day', False))
        elif action in ('delete', 'undodelete'):
            pass
        else:
            assert action == 'edit'
            title = self.get_argument('title')
            external_url = self.get_argument('external_url', u"")
            if external_url == self.get_argument('placeholdervalue_external_url', None):
                external_url = u""
            if external_url:
                # check that it's valid
                parsed = urlparse(external_url)
                if not (parsed.scheme and parsed.netloc):
                    raise tornado.web.HTTPError(400, "Invalid URL (%s)" % external_url)
            description = self.get_argument('description', u"").strip()
            if description == self.get_argument('placeholdervalue_description', None):
                description = u""

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
    
        if action == 'undodelete':
            undoer = self.get_undoer_user()
            search['user.$id'] = undoer._id
        
        event = self.db.Event.one(search)
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
            tags = title_to_tags(title)
            event.title = title
            event.external_url = external_url
            event.description = description
            event.tags = tags
            if getattr(event, 'url', -1) != -1:
                # NEED MIGRATION SCRIPTS!
                del event['url']
            event.save()
        elif action == 'delete':
            # we never actually delete. instead we chown the event to belong to 
            # the special "undoer" user
            undoer = self.get_undoer_user(create_if_necessary=True)
            event.chown(undoer, save=True)
            
            log_event(self.db, user, event,
                      actions.ACTION_DELETE, 
                      contexts.CONTEXT_CALENDAR)
            
            return self.write("Deleted")
        
        elif action == 'undodelete':
            event.chown(user, save=True)
            
            log_event(self.db, user, event, actions.ACTION_RESTORE,
                      contexts.CONTEXT_CALENDAR)
        else:
            raise NotImplementedError(action)
        
        if action in ('edit','move','resize'):
            log_event(self.db, user, event, actions.ACTION_EDIT,
                      contexts.CONTEXT_CALENDAR, comment=unicode(action))
        
        return self.write_json(dict(event=self.transform_fullcalendar_event(event, True)))
    
        
            
@route('/events/stats(\.json|\.xml|\.txt|/)?')
class EventStatsHandler(BaseHandler):
    def get(self, format):
        
        stats = self.get_stats_data()
                
        if format == '.json':
            self.write_json(stats)
        elif format == '.xml':
            self.write_xml(stats)
        elif format == '.txt':
            out = StringIO()
            for key, values in stats.items():
                out.write('%s:\n' % key.upper().replace('_', ' '))
                
                for tag, num in values:
                    tag = re.sub('</?em>', '*', tag)
                    out.write('  %s%s\n' % (tag.ljust(40), num))
                out.write('\n')
                
            self.write_txt(out.getvalue())
            
    def get_stats_data(self):
        days_spent = defaultdict(float)
        hours_spent = defaultdict(float)
        user = self.get_current_user()
        with_colors = niceboolean(self.get_argument('with_colors', False))
        
        if user:
            search = {'user.$id': user._id}
            
            if self.get_argument('start', None):
                start = parse_datetime(self.get_argument('start'))
                search['start'] = {'$gte': start}
            if self.get_argument('end', None):
                end = parse_datetime(self.get_argument('end'))
                search['end'] = {'$lt': end}
                
            for entry in self.db[Event.__collection__].find(search):
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
                            hours_spent[tag] += round(hours, 1)
                    else:
                        hours_spent[u''] += round(hours, 1)
                        
                        
        _has_untagged_events = False
        
        if '' in days_spent:
            days_spent['<em>Untagged</em>'] = days_spent.pop('')
            _has_untagged_events = True
            
        if '' in hours_spent:
            hours_spent['<em>Untagged</em>'] = hours_spent.pop('')
            _has_untagged_events = True
        
        def cmp_tags(one, two):
            if one.startswith('<em>Untagged'):
                return -1
            elif two.startswith('<em>Untagged'):
                return 1
            return cmp(one.lower(), two.lower())
        
        # flatten as a list
        
        days_spent = days_spent.items()
        days_spent.sort(lambda x,y: cmp_tags(x[0], y[0]))
        
        hours_spent = [(x, round(y, 1)) for (x, y) in hours_spent.items() if y]
        hours_spent.sort(lambda x,y: cmp_tags(x[0], y[0]))
        
        
        data = dict(days_spent=days_spent,
                    hours_spent=hours_spent)
        if with_colors:
            # then define 'days_colors' and 'hours_colors'
            
            color_series = list()
            if _has_untagged_events:
                color_series.append(UNTAGGED_COLOR)
            color_series.extend(list(TAG_COLOR_SERIES))
            color_series.reverse()
            
            days_colors = []
            _map = {}
            for tag, __ in days_spent:
                color = color_series.pop()
                _map[tag] = color
                days_colors.append(color)
                
            data['days_colors'] = days_colors
            
            hours_colors = []
            for tag, __ in hours_spent:
                color = _map.get(tag)
                if color is None:
                    color = color_series.pop()
                hours_colors.append(color)
                
            data['hours_colors'] = hours_colors
            
        return data
                     
            
@route('/user/settings(\.js|/)$')
class UserSettingsHandler(BaseHandler):
    def get(self, format=None):
        # default initials
        default = dict()
        setting_keys = list()
        
        for key in UserSettings.get_bool_keys():
            default[key] = False
            setting_keys.append(key)
            
        user = self.get_current_user()
        if user:
            user_settings = self.get_current_user_settings(user)
            if user_settings:
                for key in setting_keys:
                    default[key] = getattr(user_settings, key, False)
            else:
                user_settings = self.db.UserSettings()
                user_settings.user = user
                user_settings.save()

        if format == '.js':
            self.set_header("Content-Type", "text/javascript; charset=UTF-8")
            self.set_header("Cache-Control", "public,max-age=0")
            self.write('var SETTINGS=%s;' % tornado.escape.json_encode(default))
        else:
            self.render("user/settings.html", **default)
        
    def post(self, format=None):
        user = self.get_current_user()
        if not user:
            user = self.db.User()
            user.save()
            self.set_secure_cookie("guid", str(user.guid), expires_days=100)
            
        user_settings = self.get_current_user_settings(user)
        if user_settings:
            hide_weekend = user_settings.hide_weekend
            monday_first = user_settings.monday_first
            disable_sound = user_settings.disable_sound
            offline_mode = getattr(user_settings, 'offline_mode', False)
        else:
            user_settings = self.db.UserSettings()
            user_settings.user = user
            user_settings.save()
                
        for key in ('monday_first', 'hide_weekend', 'disable_sound', 
                    'offline_mode', 'ampm_format'):
            user_settings[key] = bool(self.get_argument(key, None))
            
        user_settings.save()
        url = "/"
        if self.get_argument('anchor', None):
            if self.get_argument('anchor').startswith('#'):
                url += self.get_argument('anchor')
            else:
                url += '#%s' % self.get_argument('anchor')
            
        self.redirect(url)
        
@route('/share/$')
class SharingHandler(BaseHandler):
    
    def get(self):
        user = self.get_current_user()
        if not user:
            return self.write("You don't have anything in your calendar yet")
        
        if not (user.email or user.first_name or user.last_name):
            self.render("sharing/cant-share-yet.html")
            return 
        
        shares = self.db.Share.find({'user.$id': user._id})
        count = shares.count()
        if count:
            if count == 1:
                share = list(shares)[0]
            else:
                raise NotImplementedError
        else:
            share = self.db.Share()
            share.user = user
            # might up this number in the future
            share.key = Share.generate_new_key(self.db[Share.__collection__], min_length=7)
            share.save()
            
        share_url = "/?share=%s" % share.key
        full_share_url = '%s://%s%s' % (self.request.protocol, 
                                        self.request.host,
                                        share_url)
                                        
        chosen_tags = sorted(share.tags)
        available_tags = sorted([x for x in self.get_all_available_tags(user)
                                     if x not in chosen_tags])
        
        self.render("sharing/share.html", 
                    share_id=str(share._id),
                    full_share_url=full_share_url, 
                    shares=shares,
                    available_tags=available_tags,
                    chosen_tags=chosen_tags,
                    )
        
    def post(self):
        """toggle the hiding of a shared key"""
        key = self.get_argument('key')
        shares = self.get_secure_cookie('shares')
        if not shares: 
            shares = ''
        keys = [x for x in shares.split(',') if x]
        if keys:
            keys = [x.key for x in self.db.Share.find({'key':{'$in':keys}})]
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

@route('/share/edit/$')
class EditSharingHandler(SharingHandler):
    def post(self):
        _id = self.get_argument('id')
        tags = self.get_arguments('tags', [])
        
        user = self.get_current_user()
        try:
            share = self.db.Share.one({'_id': ObjectId(_id), 'user.$id': user._id})
            if not share:
                raise tornado.web.HTTPError(404, "Share not found")
        except Invalid:
            raise tornado.web.HTTPError(400, "Share ID not valid")
        
        share.tags = tags
        share.save()
        
        self.write("OK")
        
        
        
        
@route('/user/account/$')
class AccountHandler(BaseHandler):
    def get(self):
        if self.get_secure_cookie('user'):
            user = self.db.User.one(dict(guid=self.get_secure_cookie('user')))
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
        user = self.db.User.one(dict(guid=guid))
        
        existing_user = self.find_user(email)
        if existing_user and existing_user != user:
            raise tornado.web.HTTPError(400, "Email address already used by someone else")

        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        self.redirect('/')
    
hex_to_int = lambda s: int(s, 16)
int_to_hex = lambda i: hex(i).replace('0x', '')

@route('/user/forgotten/$')
class ForgottenPasswordHandler(BaseHandler):
    
    def get(self, error=None, success=None):
        options = self.get_base_options()
        options['error'] = error
        options['success'] = success
        self.render("user/forgotten.html", **options)
        
#    @tornado.web.asynchronous
    def post(self):
        email = self.get_argument('email')
        if not valid_email(email):
            raise tornado.web.HTTPError(400, "Not a valid email address")
        
        existing_user = self.find_user(email)
        if not existing_user:
            self.get(error="%s is a valid email address but no account exists matching this" % \
              email)
            return
        
        from tornado.template import Loader
        loader = Loader(self.application.settings['template_path'])
                      
        recover_url = self.lost_url_for_user(existing_user._id)
        recover_url = self.request.full_url() + recover_url
        email_body = loader.load('user/reset_password.txt')\
          .generate(recover_url=recover_url,
                    first_name=existing_user.first_name,
                    signature=self.application.settings['title'])
                    
        #if not isinstance(email_body, unicode):
        #    email_body = unicode(email_body, 'utf-8')
            
        if 1:#try:
            assert send_email(self.application.settings['email_backend'],
                      "Password reset for on %s" % self.application.settings['title'],
                      email_body,
                      self.application.settings['webmaster'],
                      [existing_user.email])
            
        else:#finally:
            pass #self.finish()
        
        return self.get(success="Password reset instructions sent to %s" % existing_user.email)
        
    ORIGIN_DATE = datetime.date(2000, 1, 1)
    
    
    def lost_url_for_user(self, user_id):
        days = int_to_hex((datetime.date.today() - self.ORIGIN_DATE).days)
        secret_key = self.application.settings['cookie_secret']
        hash = md5(secret_key + days + str(user_id)).hexdigest()
        return 'recover/%s/%s/%s/'%\
                       (user_id, days, hash)

    def hash_is_valid(self, user_id, days, hash):
        secret_key = self.application.settings['cookie_secret']
        if md5(secret_key + days + str(user_id)).hexdigest() != hash:
            return False # Hash failed
        # Ensure days is within a week of today
        days_now = (datetime.date.today() - self.ORIGIN_DATE).days
        days_old = days_now - hex_to_int(days)
        return days_old < 7
    
    
@route('/user/forgotten/recover/(\w+)/([a-f0-9]+)/([a-f0-9]{32})/$')
class RecoverForgottenPasswordHandler(ForgottenPasswordHandler):
    def get(self, user_id, days, hash, error=None):
        if not self.hash_is_valid(user_id, days, hash):
            return self.write("Error. Invalid link. Expired probably")
        user = self.db.User.one({'_id': ObjectId(user_id)})
        if not user:
            return self.write("Error. Invalid user")
        
        options = self.get_base_options()
        options['error'] = error
        self.render("user/recover_forgotten.html", **options)
        
    def post(self, user_id, days, hash):
        if not self.hash_is_valid(user_id, days, hash):
            raise tornado.web.HTTPError(400, "invalid hash")
        
        new_password = self.get_argument('password')
        if len(new_password) < 4:
            raise tornado.web.HTTPError(400, "password too short")
        
        user = self.db.User.one({'_id': ObjectId(user_id)})
        if not user:
            raise tornado.web.HTTPError(400, "invalid hash")
        
        user.set_password(new_password)
        user.save()
        
        #self.set_secure_cookie("guid", str(user.guid), expires_days=100)
        self.set_secure_cookie("user", str(user.guid), expires_days=100)
        
        self.redirect("/")
        
        
class BaseAuthHandler(BaseHandler):

    def get_next_url(self, default='/'):
        next = default
        if self.get_argument('next', None):
            next = self.get_argument('next')
        elif self.get_cookie('next', None):
            next = self.get_cookie('next')
            self.clear_cookie('next')
        return next
    
    def notify_about_new_user(self, user, extra_message=None):
        if self.application.settings['debug']:
            return
        try:
            self._notify_about_new_user(user, extra_message=extra_message)
        except:
            # I hate to have to do this but I don't want to make STMP errors
            # stand in the way of getting signed up
            logging.error("Unable to notify about new user", exc_info=True)
        
    def _notify_about_new_user(self, user, extra_message=None):
        subject = "[DoneCal] New user!"
        email_body = "%s %s\n" % (user.first_name, user.last_name)
        email_body += "%s\n" % user.email
        email_body += "%s events\n" % \
          self.db.Event.find({'user.$id': user._id}).count()
        if extra_message:
            email_body += '%s\n' % extra_message
        user_settings = self.get_current_user_settings(user)
        if user_settings:
            bits = []
            for key, value in UserSettings.structure.items():
                if value == bool:
                    yes_or_no = getattr(user_settings, key, False)
                    bits.append('%s: %s' % (key, yes_or_no and 'Yes' or 'No'))
            email_body += "User settings:\n\t%s\n" % ', '.join(bits)
            
        send_email(self.application.settings['email_backend'],
                   subject,
                   email_body,
                   self.application.settings['webmaster'],
                   self.application.settings['admin_emails'])


        
@route('/user/signup/')
class SignupHandler(BaseAuthHandler):
          
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
            user = self.db.User()
            user.save()
        user.email = email
        user.set_password(password)
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        self.notify_about_new_user(user)
        
        #self.set_secure_cookie("guid", str(user.guid), expires_days=100)
        self.set_secure_cookie("user", str(user.guid), expires_days=100)
            
        self.redirect('/')

        
#class FeedHandler(BaseHandler):
#    def get(self):
#        entries = self.db.query("SELECT * FROM entries ORDER BY published "
#                                "DESC LIMIT 10")
#        self.set_header("Content-Type", "application/atom+xml")
#        self.render("feed.xml", entries=entries)


        


@route('/auth/login/')
class AuthLoginHandler(BaseAuthHandler):
    
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
            
        #self.set_secure_cookie("guid", str(user.guid), expires_days=100)
        self.set_secure_cookie("user", str(user.guid), expires_days=100)
        
        if self.request.headers.get("X-Requested-With") != "XMLHttpRequest":
            self.redirect(self.get_next_url())
            

@route('/auth/openid/google/')
class GoogleAuthHandler(BaseAuthHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        if self.get_argument('next', None):
            # because this is going to get lost when we get back from Google
            # stick it in a cookie
            self.set_cookie('next', self.get_argument('next'))
        self.authenticate_redirect()
        
    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")
        if not user.get('email'):
            raise tornado.web.HTTPError(500, "No email provided")
        locale = user.get('locale') # not sure what to do with this yet
        first_name = user.get('first_name')
        last_name = user.get('last_name')
        email = user['email']
        
        user = self.db.User.one(dict(email=email))
        if user is None:
            user = self.db.User.one(dict(email=re.compile(re.escape(email), re.I)))
            
        if not user:
            # create a new account
            user = self.db.User()
            user.email = email
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.set_password(random_string(20))
            user.save()
            
            self.notify_about_new_user(user, extra_message="Used Google OpenID")
            
        self.set_secure_cookie("user", str(user.guid), expires_days=100)
        
        self.redirect(self.get_next_url())
        


@route(r'/auth/logout/')
class AuthLogoutHandler(BaseAuthHandler):
    def get(self):
        self.clear_all_cookies()
        #self.clear_cookie("user")
        #self.clear_cookie("shares")
        #self.clear_cookie("guid")
        #self.clear_cookie("hidden_shares")
        self.redirect(self.get_next_url())


@route(r'/help/([\w-]*)')
class HelpHandler(BaseHandler):
    
    SEE_ALSO = (
      ['/', u"Help"],
      u"About",
      u"News",
      ['/API', u"Developers' API"],
      u"Bookmarklet",
      ['/Google-calendar', u"Google Calendar"],
      u"Feature requests",
      ['/Secure-passwords', u"Secure passwords"],
      ['/Internet-Explorer', u"Internet Explorer"],
    )
    
    def get(self, page):
        options = self.get_base_options()
        self.application.settings['template_path']
        if page == '':
            page = 'index'
        
        filename = "help/%s.html" % page.lower()
        if os.path.isfile(os.path.join(self.application.settings['template_path'],
                                       filename)):
            if page.lower() == 'api':
                self._extend_api_options(options)
            elif page.lower() == 'bookmarklet':
                self._extend_bookmarklet_options(options)
                
            return self.render(filename, **options)
        
        raise tornado.web.HTTPError(404, "Unknown page")
    
    def get_see_also_links(self):
        for each in self.SEE_ALSO:
            if isinstance(each, basestring):
                link = '/%s' % each.replace(' ','-')
                label = each
            else:
                link, label = each
            yield dict(link=link, label=label)
            
    def _extend_bookmarklet_options(self, options):
        url = '/static/bookmarklet.js'
        url = '%s://%s%s' % (self.request.protocol, 
                             self.request.host,
                             url)
        options['full_bookmarklet_url'] = url
    
    def _extend_api_options(self, options):
        """get all the relevant extra variables for the API page"""
        user = self.get_current_user()
        options['can_https'] = user and user['premium']
        protocol = 'http'
        if options['can_https']:
            protocol = 'https'
        
        options['base_url'] = '%s://%s' % (protocol,
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
        
        options['minimum_day_minutes'] = MINIMUM_DAY_SECONDS / 60

@route(r'/bookmarklet/')
class Bookmarklet(EventsHandler):
    
    def get(self):
        external_url = self.get_argument('external_url', u'')
        
        user = self.get_current_user()
        
        title = u""
        #doc_title = self.get_argument('doc_title', u'')
        if external_url and user:#doc_title:
            tags = self._suggest_tags(user, external_url)
            if tags:
                title = ' '.join(tags) + ' '
        self.render("bookmarklet/index.html", 
                    external_url=external_url, 
                    title=title,
                    error_title=None)

    def _suggest_tags(self, user, external_url):
        """given a user and a title (e.g. 'Tra the la [Foo]') return a list of
        tags that are in that string. Disregard English stopwords."""
        def wrap_tags(tags):
            return ['@%s' % x for x in tags]
        
        # look at the last event with the same URL and copy the tags used in
        # that event
        search = {'user.$id': user._id,
                  'external_url': external_url
                  }
        for event in self.db[Event.__collection__].find(search):
            return wrap_tags(event['tags'])
        
        # nothing found, try limiting the search
        parsed_url = urlparse(external_url)
        search_url = parsed_url.scheme + '://' + parsed_url.netloc 
        search['external_url'] = re.compile(re.escape(search_url), re.I)
        for event in self.db[Event.__collection__].find(search):
            return wrap_tags(event['tags'])
        
        return wrap_tags([])
    
    def post(self):
        title = self.get_argument("title", u'').strip()
        external_url = self.get_argument("external_url", u'')
        description = self.get_argument("description", None)
        use_current_url = niceboolean(self.get_argument("use_current_url", False))
        if not use_current_url:
            external_url = u''
            
        if not title and description and description.strip():
            description = description.strip()
            if len(description.splitlines()) > 1:
                title = description.splitlines()[0]
                description = description.splitlines()[1:]
                description = '\n'.join(description)
                description = description.strip()
            else:
                if len(description) > 50:
                    title = description[:50] + '...'
                else:
                    title = description
                    description = u''
                
        if not self.get_argument('now', None):
            return self.write("'now' not sent. Javascript must be enabled")
                
        start = parse_datetime(self.get_argument('now'))
        end = None
        
        length = self.get_argument('length', 'all_day')
        try:
            length = float(length)
            all_day = False
            end = start + datetime.timedelta(hours=length)
        except ValueError:
            # then it's an all_day
            all_day = True
        
        if title:
            user = self.get_current_user()
        
            if not user:
                user = self.db.User()
                user.save()
                
            event, created = self.create_event(user,
              title=title,
              description=description,
              external_url=external_url,
              all_day=all_day,
              start=start,
              end=end,
            )
            
            if created:
                log_event(self.db, user, event,
                          actions.ACTION_ADD, contexts.CONTEXT_BOOKMARKLET)
            
            if not self.get_secure_cookie('user'):
                # if you're not logged in, set a cookie for the user so that
                # this person can save the events without having a proper user
                # account.
                self.set_secure_cookie("guid", str(user.guid), expires_days=14)
            
            self.render("bookmarklet/posted.html")
        else:
            self.render("bookmarklet/index.html", 
                    external_url=external_url,
                    title=title,
                    error_title="No title entered")
                    
                    
                    
        
@route(r'/report/$')
class ReportHandler(BaseHandler):
    
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        if not user:
            return self.write("Error. You need to be logged in to get the report")
        
        search = {'user.$id': user._id}
        try:
            first_event = self.db[Event.__collection__].find(search).sort('start', 1).limit(1)[0]
            last_event = self.db[Event.__collection__].find(search).sort('start', -1).limit(1)[0]
        except IndexError:
            return self.write("Error. Sorry, can't use this until you have some events entered")
        
        options['first_date'] = first_event['start']
        options['last_date'] = last_event['start']
        
        self.render("report/index.html", **options)

@route(r'/report/export(\.xls|\.csv)$')
class ExportHandler(ReportHandler):
    
    @tornado.web.asynchronous
    def get(self, format):
        out = StringIO()
        if format == '.xls':
            self.set_header("Content-Type", "application/vnd.ms-excel; charset=UTF-8")
            from export.excel_export import export_events
            export_events(self.get_events(), out, user=self.get_current_user())
        elif format == '.csv':
            self.set_header("Content-Type", "application/msexcel-comma; charset=UTF-8")
            from export.csv_export import export_events
            export_events(self.get_events(), out, user=self.get_current_user())
        self.write(out.getvalue())
        self.finish()
        
    def get_events(self):
        user = self.get_current_user()
        start = parse_datetime(self.get_argument('start'))
        end = parse_datetime(self.get_argument('end'))
        search = {}
        search['start'] = {'$gte': start}
        search['end'] = {'$lte': end}
        search['user.$id'] = user['_id']
        
        return self.db[Event.__collection__].find(search).sort('start')
        
        
@route(r'/report(\.xls|\.json|\.js|\.xml|\.txt)?')
class ReportDataHandler(EventStatsHandler):
    def get(self, format=None):
        user = self.get_current_user()
        if self.get_argument('interval', None):
            stats = self.get_lumped_stats_data(
              self.get_argument('interval'))
        else:
            stats = self.get_stats_data()
        
        if format == '.xls':
            raise NotImplementedError
        elif format in ('.json', '.js'):
            self.write_json(stats, javascript=format=='.js')
        elif format == '.xml':
            self.write_xml(stats)
        elif format == '.txt':
            out = StringIO()
            for key, values in stats.items():
                out.write('%s:\n' % key.upper().replace('_', ' '))
                
                for tag, num in values:
                    tag = re.sub('</?em>', '*', tag)
                    out.write('  %s%s\n' % (tag.ljust(40), num))
                out.write('\n')
                
            self.write_txt(out.getvalue())
            
    def get_lumped_stats_data(self, interval):
        """
        return a dict with two keys:
          * data
          * tags
        Each is a list. tags[0] might be 'Project X' and data[0] is the its data.
        The data is of tuples like this: (date, count)
        """
        user = self.get_current_user()
        if not user:
            raise tornado.web.HTTPError(400, "no user")
        search = {}
        search['user.$id'] = user._id
        search['all_day'] = niceboolean(self.get_argument('all_day', False))
        
        #if self.get_argument('start', None):
        start = parse_datetime(self.get_argument('start'))
        start = datetime.datetime(start.year, start.month, start.day, 0,0,0)
        search['start'] = {'$gte': start}
        #if self.get_argument('end', None):
        end = parse_datetime(self.get_argument('end'))
        search['end'] = {'$lte': end}
            
        last_date = end
        tags = {}
        date = start#first_date
        for entry in self.db[Event.__collection__].find(search):
            for tag in entry['tags']:
                if tag not in tags:
                    tags[tag] = []
                    
        tags[''] = []
        if 'start' in search:
            search.pop('start')
        if 'end' in search:
            search.pop('end')
            
        if interval == '1 week':
            interval = datetime.timedelta(days=7)
        else:
            raise NotImplementedError(interval)
        ticks = []
        tick = 1
        while date < last_date:
            this_search = dict(search, 
                               start={'$gte':date}, 
                               end={'$lt': date + interval})
            _found = defaultdict(float)
            for entry in self.db[Event.__collection__].find(this_search):
                if search['all_day']:
                    d = (entry['end'] - entry['start']).days + 1
                else:
                    d = (entry['end'] - entry['start']).seconds / 3600.0
                
                these_tags = entry['tags'] and entry['tags'] or ['']
                
                for tag in these_tags:
                    _found[tag] += d
            
            for t in tags.keys():
                tags[t].append(_found.get(t, 0))
                    
            date += interval
            ticks.append(tick)
            tick += 1
                
        all_tags = []
        all_data = []
        if '' in tags:
            tags['<em>Untagged</em>'] = tags.pop('')
        for key in tags:
            all_tags.append(key)
            all_data.append(tags[key])
        
        return dict(data=all_data, tags=all_tags, ticks=ticks)
    
    
@route('/stats/$')
class GeneralStatisticsHandler(BaseHandler): # pragma: no cover
    
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()

        first_event = self.db[Event.__collection__].find().sort('add_date', 1).limit(1)[0]
        #last_event = self.db[Event.__collection__].find().sort('add_date', -1).limit(1)[0]
        
        options['first_date'] = first_event['start']
        #options['last_date'] = last_event['start']
        today = datetime.datetime.today()
        options['last_date'] = today
        
        self.render("stats/index.html", **options)

@route('/stats/([\w-]+)\.json$')
class StatisticsDataHandler(BaseHandler): # pragma: no cover
    
    def get(self, report_name):
        
        data = dict()
        search = dict()
        
        start = parse_datetime(self.get_argument('start'))
        start = datetime.datetime(start.year, start.month, start.day, 0,0,0)
        #search['start'] = {'$gte': start}
        end = parse_datetime(self.get_argument('end'))
        end = datetime.datetime(end.year, end.month, end.day, 0,0,0)
        #search['end'] = {'$lte': end}

        interval = None
        if self.get_argument('interval', None):
            interval = self.get_argument('interval')
            
        #cumulative = None
        #if self.get_argument('cumulative', None):
        #    cumulative = self.get_argument('cumulative')            

        if not interval:
            interval = '1 month'
        if interval == '1 week':
            interval = datetime.timedelta(days=7)
        elif interval == '1 month':
            from dateutil.relativedelta import relativedelta
            interval = relativedelta(months=1)
        elif interval == '1 day':
            interval = datetime.timedelta(days=1)
        else:
            raise NotImplementedError(interval)
            
        if report_name =='users':#in ('cum-users', 'new-users'):
            
            cum_w_email = []
            new_w_email = []
            cum_wo_email = []
            new_wo_email = []
            
            date = start
            cum_w_email_count = cum_wo_email_count = 0
            while date < end:
                this_search = dict(add_date={'$gte':date, '$lt':date + interval})
                date_serialized = date.strftime('%Y-%m-%d')#mktime(date.timetuple())
                this_count = self.db[User.__collection__]\
                  .find(dict(this_search, email={'$ne':None})).count()
                
                new_w_email.append((date_serialized, this_count))
                cum_w_email.append((date_serialized, this_count + cum_w_email_count))
                cum_w_email_count += this_count

                this_count = self.db[User.__collection__]\
                  .find(dict(this_search, email=None)).count()
                  
                new_wo_email.append((date_serialized, this_count))
                cum_wo_email.append((date_serialized, this_count + cum_wo_email_count))
                cum_wo_email_count += this_count
                
                date += interval
                
            data = dict(cum_w_email=cum_w_email,
                        new_w_email=new_w_email,
                        cum_wo_email=cum_wo_email,
                        new_wo_email=new_wo_email,
                        )
        elif report_name == 'events':
            
            cum = []
            new = []
            
            date = start
            cum_count = 0
            while date < end:
                this_search = dict(add_date={'$gte':date, '$lt':date + interval})
                date_serialized = date.strftime('%Y-%m-%d')#mktime(date.timetuple())
                this_count = self.db[Event.__collection__]\
                  .find(this_search).count()
                
                new.append((date_serialized, this_count))
                cum.append((date_serialized, this_count + cum_count))
                cum_count += this_count

                date += interval
                
            data = dict(cum=cum,
                        new=new,
                        )
                    
        elif report_name == 'numbers':
            # misc numbers
            numbers = self._get_numbers(start, end)
            data['numbers'] = numbers
                    
        elif report_name == 'usersettings':
            #data['lines'] = list()
            trues = list()
            falses = list()
            data['labels'] = list()
            
            counts = {}
            _translations = {
              'hash_tags': "Tag with #",
              'ampm_format': "AM/PM format",
            }
            total_count = self.db[UserSettings.__collection__].find().count()
            for key in UserSettings.get_bool_keys():
                if key in ('offline_mode'):
                    # skip these
                    continue
                count_true = self.db[UserSettings.__collection__].find({key:True}).count()
                #count_false = self.db[UserSettings.__collection__].find({key:False}).count()
                p = int(100. * count_true / total_count)
                try:
                    label = _translations[key]
                except KeyError:
                    label = key.replace('_',' ').capitalize()
                data['labels'].append(label)
                trues.append(p)
                falses.append(100 - p)
            
            data['lines'] = [trues, falses]
            
        else:
            raise tornado.web.HTTPError(404, report_name)
        
        self.write_json(data)
        
    def _get_numbers(self, start, end):
        data = list()
        
        # No. users
        _search = {'add_date': {'$gte':start, '$lt':end}}
        c = self.db[User.__collection__].find(_search).count()
        #data.append(dict(number=c,
        #                 label=u"sers"))
                         
        # No. users without email address
        wo_search = dict(_search, email=None)
        c2 = self.db[User.__collection__].find(wo_search).count()
        data.append(dict(number=c-c2,
                         label=u"Users with email address"))
        data.append(dict(number=c2,
                         label=u"Users without email address"))
                         
        c = self.db[Event.__collection__].find(_search).count()
        data.append(dict(number=c,
                         label=u"Events"))
        diff = end - start
        days = diff.days
        
        data.append(dict(number='%.1f' % (c/float(days)),
                         label=u"Events per day"))
        if days > 28:
            weeks = days / 7
            data.append(dict(number='%.1f' % (c/float(weeks)),
                             label=u"Events per week"))
        if days > 90:
            months = days/ 30
            data.append(dict(number='%.1f' % (c/float(months)),
                             label=u"Events per month"))
                             
        data.append(dict(number=self.db.EmailReminder.find(_search).count(),
                         label=u"Email reminders set up"))

        return data
        
    
@route('/features/$')
class FeatureRequestsHandler(BaseHandler):
    
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        
        if self.get_secure_cookie('user'):
            options['can_add'] = True
        else:
            options['can_add'] = False
        
        options['feature_requests'] = \
          self.db.FeatureRequest.find().sort('vote_weight', -1).limit(20)
          
        # Compile a list of the features this user already has voted on
        options['have_voted_features'] = []
        if user:
            _search = {'user.$id': user._id}
            for feature_request_comment in \
              self.db[FeatureRequestComment.__collection__].find(_search):
                options['have_voted_features'].append(
                  'feature--%s' % feature_request_comment['feature_request'].id
                )
          
        return self.render("featurerequests/index.html", **options)
    
    def find_feature_requests(self, title):
        return self.db.FeatureRequest.find({'title':re.compile(re.escape(title), re.I)})
    
    def get_user_voting_weight(self, user):
        no_events = self.db[Event.__collection__].find({'user.$id': user._id}).count()
        if no_events > 100:
            voting_weight = 5
        elif no_events > 50:
            voting_weight = 3
        elif no_events > 10:
            voting_weight = 2
        else:
            voting_weight = 1
        
        if user.first_name and user.last_name:
            # boost for nice friends
            voting_weight *= 1.5
            
        # XXX could perhaps give another boost to people who have many events
        # over a long period of time
        
        if user.premium:
            # extra privilege
            voting_weight *= 2
            
        return int(voting_weight)

    def post(self):
        title = self.get_argument('title').strip()
        if title == 'Add your own new feature request':
            # placeholder text
            title = None
            
        description = self.get_argument('description', u'').strip()
        if description == u'Longer description (optional)':
            # placeholder text
            description = u''
            
        if not title:
            raise tornado.web.HTTPError(400, "Missing title")
        
        if list(self.find_feature_requests(title)):
            raise tornado.web.HTTPError(400, "Duplicate title")
        
        user = self.get_current_user()
        if not user:
            raise tornado.web.HTTPError(403, "Not logged in")
        
        feature_request = self.db.FeatureRequest()
        feature_request.author = user
        feature_request.title = title
        if description:
            feature_request.description = description
            feature_request.description_format = u'plaintext'
        
        # figure out what voting weight the logged in user has
        voting_weight = self.get_user_voting_weight(user)
        
        # to start with the feature request gets as much voting weight
        # as the first comment
        feature_request.vote_weight = voting_weight
        feature_request.save()
        
        feature_request_comment = self.db.FeatureRequestComment()
        feature_request_comment.feature_request = feature_request
        feature_request_comment.user = user
        feature_request_comment.comment = u''
        feature_request_comment.vote_weight = voting_weight
        feature_request_comment.save()
        
        self.redirect('/features/#added-%s' % feature_request._id)

@route('/features/feature\.(html|json)$')
class FeatureRequestHandler(BaseHandler):
    
    
    def get(self, format):
        feature_request = self.get_feature(self.get_argument('id'))
        if format == 'html':
            from ui_modules import ShowFeatureRequest
            m = ShowFeatureRequest(self)
            self.write(m.render(feature_request))
        else:
            raise NotImplementedError
        
    
    def get_feature(self, _id):
        try:
            return self.db.FeatureRequest.one({'_id': ObjectId(_id)})
        except InvalidId:
            raise tornado.web.HTTPError(404, "Invalid ID")
        if not feature_request:
            raise tornado.web.HTTPError(404, "Not found ID")
        
        
        
@route('/features/vote/(up|down)/$')
class VoteUpFeatureRequestHandler(FeatureRequestsHandler, FeatureRequestHandler):
    
    def post(self, direction):
        assert direction in ('up','down'), direction
        _id = self.get_argument('id')
        # because DOM IDs can't start with numbers I've prefixed them in HTML
        _id = _id.replace('feature--','')
        comment = self.get_argument('comment', u'').strip()
        
        feature_request = self.get_feature(_id)
        
        user = self.get_current_user()
        if not user:
            return self.write_json(dict(error="Error. Not logged in or user with saved events"))
        voting_weight = self.get_user_voting_weight(user)
        
        # remove any previous comments
        _search = {'feature_request.$id': feature_request._id,
                   'user.$id': user._id}
        if self.db.FeatureRequestComment.one(_search):
            # this applies indepdent of direction
            feature_request.vote_weight -= voting_weight
            feature_request.save()
            
        for each in self.db.FeatureRequestComment.find(_search):
            each.delete()
        
        if direction == 'up':
            fr_comment = self.db.FeatureRequestComment()
            fr_comment.comment = comment
            fr_comment.user = user
            fr_comment.feature_request = feature_request
            fr_comment.vote_weight = voting_weight
            fr_comment.save()
            
            feature_request.vote_weight += voting_weight
            feature_request.save()
            
        # now return some stats about all feature request
        vote_weights = self.get_all_feature_request_vote_weights()
        
        self.write_json(dict(id=str(feature_request._id),
          vote_weights=\
          [{'id':'feature--%s' % k, 'weight':v} for (k,v) in vote_weights.items()]
        ))
    
    def get_all_feature_request_vote_weights(self):
        data = dict()
        for feature_request in self.db[FeatureRequest.__collection__].find():
            data[str(feature_request['_id'])] = feature_request['vote_weight']
        return data
        
        
@route('/features/find.json$')
class FindFeatureRequestsHandler(FeatureRequestsHandler):
    
    def get(self):
        title = self.get_argument('title').strip()
        data = dict(feature_requests=list())
        for feature_request in self.find_feature_requests(title):
            data['feature_requests'].append(dict(title=feature_request.title,
                                                 description=feature_request.description))
        self.write_json(data)
        
