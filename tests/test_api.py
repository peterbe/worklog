from pymongo.objectid import InvalidId, ObjectId
import datetime
import simplejson as json
from time import mktime
from base import BaseHTTPTestCase


class APITestCase(BaseHTTPTestCase):
    
    def test_getting_events(self):
        response = self.get('/api/events.json')
        self.assertEqual(response.code, 404)
        self.assertTrue('guid not supplied' in response.body)
        self.assertTrue('text/plain' in response.headers['Content-type'])

        response = self.get('/api/events.json', dict(guid='xxx'))
        self.assertEqual(response.code, 403)
        self.assertTrue('guid not recognized' in response.body)
        
        from models import User
        peter = self.get_db().users.User()
        assert peter.guid
        peter.save()
        
        assert self.get_db().users.User.find().count()
        data = dict(guid=peter.guid)
        response = self.get('/api/events.json', data)
        self.assertEqual(response.code, 404)
        self.assertTrue('start timestamp not' in response.body)
        
        today = datetime.date.today()
        first = datetime.date(today.year, today.month, 1)

        data['start'] = int(mktime(first.timetuple()))
        response = self.get('/api/events.json', data)
        self.assertEqual(response.code, 404)
        self.assertTrue('end timestamp not' in response.body)
        
        if today.month == 12:
            last = datetime.datetime(today.year + 1, 1, 1)
        else:
            last = datetime.datetime(today.year, today.month + 1, 1)
        last -= datetime.timedelta(days=1)
        
        data['end'] = int(mktime(last.timetuple()))
        response = self.get('/api/events.json', data)
        self.assertEqual(response.code, 200)
        self.assertTrue('application/json' in response.headers['Content-Type'])
        self.assertTrue('UTF-8' in response.headers['Content-Type'])
        self.assertTrue('start timestamp not' not in response.body)
        self.assertTrue('end timestamp not' not in response.body)
        
        struct = json.loads(response.body)
        self.assertEqual(struct.get('events'), [])
        self.assertEqual(struct.get('tags'), [])
        
        # post an event
        event1 = self.get_db().events.Event()
        event1.user = peter
        event1.title = u"Test1"
        event1.all_day = True
        event1.start = datetime.datetime.today()
        event1.end = datetime.datetime.today()
        event1.url = u'http://www.peterbe.com'
        event1.save()
        
        struct = json.loads(self.get('/api/events.json', data).body)
        self.assertTrue(struct.get('events'))
        self.assertEqual(len(struct['events']), 1)
        self.assertEqual(struct['events'][0]['title'], event1.title)
        self.assertEqual(struct['events'][0]['id'], str(event1._id))
        self.assertEqual(struct['events'][0]['allDay'], True)
        self.assertEqual(struct['events'][0]['url'], event1.url)
        self.assertEqual(struct.get('tags'), [])
        
        # some time in the middle of the current month
        this_month = datetime.datetime(today.year, today.month, 15, 13, 0)
        next_month = this_month + datetime.timedelta(days=30)
        event2 = self.get_db().events.Event()
        event2.user = peter
        event2.title = u"Test2"
        event2.all_day = False
        event2.start = next_month
        event2.end = next_month + datetime.timedelta(minutes=60)
        event2.tags = [u'Tag']
        event2.save()

        struct = json.loads(self.get('/api/events.json', data).body)
        self.assertEqual(len(struct['events']), 1)
        self.assertEqual(struct.get('tags'), [])

        data['start'] += 60 * 60 * 24 * 30
        data['end'] += 60 * 60 * 24 * 30
        struct = json.loads(self.get('/api/events.json', data).body)
        self.assertEqual(len(struct['events']), 1)
        
        self.assertEqual(struct['events'][0]['title'], event2.title)
        self.assertEqual(struct.get('tags'), ['@Tag'])
        
    def test_posting_events(self):
        response = self.post('/api/events.json', {})
        self.assertEqual(response.code, 404)
        self.assertTrue('guid not supplied' in response.body)
        self.assertTrue('text/plain' in response.headers['Content-type'])

        response = self.post('/api/events.json', dict(guid='xxx'))
        self.assertEqual(response.code, 403)
        self.assertTrue('guid not recognized' in response.body)
        
        from models import User
        peter = self.get_db().users.User()
        assert peter.guid
        peter.save()
        
        assert self.get_db().users.User.find().count()
        data = dict(guid=peter.guid)
        response = self.post('/api/events.json', data)
        self.assertEqual(response.code, 404)
        self.assertTrue('title not supplied' in response.body)

        data['title'] = u"<script>alert('xss')</script> @tagged"
        response = self.post('/api/events.json', data)
        self.assertEqual(response.code, 404)
        self.assertTrue('date or (start and end) not supplied' in response.body)
        
        today = datetime.date.today()
        data['date'] = mktime(today.timetuple())
        response = self.post('/api/events.json', data)
        self.assertEqual(response.code, 201)
        self.assertTrue('</script>' not in response.body)
        struct = json.loads(response.body)
        
        self.assertEqual(struct['event']['allDay'], True)
        self.assertEqual(struct['event']['title'], data['title'])
        self.assertEqual(struct['tags'], ['@tagged'])
        self.assertTrue(struct['event'].get('id'))
        
        event = self.get_db().events.Event.one({'_id': ObjectId(struct['event']['id'])})
        self.assertEqual(event.user['_id'], peter['_id'])
        self.assertEqual(event['tags'], ['tagged'])
        
        self.assertEqual(self.get_db().events.Event.find().count(), 1)
        # post the same thing again
        response = self.post('/api/events.json', data)
        self.assertEqual(response.code, 200)
        struct_again = json.loads(response.body)
        self.assertEqual(struct_again, struct)
        
