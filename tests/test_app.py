import re
import datetime
from urllib import urlencode
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
    
    
    _once = False
    def setUp(self):
        super(ApplicationTest, self).setUp()
        if not self._once:
            self._once = True
            self._emptyCollections()
        
    def _emptyCollections(self):
        db = self.get_db()
        [db.drop_collection(x) for x 
         in db.collection_names() 
         if x not in ('system.indexes',)]
        
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
        self.assertTrue('application/json' in response.headers['Content-Type'])
        struct = json.loads(response.body)
        self.assertEqual(struct, dict(events=[], tags=[]))
        
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
        
        
    def test_set_user_settings(self):
        db = self.get_db()
        assert not db.users.User.find().count()
        
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()
        
        # rendering won't automatically create a user
        self.assertFalse(db.users.User.find().count())
        
        # rendering the user settings form won't either
        self.http_client.fetch(self.get_url('/user/settings/'), self.stop)
        response = self.wait()
        self.assertEqual(response.code, 200)
        self.assertFalse(db.users.User.find().count())
        xsrf_regex = re.compile('name="_xsrf" value="(\w+)"')
        xsrf = xsrf_regex.findall(response.body)[0]
        print repr(xsrf)
        
        # saving it will
        self.http_client.fetch(self.get_url('/user/settings/'), self.stop,
                               method='POST',
                               body=urlencode({'a':'A', '_xsrf': xsrf}))
        response = self.wait()
        self.assertEqual(response.code, 200)
        self.assertTrue(db.users.User.find().count())        
        self.assertTrue(db.users.UserSettings.find().count())

        
        
        #self.assertTrue('Saturday' in response.body)
        #self.assertTrue('Sunday' in response.body)
        #print response.body.find('Monday'), response.body.find('Sunday')
        
        