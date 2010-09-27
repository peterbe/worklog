#!/usr/bin/env python
#
from pymongo.objectid import InvalidId, ObjectId
#from mongokit import DBRef
from pprint import pprint
from time import mktime
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

from models import Event, User
from utils import parse_datetime

define("port", default=8000, help="run on the given port", type=int)
define("database_name", default="worklog", help="mongodb database name")
#define("mysql_host", default="127.0.0.1:3306", help="blog database host")
#define("mysql_database", default="blog", help="blog database name")
#define("mysql_user", default="blog", help="blog database user")
#define("mysql_password", default="blog", help="blog database password")


class Application(tornado.web.Application):
    def __init__(self, database_name=None):
        handlers = [
            (r"/", HomeHandler),
            (r"/events/tags(\.json|\.xml|\.txt)?", EventTagsHandler),
            (r"/events/stats(\.json|\.xml|\.txt)?", EventStatsHandler),
            (r"/events(\.json|\.xml|\.txt)?", EventsHandler),
            (r"/event/(edit|resize|move)", EventHandler),
            #(r"/archive", ArchiveHandler),
            #(r"/feed", FeedHandler),
            #(r"/entry/([^/]+)", EntryHandler),
            #(r"/compose", ComposeHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
        ]
        settings = dict(
            title=u"Worklog",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            #ui_modules={"Entry": EntryModule},
            xsrf_cookies=True,
            cookie_secret="11oETzKsXQAGaYdkL5gmGeJJFuYh7EQnp2XdTP1o/Vo=",
            login_url="/auth/login",
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        
        #print database_name and database_name or options.database_name
        # Have one global connection to the blog DB across all handlers
        self.database_name = options.database_name
        self.con = Connection()
        self.con.register([Event, User])
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
        if not guid: return None
        return self.db.users.User.one({'guid': guid})
    
    def write_json(self, struct):
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        self.write(tornado.escape.json_encode(struct))
        
    def write_xml(self, struct):
        raise NotImplementedError
    
    def write_txt(self, str_):
        self.set_header("Content-Type", "text/plain; charset=UTF-8") # doesn;t seem to work
        self.write(str_)
        
        
        
    

class HomeHandler(BaseHandler):
    def get(self):
        self.render("calendar.html")


class EventsHandler(BaseHandler):

    def _transform_fullcalendar_event(self, obj, serialize=False):
        data = dict(title=obj.title, 
                    start=obj.start,
                    end=obj.end,
                    allDay=obj.all_day,
                    id=str(obj._id))
            
        if serialize:
            for key, value in data.items():
                if isinstance(value, (datetime.datetime, datetime.date)):
                    #time_tuple = (2008, 11, 12, 13, 59, 27, 2, 317, 0)
                    timestamp = mktime(value.timetuple())
                    data[key] = timestamp
            
        return data
        
        
    def get(self, format=None):
        user = self.get_current_user()
        entries = []
        if user:
            search = {'user.$id': user._id}
            start = parse_datetime(self.get_argument('start'))
            end = parse_datetime(self.get_argument('end'))
            search['start'] = {'$gte': start}
            search['start'] = {'$lte': end}
            
            for entry in self.db.events.Event.find(search):
                entries.append(self._transform_fullcalendar_event(entry, True))
            
        if format == '.json':
            self.write_json(entries)
        elif format == '.xml':
            self.write_json(dict(entries=entries))
        elif format == '.txt':
            out = cStringIO.StringIO()
            for entry in entries:
                pprint(entry, out)
                out.write("\n")
            self.write_txt(out.getvalue())
        
    def post(self, *args, **kwargs):
        title = self.get_argument("title")
        date = self.get_argument("date")
        date = parse_datetime(date)
        
        all_day = bool(self.get_argument("all_day", False))
        
        tags = list(set([x[1:] for x in re.findall('@\w+', title)]))
        
        user = self.get_current_user()
        if not user:
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
        
        self.set_secure_cookie("guid", str(user.guid), expires_days=100)
        
        fullcalendar_event = self._transform_fullcalendar_event(event, serialize=True)
        
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
        
        return self.write("thanks")
    
class EventTagsHandler(BaseHandler):
    def get(self, format):
        tags = set()
        user = self.get_current_user()
        if user:
            search = {'user.$id': user._id}
            # XXX: can search smarter
            for entry in self.db.events.find(search):
                tags.update(entry['tags'])
                
        tags = list(tags)
        tags.sort(lambda x, y: cmp(x.lower(), y.lower()))
        
        tags = ['@%s' % x for x in tags]
        
        if format == '.json':
            self.write_json(dict(tags=tags))
        elif format == '.xml':
            self.write_xml(dict(tags=tags))
        elif format == '.txt':
            self.write_txt('\n'.join(tags))
            
            
class EventStatsHandler(BaseHandler):
    def get(self, format):
        time_spent = {}
        user = self.get_current_user()
        if user:
            search = {'user.$id': user._id}
            # XXX: can search smarter
            for entry in self.db.events.find(search):
                tags.update(entry['tags'])
                
        if format == '.json':
            self.write_json(dict(time_spent=time_spent))
        elif format == '.xml':
            self.write_xml(dict(time_spent=time_spent))
        elif format == '.txt':
            raise NotImplementedError
            #self.write_txt(
        


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


class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", "/"))


class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    # Re-read and consider pre-forking
    # http://groups.google.com/group/python-tornado/browse_thread/thread/357e6637f881e9f0
    try:
        print "Starting tornado on port", options.port
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
