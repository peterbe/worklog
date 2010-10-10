import unittest
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
    
    def get(self, url, data=None, headers=None):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data)
            if '?' in url:
                url += '&%s' % data
            else:
                url += '?%s' % data
        self.http_client.fetch(self.get_url(url), self.stop, headers=headers)
        return self.wait()
    
    def post(self, url, data, headers=None):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data)
        self.http_client.fetch(self.get_url(url), self.stop, method='POST',
                               body=data, headers=headers)
        return self.wait()
    
    def _get_xsrf(self, response):
        return re.findall('_xsrf=(\w+);', response.headers['Set-Cookie'])[0]
    
    
    def test_homepage(self):
        response = self.get('/')
        self.assertTrue('id="calendar"' in response.body)
        
    def test_posting_events(self):
        db = self.get_db()
        today = datetime.date.today()
        
        self.assertEqual(db.users.User.find().count(), 0)
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('event'))
        self.assertTrue(isinstance(struct['event'].get('start'), float))
        self.assertTrue(isinstance(struct['event'].get('end'), float))
        self.assertEqual(struct['event']['start'], struct['event']['end'])
        self.assertEqual(struct['event'].get('title'), 'Foo')
        self.assertEqual(struct.get('tags'), [])
        
        self.assertEqual(db.events.Event.find().count(), 1)
        event = db.events.Event.one()
        self.assertTrue(isinstance(event.start, datetime.datetime))
        
        first_of_this_month = datetime.datetime(today.year, today.month, 1)
        if today.month == 12:
            last_of_this_month = datetime.datetime(today.year + 1, 1, 1)
        else:
            last_of_this_month = datetime.datetime(today.year, today.month + 1, 1)
        last_of_this_month -= datetime.timedelta(days=1)
        
        self.assertEqual(db.events.Event.find({
          'start':{'$gte':first_of_this_month},
          'end':{'$lte': last_of_this_month}
          }).count(),
          1)
        self.assertEqual(db.users.User.find().count(), 1)
        
        guid_cookie = re.findall('guid=([\w\|]+);', response.headers['Set-Cookie'])[0]
        cookie = 'guid=%s;' % guid_cookie
        import base64
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(db.users.User.find({'guid':guid}).count(), 1)
        
        # with a tag this time
        data = {'title': "@fryit Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data, headers={'Cookie':cookie})
        struct = json.loads(response.body)
        self.assertTrue(struct.get('event'))
        self.assertEqual(struct.get('tags'), ['@fryit'])
        
        self.assertEqual(db.events.Event.find({
          'tags':'fryit'
        }).count(), 1)

        self.assertEqual(db.users.User.find().count(), 1)
        
        # change your preference for case on the fryit tag
        data = {'title': "@FryIT working on @Italy",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data, headers={'Cookie':cookie})
        struct = json.loads(response.body)
        self.assertTrue(struct.get('event'))
        self.assertEqual(struct.get('tags'), ['@Italy', '@FryIT'])
        
        self.assertEqual(db.users.User.find().count(), 1)
        
        self.assertEqual(db.events.Event.find({
          'tags':'FryIT'
        }).count(), 2)
        
        # Post with another tag that is contained in one of the existing ones
        data = {'title': "@It Experiment",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data, headers={'Cookie':cookie})
        
        self.assertEqual(db.users.User.find().count(), 1)
        # change the other ones from before
        self.assertEqual(db.events.Event.find({
          'tags':'FryIT'
        }).count(), 2)
        
        self.assertEqual(db.events.Event.find({
          'tags':'It'
        }).count(), 1)        
        
        
        
    def test_events(self):
        url = '/events.json'
        start = datetime.datetime(2010, 10, 1)
        end = datetime.datetime(2010, 11, 1) - datetime.timedelta(days=1)
        start = mktime(start.timetuple())
        end = mktime(end.timetuple())
        data = dict(start=start, end=end)
        response = self.get(url, data)
        self.assertEqual(response.code, 200)
        
        self.assertTrue('application/json' in response.headers['Content-Type'])
        self.assertTrue('UTF-8' in response.headers['Content-Type'])
        struct = json.loads(response.body)
        self.assertEqual(struct, dict(events=[], tags=[]))
        
        url = '/events.js'
        response = self.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertTrue('text/javascript' in response.headers['Content-Type'])
        self.assertTrue('UTF-8' in response.headers['Content-Type'])
        
        url = '/events.txt'
        response = self.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertTrue('text/plain' in response.headers['Content-Type'])
        self.assertTrue('UTF-8' in response.headers['Content-Type'])
        self.assertTrue('ENTRIES\n' in response.body)
        self.assertTrue('TAGS\n' in response.body)
        
    def test_events_stats(self):
        pass
        
    def test_set_user_settings(self):
        pass
    
    def test_share_calendar(self):
        pass

        
        