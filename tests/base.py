from urllib import urlencode

from tornado.testing import LogTrapTestCase, AsyncHTTPTestCase

import app

class HTTPClientMixin(object):

    def get(self, url, data=None, headers=None):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data)
            if '?' in url:
                url += '&%s' % data
            else:
                url += '?%s' % data
        return self._fetch(url, 'GET', headers=headers)
    
    def post(self, url, data, headers=None):
        if data is not None:
            if isinstance(data, dict):
                data = urlencode(data)
        return self._fetch(url, 'POST', data, headers)
    
    def _fetch(self, url, method, data=None, headers=None):
        self.http_client.fetch(self.get_url(url), self.stop, method=method,
                               body=data, headers=headers)
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
        return app.Application(database_name='test', xsrf_cookies=False) # consider passing a different database name
    