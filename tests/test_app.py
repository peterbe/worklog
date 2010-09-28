import datetime
from mongokit import Connection
import simplejson as json
from tornado.testing import LogTrapTestCase, AsyncHTTPTestCase
from tornado.web import RequestHandler, _O

import app
from models import Event, User

class CookieTestRequestHandler(RequestHandler):
    # stub out enough methods to make the secure_cookie functions work
    def __init__(self):
        # don't call super.__init__
        self._cookies = {}
        self.application = _O(settings=dict(cookie_secret='0123456789'))

    def get_cookie(self, name):
        return self._cookies.get(name)

    def set_cookie(self, name, value, expires_days=None):
        self._cookies[name] = value


class ApplicationTest(AsyncHTTPTestCase, LogTrapTestCase):
    
    _registered = False
    
    def setUp(self):
        super(ApplicationTest, self).setUp()
        return
        con = Connection()
        con.register([Event, User])
        if not self._registered:
            print "in _registered"
            self._registered = True
        print "set up"
        
    def get_db(self):
        return self._app.con[self._app.database_name]
    
    def get_app(self):
        return app.Application(database_name='test') # consider passing a different database name
    
    def test_homepage(self):
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()
        self.assertTrue('id="calendar"' in response.body)
        
    def test_events(self):
        self.http_client.fetch(self.get_url('/events.json'), self.stop)
        response = self.wait()
        self.assertTrue('text/javascript' in response.headers['Content-Type'])
        struct = json.loads(response.body)
        self.assertEqual(struct, [])
        
    def test_events_stats(self):
        # first load some events
        db = self.get_db()
        user = db.users.User()
        assert user.guid
        
        event1 = db.events.Event()
        event1.user = user
        event1.title = u"Title1"
        event1.start = datetime.datetime(2010, 10, 1)
        event1.end = datetime.datetime(2010, 10, 1)
        event1.all_day = True
        event1.save()
        
        XXX unfinihsed
        