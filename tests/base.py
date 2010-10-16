import time
import base64
from urllib import urlencode

from tornado.httpclient import HTTPRequest
from tornado.testing import LogTrapTestCase, AsyncHTTPTestCase

import app

class HTTPClientMixin(object):

    def get(self, url, data=None, headers=None, follow_redirects=True):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data)
            if '?' in url:
                url += '&%s' % data
            else:
                url += '?%s' % data
        return self._fetch(url, 'GET', headers=headers,
                           follow_redirects=follow_redirects)
    
    def post(self, url, data, headers=None, follow_redirects=True):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data)
        return self._fetch(url, 'POST', data, headers, 
                           follow_redirects=follow_redirects)
    
    def _fetch(self, url, method, data=None, headers=None, follow_redirects=True):
        request = HTTPRequest(self.get_url(url), follow_redirects=follow_redirects,
                              headers=headers, method=method, body=data)
        self.http_client.fetch(request, self.stop)
        return self.wait()
    
                                
    
    
class BaseHTTPTestCase(AsyncHTTPTestCase, LogTrapTestCase, HTTPClientMixin):
    
    _once = False
    def setUp(self):
        super(BaseHTTPTestCase, self).setUp()
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
        return app.Application(database_name='test', xsrf_cookies=False) 
    