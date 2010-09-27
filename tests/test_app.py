import simplejson as json
from tornado.testing import LogTrapTestCase, AsyncHTTPTestCase

from app import Application

class ApplicationTest(AsyncHTTPTestCase, LogTrapTestCase):
    
    def get_app(self):
        return Application(database_name='test') # consider passing a different database name
    
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
        
        