import re
import unittest
from urllib import urlencode
from cStringIO import StringIO

from tornado.httpclient import HTTPRequest
from tornado.testing import LogTrapTestCase, AsyncHTTPTestCase

import app
from apps.main.models import User, Event, UserSettings, Share, \
  FeatureRequest, FeatureRequestComment


class BaseModelsTestCase(unittest.TestCase):
    _once = False
    def setUp(self):
        if not self._once:
            self._once = True
            from mongokit import Connection
            con = Connection()
            con.register([User, Event, UserSettings, Share, 
                          FeatureRequest, FeatureRequestComment])
            self.db = con.test
            self._emptyCollections()
            
    def _emptyCollections(self):
        [self.db.drop_collection(x) for x 
         in self.db.collection_names() 
         if x not in ('system.indexes',)]
        
    def tearDown(self):
        self._emptyCollections()


class HTTPClientMixin(object):

    def get(self, url, data=None, headers=None, follow_redirects=True):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data, True)
            if '?' in url:
                url += '&%s' % data
            else:
                url += '?%s' % data
        return self._fetch(url, 'GET', headers=headers,
                           follow_redirects=follow_redirects)
    
    def post(self, url, data, headers=None, follow_redirects=True):
        if data is not None:
            if isinstance(data, dict):
                #print urlencode(data)
                #print help(urlencode)
                data = urlencode(data, True)
                #print data
        return self._fetch(url, 'POST', data, headers, 
                           follow_redirects=follow_redirects)
    
    def _fetch(self, url, method, data=None, headers=None, follow_redirects=True):
        full_url = self.get_url(url)
        request = HTTPRequest(full_url, follow_redirects=follow_redirects,
                              headers=headers, method=method, body=data)
        self.http_client.fetch(request, self.stop)
        return self.wait()

    
                                
import Cookie
class TestClient(HTTPClientMixin):
    def __init__(self, testcase):
        self.testcase = testcase
        self.cookies = Cookie.SimpleCookie()

    def get(self, url, data=None, headers=None, follow_redirects=False):
        if self.cookies:
            if headers is None:
                headers = dict()
            headers['Cookie'] = self.cookies.output()
        response = self.testcase.get(url, data=data, headers=headers,
                                     follow_redirects=follow_redirects)
        self._update_cookies(response.headers)
        
        return response
    
    def post(self, url, data, headers=None, follow_redirects=False):
        if self.cookies:
            if headers is None:
                headers = dict()
            headers['Cookie'] = self.cookies.output()
        response = self.testcase.post(url, data=data, headers=headers,
                                     follow_redirects=follow_redirects)
        self._update_cookies(response.headers)
        return response
    
    def _update_cookies(self, headers):
        try:
            sc = headers['Set-Cookie']
            self.cookies = Cookie.SimpleCookie(sc)
        except KeyError:
            return
        
    def login(self, email, password):
        data = dict(email=email, password=password)
        response = self.post('/auth/login/', data, follow_redirects=False)
        if response.code != 302:
            raise LoginError(response.body)
        if 'Error' in response.body:
            raise LoginError(response.body)
        
        
        
class BaseHTTPTestCase(AsyncHTTPTestCase, LogTrapTestCase, HTTPClientMixin):
    
    _once = False
    def setUp(self):
        super(BaseHTTPTestCase, self).setUp()
        if not self._once:
            self._once = True
            self._emptyCollections()
            
        self._app.settings['email_backend'] = 'utils.send_mail.backends.locmem.EmailBackend'
        self._app.settings['email_exceptions'] = False
        
    def _emptyCollections(self):
        db = self.get_db()
        [db.drop_collection(x) for x 
         in db.collection_names() 
         if x not in ('system.indexes',)]
        
    def get_db(self):
        return self._app.con[self._app.database_name]
    
    def get_app(self):
        return app.Application(database_name='test', 
                               xsrf_cookies=False,
                               optimize_static_content=False)
                               
    def decode_cookie_value(self, key, cookie_value):
        try:
            return re.findall('%s=([\w=\|]+);' % key, cookie_value)[0]
        except IndexError:
            raise ValueError("couldn't find %r in %r" % (key, cookie_value))
