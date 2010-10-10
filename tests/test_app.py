from time import mktime, time
import re
import datetime
from urllib import urlencode
from mongokit import Connection
import simplejson as json
from tornado.testing import LogTrapTestCase, AsyncHTTPTestCase
from tornado.web import RequestHandler, _O

import app
from models import Event, User

#class CookieTestRequestHandler(RequestHandler):
#    # stub out enough methods to make the secure_cookie functions work
#    def __init__(self):
#        # don't call super.__init__
#        self._cookies = {}
#        self.application = _O(settings=dict(cookie_secret='0123456789'))
#
#    def get_cookie(self, name):
#        return self._cookies.get(name)
#
#    def set_cookie(self, name, value, expires_days=None):
#        self._cookies[name] = value


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
        return app.Application(database_name='test', xsrf_cookies=False) # consider passing a different database name
    
    def _get_xsrf(self, response):
        return re.findall('_xsrf=(\w+);', response.headers['Set-Cookie'])[0]
    
    def test_homepage(self):
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()
        self.assertTrue('id="calendar"' in response.body)
        
    def test_posting_events(self):
        today = datetime.date.today()
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        self.http_client.fetch(self.get_url('/events'), self.stop,
                               method='POST',
                               body=urlencode(data))
        response = self.wait()
        struct = json.loads(response.body)
        
    def test_events(self):
        url = '/events.json'
        start = datetime.datetime(2010, 10, 1)
        end = datetime.datetime(2010, 11, 1) - datetime.timedelta(days=1)
        start = mktime(start.timetuple())
        end = mktime(end.timetuple())
        url += '?start=%d&end=%d' % (start, end)
        self.http_client.fetch(self.get_url(url), self.stop)
        response = self.wait()
        self.assertEqual(response.code, 200)
        
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
        
        # rendering won't automatically create a user
        self.assertFalse(db.users.User.find().count())
        
        # rendering the user settings form won't either
        self.http_client.fetch(self.get_url('/user/settings/'), self.stop)
        response = self.wait()
        self.assertEqual(response.code, 200)
        self.assertFalse(db.users.User.find().count())
        #xsrf = self._get_xsrf(response)
        #print repr(xsrf)
        
        self.get_app().settings['xsrf_cookies'] = False

        # saving it will
        #data = {'a':'A', '_xsrf': xsrf}
        data = {}
        self.http_client.fetch(self.get_url('/user/settings/'), self.stop,
                               method='POST',
                               body=urlencode(data))
        response = self.wait()
        self.assertEqual(response.code, 200)
        self.assertTrue(db.users.User.find().count())        
        self.assertTrue(db.users.UserSettings.find().count())

        
        #self.assertTrue('Saturday' in response.body)
        #self.assertTrue('Sunday' in response.body)
        #print response.body.find('Monday'), response.body.find('Sunday')
        
    def test_share_calendar(self):
        db = self.get_db()
        
        self.http_client.fetch(self.get_url('/'), self.stop)
        response = self.wait()
        
        
        