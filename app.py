#!/usr/bin/env python
#
from pprint import pprint
from collections import defaultdict
from pymongo.objectid import InvalidId, ObjectId
from time import mktime, sleep
import cStringIO
import datetime
import os.path
import re
from mongokit import Connection
import tornado.auth
import tornado.database
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata

from tornado.options import define, options

from models import Event, User, UserSettings, Share
from utils import parse_datetime, encrypt_password

define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=8000, help="run on the given port", type=int)
define("database_name", default="worklog", help="mongodb database name")
define("prefork", default=False, help="pre-fork across all CPUs", type=bool)
#define("mysql_host", default="127.0.0.1:3306", help="blog database host")
#define("mysql_database", default="blog", help="blog database name")
#define("mysql_user", default="blog", help="blog database user")
#define("mysql_password", default="blog", help="blog database password")


class Application(tornado.web.Application):
    def __init__(self, database_name=None, xsrf_cookies=True):
        handlers = [
            (r"/", HomeHandler),
            (r"/events/stats(\.json|\.xml|\.txt)?", EventStatsHandler),
            (r"/events(\.json|\.js|\.xml|\.txt)?", EventsHandler),
            (r"/event/(edit|resize|move)", EventHandler),
            (r"/user/settings(.js|/)", UserSettingsHandler),
            (r"/user/account/", AccountHandler),
            (r"/share/$", SharingHandler),
            (r"/user/signup/", SignupHandler),
            #(r"/archive", ArchiveHandler),
            #(r"/feed", FeedHandler),
            #(r"/entry/([^/]+)", EntryHandler),
            #(r"/compose", ComposeHandler),
            (r"/auth/login/", AuthLoginHandler),
            (r"/auth/logout/", AuthLogoutHandler),
            (r"/help/(\w*)", HelpHandler),
        ]
        settings = dict(
            title=u"Donecal",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules={"Settings": SettingsModule},
            xsrf_cookies=xsrf_cookies,
            cookie_secret="11oETzKsXQAGaYdkL5gmGeJJFuYh7EQnp2XdTP1o/Vo=",
            login_url="/auth/login",
            debug=options.debug,
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        
        #print database_name and database_name or options.database_name
        # Have one global connection to the blog DB across all handlers
        self.database_name = database_name and database_name or options.database_name
        self.con = Connection()
        self.con.register([Event, User, UserSettings, Share])
        #self.db = Connection()
        
        #self.db = tornado.database.Connection(
        #    host=options.mysql_host, database=options.mysql_database,
        #    user=options.mysql_user, password=options.mysql_password)


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
        raise NotImplementedError
    
    def write_txt(self, str_):
        self.set_header("Content-Type", "text/plain; charset=UTF-8") # doesn;t seem to work
        self.write(str_)
        
        
    def transform_fullcalendar_event(self, obj, serialize=False, **kwargs):
        data = dict(title=obj.title, 
                    start=obj.start,
                    end=obj.end,
                    allDay=obj.all_day,
                    id=str(obj._id))
            
        data.update(**kwargs)
            
        if serialize:
            for key, value in data.items():
                if isinstance(value, (datetime.datetime, datetime.date)):
                    #time_tuple = (2008, 11, 12, 13, 59, 27, 2, 317, 0)
                    timestamp = mktime(value.timetuple())
                    data[key] = timestamp
            
        return data
    
    def case_correct_tags(self, tags, user):
        # XXX: work on this
        pass
        #for tag in tags:
        #    for event in self.db.
        
        
    def find_user(self, email):
        return self.db.users.User.one(dict(email=\
         re.compile(re.escape(email), re.I)))
         
    def has_user(self, email):
        return bool(self.find_user(email))
    
    def get_base_options(self):
        options = {}
        # default settings
        settings = dict(hide_weekend=False,
                        monday_first=False)

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
                
        options['user'] = user
        options['user_name'] = user_name
        options['settings'] = settings
        
        
        return options

        
    

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
            self.redirect('/')

        # default settings
        options = self.get_base_options()
        
        user = options['user']
        
        if user:
                
            
            hidden_shares = self.get_secure_cookie('hidden_shares')
            if not hidden_shares: 
                hidden_shares = ''
            hidden_keys = [x for x in hidden_shares.split(',') if x]
            hidden_shares = []
            for share in self.db.shares.Share.find({'key':{'$in':hidden_keys}}):
                className = 'share-%s' % share.user._id
                hidden_shares.append(dict(key=share.key,
                                          className=className))

            options['settings']['hidden_shares'] = hidden_shares
        
        self.render("calendar.html", 
          #
          **options
        )

        
class SettingsModule(tornado.web.UIModule):
    def render(self, settings):
        return self.render_string("modules/settings.html",
           settings_json=tornado.escape.json_encode(settings),
         )

class EventsHandler(BaseHandler):

    
    def get(self, format=None):
        user = self.get_current_user()
        events = []
        sharers = []
        tags = set()

        start = parse_datetime(self.get_argument('start'))
        end = parse_datetime(self.get_argument('end'))
        search = {}
        search['start'] = {'$gte': start}
        search['start'] = {'$lte': end}

        if user:
            search['user.$id'] = user._id
            for event in self.db.events.Event.find(search):
                events.append(self.transform_fullcalendar_event(event, True))
                tags.update(event['tags'])
                
        shares = self.get_secure_cookie('shares')
        if not shares: 
            shares = ''
        for key in [x for x in shares.split(',') if x]:
            for share in self.db.shares.Share.find(dict(key=key)):
                search['user.$id'] = share.user._id
                className = 'share-%s' % share.user._id
                full_name = u"%s %s" % (share.user.first_name, share.user.last_name)
                full_name = full_name.strip()
                if not full_name:
                    full_name = share.user.email
                sharers.append(dict(className=className,
                                    full_name=full_name,
                                    key=share.key))
                                    
                for event in self.db.events.Event.find(search):
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
            
        if format in ('.json', '.js'):
            self.write_json(data, javascript=format=='.js')
        elif format == '.xml':
            self.write_json(data)
        elif format == '.txt':
            out = cStringIO.StringIO()
            out.write('ENTRIES\n')
            for event in events:
                pprint(event, out)
                out.write("\n")
            out.write('TAGS\n')
            out.write('\n'.join(tags))
            out.write("\n")
            self.write_txt(out.getvalue())
        
    def post(self, *args, **kwargs):
        title = self.get_argument("title")
        date = self.get_argument("date")
        date = parse_datetime(date)
        
        all_day = bool(self.get_argument("all_day", False))
        
        tags = list(set([x[1:] for x in re.findall('@\w+', title)]))
        
        
        user = self.get_current_user()
        if user:
            self.case_correct_tags(tags, user)
        else:
            user = self.db.users.User()
            user.save()
            
        event = self.db.events.Event()
        event.user = self.db.users.User(user)
        event.title = title
        event.tags = tags
        event.all_day = all_day
        event.start = date
        event.end = date
        event.save()
        
        self.set_secure_cookie("guid", str(user.guid), expires_days=14)
        
        fullcalendar_event = self.transform_fullcalendar_event(event, serialize=True)
        
        self.set_header("Content-Type", "application/json")
        self.write(tornado.escape.json_encode(
          dict(event=fullcalendar_event,
               tags=['@%s' % x for x in tags],
           )))
        
        
class EventHandler(BaseHandler):
    
    def post(self, action):
        _id = self.get_argument('id')
        
        if action in ('move', 'resize'):
            days = int(self.get_argument('days'))
            minutes = int(self.get_argument('minutes'))
        else:
            assert action == 'edit'
            title = self.get_argument('title')
        
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
            event.end += datetime.timedelta(days=days, minutes=minutes)
            event.save()
        elif action == 'move':
            event.start += datetime.timedelta(days=days, minutes=minutes)
            event.end += datetime.timedelta(days=days, minutes=minutes)
            event.save()
        elif action == 'edit':
            tags = list(set([x[1:] for x in re.findall('@\w+', title)]))
            event.title = title
            event.tags = tags
            event.save()
        else:
            raise NotImplementedError
        
        return self.write_json(dict(event=self.transform_fullcalendar_event(event, True)))
    
    def get(self, action):
        assert action == 'edit'
        
        _id = self.get_argument('id')
       
        user = self.get_current_user()
        if not user:
            return self.write(dict(error="Not logged in (no cookie)"))
        
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
        
        self.render('event/edit.html', event=event)
    
            
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
                
            for entry in self.db.events.Event.find(search):
                if entry.all_day:
                    days = 1 + (entry.end - entry.start).days
                    if entry.tags:
                        for tag in entry.tags:
                            days_spent[tag] += days
                    else:
                        days_spent[u''] += days
                    
                else:
                    hours = (entry.end - entry.start).seconds / 60.0 / 60
                    if entry.tags:
                        for tag in entry.tags:
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
        #pprint(stats)
                
        if format == '.json':
            self.write_json(stats)
        elif format == '.xml':
            self.write_xml(stats)
        elif format == '.txt':
            raise NotImplementedError
            #self.write_txt(
        

class UserSettingsHandler(BaseHandler):
    def get(self, format=None):
        # default initials
        hide_weekend = False
        monday_first = False
        
        user = self.get_current_user()
        if user:
            user_settings = self.get_current_user_settings(user)
            if user_settings:
                hide_weekend = user_settings.hide_weekend
                monday_first = user_settings.monday_first
            else:
                user_settings = self.db.user_settings.UserSettings()
                user_settings.user = user
                user_settings.save()

        if format == '.js':
            data = dict(hide_weekend=hide_weekend,
                        monday_first=monday_first)
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
        else:
            user_settings = self.db.user_settings.UserSettings()
            user_settings.user = user
            user_settings.save()
                
        user_settings['monday_first'] = bool(self.get_argument('monday_first', None))
        user_settings['hide_weekend'] = bool(self.get_argument('hide_weekend', None))
        user_settings.save()
        self.redirect("/")
        #self.render("user/settings-saved.html")
        
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

        
class AccountHandler(BaseHandler):
    def get(self):
        self.render("user/account.html")
        
        

class SignupHandler(BaseHandler):
    
          
    def get(self):
        
        if self.get_argument('validate_email', None):
            # some delay to make brute-force testing boring
            sleep(0.5)
            
            email = self.get_argument('validate_email').strip()
            if self.has_user(email):
                result = dict(error='taken')
            else:
                result = dict(ok=True)
            self.write_json(result)
            
    def post(self):
        email = self.get_argument('email')
        password = self.get_argument('password')
        first_name = self.get_argument('first_name', u'')
        last_name = self.get_argument('last_name', u'')
        
        if not email:
            return self.write("Error. No email provided")
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


class ComposeHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument("id", None)
        entry = None
        if id:
            entry = self.db.get("SELECT * FROM entries WHERE id = %s", int(id))
        self.render("compose.html", entry=entry)

    @tornado.web.authenticated
    def post(self):
        id = self.get_argument("id", None)
        title = self.get_argument("title")
        text = self.get_argument("markdown")
        html = markdown.markdown(text)
        if id:
            entry = self.db.get("SELECT * FROM entries WHERE id = %s", int(id))
            if not entry: raise tornado.web.HTTPError(404)
            slug = entry.slug
            self.db.execute(
                "UPDATE entries SET title = %s, markdown = %s, html = %s "
                "WHERE id = %s", title, text, html, int(id))
        else:
            slug = unicodedata.normalize("NFKD", title).encode(
                "ascii", "ignore")
            slug = re.sub(r"[^\w]+", " ", slug)
            slug = "-".join(slug.lower().strip().split())
            if not slug: slug = "entry"
            while True:
                e = self.db.get("SELECT * FROM entries WHERE slug = %s", slug)
                if not e: break
                slug += "-2"
            self.db.execute(
                "INSERT INTO entries (author_id,title,slug,markdown,html,"
                "published) VALUES (%s,%s,%s,%s,%s,UTC_TIMESTAMP())",
                self.current_user.id, title, slug, text, html)
        self.redirect("/entry/" + slug)


class AuthLoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()
    
    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")
        author = self.db.get("SELECT * FROM authors WHERE email = %s",
                             user["email"])
        if not author:
            # Auto-create first author
            any_author = self.db.get("SELECT * FROM authors LIMIT 1")
            if not any_author:
                author_id = self.db.execute(
                    "INSERT INTO authors (email,name) VALUES (%s,%s)",
                    user["email"], user["name"])
            else:
                self.redirect("/")
                return
        else:
            author_id = author["id"]
        self.set_secure_cookie("user", str(author_id))
        self.redirect(self.get_argument("next", "/"))
        
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
        

class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.clear_cookie("shares")
        self.clear_cookie("guid")
        self.clear_cookie("hidden_shares")
        self.redirect(self.get_argument("next", "/"))


class HelpHandler(BaseHandler):
    
    def get(self, page):
        options = self.get_base_options()
        self.application.settings['template_path']
        if page == '':
            page = 'index'
        filename = "help/%s.html" % page.lower()
        if os.path.isfile(os.path.join(self.application.settings['template_path'],
                                       filename)):
            return self.render(filename, **options)
        raise tornado.web.HTTPError(404, "Unknown page")


def main():
    tornado.options.parse_command_line()
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
