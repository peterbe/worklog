from time import mktime
from pymongo.objectid import ObjectId
import datetime
from apps.main.tests.base import BaseHTTPTestCase
from utils.http_test_client import TestClient
from apps.eventlog.constants import *

class EventLogsTestCase(BaseHTTPTestCase):

    def test_posting_editing_deleting_restoring(self):
        db = self.get_db()
        client = TestClient(self)

        today = datetime.date.today()
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = client.post('/events/', data)
        self.assertEqual(response.code, 200)
        event = db.Event.one()

        from apps.eventlog.models import EventLog

        self.assertEqual(db.EventLog.find().count(), 1)
        assert db.EventLog.one({'action': ACTION_ADD})

        data = {'id': str(event._id),
                'all_day':'1',
                'title': 'New title'}
        response = client.post('/event/edit/', data)
        event = db.Event.one()
        assert event.title == 'New title'

        self.assertEqual(db.EventLog.find().count(), 2)
        self.assertTrue(db.EventLog.one({'action': ACTION_EDIT}))

        data['days'] = '3'
        data['minutes'] = 0
        response = client.post('/event/resize/', data)
        self.assertEqual(response.code, 200)
        assert 'error' not in response.body

        event = db.Event.one({'_id': ObjectId(data['id'])})
        assert (event.end - event.start).days == 3

        self.assertEqual(db.EventLog.find().count(), 3)
        self.assertEqual(db.EventLog.find({'action': ACTION_EDIT}).count(), 2)
        self.assertTrue(db.EventLog.one({'comment': u'resize'}))

        response = client.post('/event/delete/', data)
        self.assertEqual(response.code, 200)
        assert 'error' not in response.body
        event = db.Event.one({'_id': ObjectId(data['id'])})
        assert event.user.guid == 'UNDOER'

        self.assertTrue(db.EventLog.one({'action': ACTION_DELETE}))

        response = client.post('/event/undodelete/', {'id': data['id']})
        self.assertEqual(response.code, 200)
        assert 'error' not in response.body
        event = db.Event.one({'_id': ObjectId(data['id'])})
        assert event.user.guid != 'UNDOER'

        self.assertTrue(db.EventLog.one({'action': ACTION_RESTORE}))

    def test_bookmarkleting_and_log(self):
        db = self.get_db()

        client = TestClient(self)

        today = datetime.date.today()
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = client.post('/events/', data)
        self.assertEqual(response.code, 200)

        future = datetime.datetime.now() + datetime.timedelta(hours=2)
        data = dict(now=mktime(future.timetuple()),
                    title="somethign")
        response = client.post('/bookmarklet/', data)
        self.assertEqual(response.code, 200)
        assert db.Event.one({'title': data['title']})

        self.assertTrue(db.EventLog.one(
          {'action': ACTION_ADD, 'context': CONTEXT_BOOKMARKLET}))

    def test_posting_with_api(self):
        db = self.get_db()
        today = datetime.date.today()

        peter = self.get_db().users.User()
        assert peter.guid
        peter.save()
        data = dict(guid=peter.guid,
                    title="SOmething",
                    data=mktime(today.timetuple()))
        response = self.post('/api/events.json', data)
        self.assertEqual(response.code, 201)

        self.assertTrue(db.EventLog.one(
          {'action': ACTION_ADD, 'context': CONTEXT_API}))