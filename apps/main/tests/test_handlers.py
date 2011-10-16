import base64
from pprint import pprint
from time import mktime
import re
import datetime
import simplejson as json

from base import BaseHTTPTestCase
from utils import encrypt_password
#from apps.main.models import Event, User, Share
import utils.send_mail as mail
from apps.main.config import MINIMUM_DAY_SECONDS
from tornado_utils.http_test_client import TestClient


class ApplicationTestCase(BaseHTTPTestCase):

    def _login(self, email=u"test@test.com"):
        user = self.db.User()
        user.email = unicode(email)
        user.set_password('secret')
        user.save()

        data = dict(email=user.email, password="secret")
        response = self.client.post('/auth/login/', data)
        assert response.code == 302
        return user

    def test_homepage(self):
        response = self.client.get('/')
        self.assertTrue('id="calendar"' in response.body)

    def test_posting_events(self):
        today = datetime.date.today()

        self.assertEqual(self.db.User.find().count(), 0)
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('event'))
        self.assertTrue(isinstance(struct['event'].get('start'), float))
        self.assertTrue(isinstance(struct['event'].get('end'), float))
        self.assertEqual(struct['event']['start'], struct['event']['end'])
        self.assertEqual(struct['event'].get('title'), 'Foo')
        self.assertEqual(struct.get('tags'), [])

        self.assertEqual(self.db.Event.find().count(), 1)
        event = self.db.Event.one()
        self.assertTrue(isinstance(event.start, datetime.datetime))

        first_of_this_month = datetime.datetime(today.year, today.month, 1)
        if today.month == 12:
            last_of_this_month = datetime.datetime(today.year + 1, 1, 1)
        else:
            last_of_this_month = datetime.datetime(today.year, today.month + 1, 1)
        last_of_this_month -= datetime.timedelta(days=1)

        self.assertEqual(self.db.Event.find({
          'start':{'$gte':first_of_this_month},
          'end':{'$lte': last_of_this_month}
          }).count(),
          1)
        self.assertEqual(self.db.User.find().count(), 1)

        #guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        #cookie = 'guid=%s;' % guid_cookie
        guid_cookie = self.client.cookies['guid'].value
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(self.db.User.find({'guid':guid}).count(), 1)

        # with a tag this time
        data = {'title': "@fryit Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('event'))
        self.assertEqual(struct.get('tags'), ['@fryit'])

        self.assertEqual(self.db.Event.find({
          'tags':'fryit'
        }).count(), 1)

        self.assertEqual(self.db.User.find().count(), 1)

        # change your preference for case on the fryit tag
        data = {'title': "@FryIT working on @Italy",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('event'))
        self.assertEqual(struct.get('tags'), ['@Italy', '@FryIT'])

        self.assertEqual(self.db.User.find().count(), 1)

        self.assertEqual(self.db.Event.find({
          'tags':'FryIT'
        }).count(), 2)

        # Post with another tag that is contained in one of the existing ones
        data = {'title': "@It Experiment",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)

        self.assertEqual(self.db.User.find().count(), 1)
        # change the other ones from before
        self.assertEqual(self.db.Event.find({
          'tags':'FryIT'
        }).count(), 2)

        self.assertEqual(self.db.Event.find({
          'tags':'It'
        }).count(), 1)

    def test_editing_event(self):
        today = datetime.datetime.today()
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']

        event_obj = self.db.Event.one(dict(title="Foo"))
        event_user = event_obj.user
        self.assertTrue(event_obj.all_day)

        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(self.db.User.find({'guid':guid}).count(), 1)

        # move it
        data = {'id': event_id,
                'all_day': 'true', # still
                'days': '-1',
                'minutes': 0}
        response = self.client.post('/event/move/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        new_start = struct['event']['start']
        self.assertEqual(new_start, struct['event']['end'])
        new_start = datetime.datetime.fromtimestamp(new_start)
        self.assertEqual((today - new_start).days, 1)

        event_obj = self.db.Event.one(dict(title="Foo"))
        self.assertTrue(event_obj.all_day)

        # resize it
        data = {'id': event_id,
                'all_day': '',
                'days': '3',
                'minutes': 0}
        response = self.client.post('/event/resize/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        new_start = struct['event']['start']
        new_end = struct['event']['end']
        self.assertNotEqual(new_start, new_end)
        new_start = datetime.datetime.fromtimestamp(new_start)
        new_end = datetime.datetime.fromtimestamp(new_end)
        self.assertEqual((new_end - new_start).days, 3)

        # try resizing it again in the wrong way
        data = {'id': event_id,
                'all_day': '',
                'days': '0',
                'minutes': 10}
        response = self.client.post('/event/resize/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('error'))

        # render the edit template
        data = {'id': event_id}

        # edit title
        data['title'] = 'New title'
        response = self.client.post('/event/edit/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['title'], data['title'])
        self.assertTrue('description' not in struct['event'])
        self.assertTrue(self.db.Event.one({'title':'New title'}))

        data['description'] = '\nA longer description\n'
        response = self.client.post('/event/edit/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['description'], data['description'].strip())
        self.assertTrue(self.db.Event.one({'description': data['description'].strip()}))

        # edit URL (wrong)
        data = {'id': event_id,
                'title': 'New title',
                'external_url': 'junk'}
        response = self.client.post('/event/edit/', data)
        self.assertEqual(response.code, 400)
        # edit URL (right)
        data['external_url'] = 'http://www.peterbe.com'
        response = self.client.post('/event/edit/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['external_url'], data['external_url'])

        # delete
        data = {'id': '___'}
        response = self.client.post('/event/delete/', data)
        self.assertEqual(response.code, 404)

        data['id'] = event_id
        response = self.client.post('/event/delete/', data)
        self.assertEqual(response.code, 200)

        search = {'user.$id': event_user._id}
        self.assertTrue(not self.db.Event.find(search).count())

    def test_moving_all_day_event_to_not_all_day_event(self):
        today = datetime.datetime.today()
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']

        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie

        event_obj = self.db.Event.one(dict(title="Foo"))
        event_user = event_obj.user
        # now move it from an all_day event to a day event
        data = {'event':{}, 'id':str(event_obj._id), 'days':0, 'minutes':800}
        now = datetime.datetime(today.year, today.month, today.day, 10, 30, 0)
        data['event']['start'] = mktime(now.timetuple())
        data['event']['allDay'] = False
        data['event']['end'] = data['event']['start'] # this is what fullCalendar does
        data['event']['id'] = str(event_obj._id)
        data['event']['title'] = event_obj.title
        response = self.client.post('/event/move/', data)
        self.assertEqual(response.code, 200)

        event_obj = self.db.Event.one(dict(_id=event_obj._id))
        self.assertTrue(not event_obj.all_day)
        self.assertNotEqual(event_obj.start, event_obj.end)
        self.assertTrue(event_obj.end > event_obj.start)

    def test_getting_event_for_edit_json(self):
        today = datetime.datetime.today()
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']

        event_obj = self.db.Event.one(dict(title="Foo"))
        self.assertTrue(event_obj.all_day)

        #guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        #cookie = 'guid=%s;' % guid_cookie
        guid_cookie = self.client.cookies['guid']
        guid = base64.b64decode(guid_cookie.value.split('|')[0])
        self.assertEqual(self.db.User.find({'guid':guid}).count(), 1)

        url = '/event.json'
        client2 = TestClient(self)
        response = client2.get(url, dict(id=event_id))
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('error'))

        response = self.client.get(url, dict(id=event_id))
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct.get('title'), data['title'])
        self.assertTrue('description' not in struct)

        event_obj.description = u"A description"
        event_obj.save()

        response = self.client.get(url, dict(id=event_id))
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['description'], event_obj.description)

    def test_get_event_stats(self):
        today = datetime.date.today()

        response = self.client.get('/events/stats.json')
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct,
          {'hours_spent': [], 'days_spent': []})

        self.assertEqual(self.db.User.find().count(), 0)
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)

        response = self.client.get('/events/stats.json')
        self.assertEqual(response.code, 200)

        struct = json.loads(response.body)
        self.assertEqual(struct.get('hours_spent'), [])
        self.assertTrue(struct.get('days_spent'))
        self.assertEqual(len(struct.get('days_spent')), 1)
        self.assertTrue(struct.get('days_spent')[0][1], 1.0)
        self.assertTrue('untagged' in struct.get('days_spent')[0][0].lower())

        data = {'title': "Foo2 @tagged",
                'date': mktime(today.timetuple()),
                'all_day': 'no'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)

        response = self.client.get('/events/stats.json')
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct.get('hours_spent'),
                         [['tagged', MINIMUM_DAY_SECONDS/float(60*60)]])

        data = {'title': "Foo3 @tagged",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        event = self.db.Event.one(dict(title=data['title']))
        event.end += datetime.timedelta(days=2)
        event.save()

        response = self.client.get('/events/stats.json')
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        days_spent = struct['days_spent']
        self.assertEqual(len(days_spent), 2)
        numbers = [x[1] for x in days_spent]
        self.assertEqual(numbers, [1.0, 3.])

        response = self.client.get('/events/stats.txt')
        self.assertEqual(response.code, 200)
        self.assertTrue('*Untagged*' in response.body)
        self.assertEqual(response.body.count('1.0'), 1)
        self.assertEqual(response.body.count('3.0'), 1)


    def test_previewing_posted_events(self):
        today = datetime.date.today()

        self.assertEqual(self.db.User.find().count(), 0)
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']

        #guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        #cookie = 'guid=%s;' % guid_cookie
        guid_cookie = self.client.cookies['guid'].value
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(self.db.User.find({'guid':guid}).count(), 1)

        client2 = TestClient(self)
        response = client2.get('/event?id=%s' % event_id)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('error'))  # not logged in

        response = self.client.get('/event.html?id=%s' % event_id)
        self.assertEqual(response.code, 200)
        self.assertTrue(data['title'] in response.body)
        self.assertTrue("by peter" not in response.body.lower())
        self.assertTrue("added seconds ago" in response.body.lower())

        event = self.db.Event.one(dict(title=data['title']))
        event.add_date -= datetime.timedelta(minutes=3)
        event.save()

        user = self.db.User.one({'guid':guid})
        user.email = u"peter@fry-it.com"
        user.save()

        response = self.client.get('/event.html?id=%s' % event_id)
        self.assertEqual(response.code, 200)
        self.assertTrue(data['title'] in response.body)
        self.assertTrue("peter@fry-it.com" in response.body)
        self.assertTrue("Added 3 minutes ago" in response.body)

        user.first_name = u"Peter"
        user.save()

        self.assertTrue("Peter" not in response.body)
        response = self.client.get('/event.html?id=%s' % event_id)
        self.assertEqual(response.code, 200)
        self.assertTrue("by Peter" in response.body)

        response = self.client.get('/event.html?id=______')
        self.assertEqual(response.code, 404)


    def test_previewing_shared_event(self):
        # post one yourself first so that you become someone
        today = datetime.datetime.today()
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']

        #guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        #cookie = 'guid=%s;' % guid_cookie
        guid_cookie = self.client.cookies['guid'].value
        guid = base64.b64decode(guid_cookie.split('|')[0])

        # try to preview someone else's event
        user2 = self.db.User()
        user2.email = u"ashley@test.com"
        user2.save()

        event = self.db.Event()
        event.user = user2
        event.title = u"Testing @at"
        event.all_day = True
        event.start = datetime.datetime.today()
        event.end = datetime.datetime.today()
        event.save()
        event_id = str(event._id)


        # you can't view this one yet
        response = self.client.get('/event/?id=%s' % event_id)
        self.assertEqual(response.code, 403)

        # user2 needs to create a share
        user3 = self.db.User()
        user3.email = u"else@test.com"
        user3.save()

        self.assertTrue(self.db.User.one({'guid':guid}))

        share = self.db.Share()
        share.user = user2._id
        share.users = [user3._id]
        share.save()

        response = self.client.get('/share/%s' % share.key,
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        #shares_cookie = self.decode_cookie_value('shares', response.headers['Set-Cookie'])
        #
        #cookie += ';shares=%s' % shares_cookie
        response = self.client.get('/event/?id=%s' % event_id)
        # shared but not shared with this user

        self.assertEqual(response.code, 403)

        share.users = []
        share.save()

        response = self.client.get('/event/', {'id': event_id})
        self.assertEqual(response.code, 200)

    def test_sharing_with_yourself(self):
        """test using the share on yourself"""
        # post one yourself first so that you become someone
        today = datetime.datetime.today()
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        #event_id = struct['event']['id']

        #guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        #cookie = 'guid=%s;' % guid_cookie
        guid_cookie = self.client.cookies['guid'].value
        guid = base64.b64decode(guid_cookie.split('|')[0])

        user = self.db.User.one()
        self.assertEqual(user.guid, guid)
        user.email = u'test@peterbe.com'
        user.save()

        share = self.db.Share()
        share.user = user._id
        share.key = u'foo'
        share.save()

        # use it yourself
        response = self.client.get('/share/%s' % share.key,
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue('Set-Cookie' not in response.headers) # because no cookie is set
        #shares_cookie = self.decode_cookie_value('shares', response.headers['Set-Cookie'])

        user2 = self.db.User()
        user2.email = u'one@two.com'
        user2.save()

        share2 = self.db.Share()
        share2.user = user2._id
        share2.key = u'foo2'
        share2.save()

        response = self.client.get('/share/%s' % share2.key,
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        #self.assertTrue('Set-Cookie' not in response.headers) # because no cookie is set
        #shares_cookie = self.decode_cookie_value('shares', response.headers['Set-Cookie'])
        #cookie += 'shares=%s;' % shares_cookie
        #shares = base64.b64decode(shares_cookie.split('|')[0])
        #self.assertEqual(shares, 'foo2')

        user3 = self.db.User()
        user3.email = u'ass@three.com'
        user3.save()

        share3 = self.db.Share()
        share3.user = user3._id
        share3.key = u'foo3'
        share3.save()

        response = self.client.get('/share/%s' % share3.key,
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        #shares_cookie = self.decode_cookie_value('shares', response.headers['Set-Cookie'])
        shares_cookie = self.client.cookies['shares'].value
        shares = base64.b64decode(shares_cookie.split('|')[0])
        self.assertEqual(shares, 'foo2,foo3')


    def test_events(self):
        url = '/events.json'
        start = datetime.datetime(2010, 10, 1)
        end = datetime.datetime(2010, 11, 1) - datetime.timedelta(days=1)
        start = mktime(start.timetuple())
        end = mktime(end.timetuple())
        data = dict(start=start, end=end)
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)

        self.assertTrue('application/json' in response.headers['Content-Type'])
        self.assertTrue('UTF-8' in response.headers['Content-Type'])
        struct = json.loads(response.body)
        self.assertEqual(struct, dict(events=[]))

        data['include_tags'] = 'yes'
        response = self.client.get(url, data)
        struct = json.loads(response.body)
        self.assertEqual(struct, dict(events=[], tags=[]))

        url = '/events.js'
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertTrue('text/javascript' in response.headers['Content-Type'])
        self.assertTrue('UTF-8' in response.headers['Content-Type'])

        url = '/events.txt'
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertTrue('text/plain' in response.headers['Content-Type'])
        self.assertTrue('UTF-8' in response.headers['Content-Type'])
        self.assertTrue('ENTRIES\n' in response.body)
        self.assertTrue('TAGS\n' in response.body)

    def test_view_shared_calendar(self):

        user = self.db.User()
        user.email = u"peter@fry-it.com"
        user.save()

        event = self.db.Event()
        event.user = user
        event.title = u"Title"
        event.start = datetime.datetime(2010,10, 13)
        event.end = datetime.datetime(2010,10, 13)
        event.all_day = True
        event.tags = [u"tag1"]
        event.save()


        share = self.db.Share()
        share.user = user._id
        share.save()

        url = '/share/%s' % share.key
        response = self.client.get(url, follow_redirects=False)
        self.assertEqual(response.code, 302)
        #shares_cookie = self.decode_cookie_value('shares', response.headers['Set-Cookie'])
        #cookie = 'shares=%s;' % shares_cookie
        data = dict(start=mktime(datetime.datetime(2010,10,1).timetuple()),
                    end=mktime(datetime.datetime(2010,10,30).timetuple()))
        response = self.client.get('/events.json', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['events'][0]['title'], event.title)
        self.assertTrue('tags' not in struct)

        data['include_tags'] = 'yes'
        response = self.client.get('/events.json', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        #self.assertEqual(struct['tags'], [u"@tag1"])
        self.assertEqual(struct['tags'], [])

        event2 = self.db.Event()
        event2.user = user
        event2.title = u"Title 2"
        event2.start = datetime.datetime(2010,10, 14)
        event2.end = datetime.datetime(2010,10, 14)
        event2.all_day = True
        event2.tags = [u"tag2"]
        event2.save()

        share.tags = [u'tag2']
        share.save()

        response = self.client.get('/events.json', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['events'][0]['title'], event2.title)

    def test_user_settings(self):
        response = self.client.get('/user/settings/')
        self.assertEqual(response.code, 200)
        # nothing is checked
        self.assertTrue(not response.body.count('checked'))
        self.assertTrue('name="hide_weekend"' in response.body)
        self.assertTrue('name="monday_first"' in response.body)
        self.assertTrue('name="disable_sound"' in response.body)

        response = self.client.get('/user/settings.js')
        self.assertEqual(response.code, 200)
        json_str = re.findall('{.*?}', response.body)[0]
        settings = json.loads(json_str)
        self.assertEqual(settings['hide_weekend'], False)
        self.assertEqual(settings['monday_first'], False)

        data = {'hide_weekend':True,
                'disable_sound':True,
                'first_hour':10}
        response = self.client.post('/user/settings/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        guid = base64.b64decode(guid_cookie.split('|')[0])

        user = self.db.User.one(dict(guid=guid))
        user_settings = self.db.UserSettings.one({
          'user': user._id
        })
        self.assertTrue(user_settings.hide_weekend)
        self.assertTrue(user_settings.disable_sound)
        self.assertEqual(user_settings.first_hour, 10)
        self.assertFalse(user_settings.monday_first)

    def test_share_calendar(self):
        response = self.client.get('/share/')
        self.assertEqual(response.code, 200)
        self.assertTrue("don't have anything" in response.body)

        today = datetime.date.today()

        data = {'title': "@tag1 @tag2 Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        #response = self.client.post('/events/', data)
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)

        #guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        #cookie = 'guid=%s;' % guid_cookie
        #guid = base64.b64decode(guid_cookie.split('|')[0])
        user, = self.db.User.find()
        guid = user.guid

        response = self.client.get('/share/')
        self.assertEqual(response.code, 200)
        self.assertTrue("can't share yet" in response.body.lower())

        user = self.db.User.one(dict(guid=guid))
        user.first_name = u"peter"
        user.save()

        response = self.client.get('/share/')
        self.assertEqual(response.code, 200)

        # expect there to be a full URL in the HTML
        url = re.findall('value="http(.*)"', response.body)[0]
        key = re.findall('/share/(.*)', url)[0]
        share = self.db.Share.one(dict(key=key))
        self.assertTrue(share)
        self.assertEqual(share.user, user)

        data = {'id': str(share._id), 'tags':'tag2'}
        #response = self.client.post('/share/edit/', data)
        response = self.client.post('/share/edit/', data)
        self.assertEqual(response.code, 200)
        share = self.db.Share.one(dict(_id=share._id))
        self.assertEqual(share.tags, [u'tag2'])

        # so a new user can start using this
        client2 = TestClient(self)
        response = client2.get('/share/%s' % key, follow_redirects=False)
        self.assertEqual(response.code, 302)
        #shares_cookie = self.decode_cookie_value('shares', response.headers['Set-Cookie'])
        #cookie = 'shares=%s;' % shares_cookie

        # I can now toggle this share to be hidden
        #response = self.client.post('/share/', dict(), headers={'Cookie': cookie})
        response = client2.post('/share/', dict())
        self.assertEqual(response.code, 400)

        #response = self.client.post('/share/', dict(key='bullshit'), headers={'Cookie': cookie})
        response = client2.post('/share/', dict(key='bullshit'))
        self.assertEqual(response.code, 404)

        #response = self.client.post('/share/', dict(key=key), headers={'Cookie': cookie})
        response = client2.post('/share/', dict(key=key))
        self.assertEqual(response.code, 200)
        assert client2.cookies['hidden_shares']

    def test_signup(self):
        # the get method is just used to validate if an email is used another
        # user
        response = self.client.get('/user/signup/')
        self.assertEqual(response.code, 404)

        data = {'validate_email': 'peter@test.com'}
        response = self.client.get('/user/signup/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, dict(ok=True))

        user = self.db.users.User()
        user.email = u"Peter@Test.com"
        user.save()

        data = {'validate_email': 'peter@test.com'}
        response = self.client.get('/user/signup/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, dict(error='taken'))

        data = dict(email="peterbe@gmail.com",
                    password="secret",
                    first_name="Peter",
                    last_name="Bengtsson")
        response = self.client.post('/user/signup/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)

        data.pop('password')
        user = self.db.users.User.one(data)
        self.assertTrue(user)

        # a secure cookie would have been set containing the user id
        user_cookie = self.client.cookies['user'].value
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(user.guid, guid)

    def test_change_account(self):
        user = self.db.User()
        user.email = u"peter@fry-it.com"
        user.first_name = u"Ptr"
        user.password = encrypt_password(u"secret")
        user.save()

        other_user = self.db.User()
        other_user.email = u'peterbe@gmail.com'
        other_user.save()

        data = dict(email=user.email, password="secret")
        response = self.client.post('/auth/login/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)

        response = self.client.get('/user/account/')
        self.assertEqual(response.code, 200)
        self.assertTrue('value="Ptr"' in response.body)

        # not logged in
        client2 = TestClient(self)
        response = client2.post('/user/account/', {})
        self.assertEqual(response.code, 403)

        # no email supplied
        response = self.client.post('/user/account/', {})
        self.assertEqual(response.code, 400)

        data = {'email':'bob'}
        response = self.client.post('/user/account/', data)
        self.assertEqual(response.code, 400)

        data = {'email':'PETERBE@gmail.com'}
        response = self.client.post('/user/account/', data)
        self.assertEqual(response.code, 400)

        data = {'email':'bob@test.com', 'last_name': '  Last Name \n'}
        response = self.client.post('/user/account/', data,
                             follow_redirects=False)
        self.assertEqual(response.code, 302)

        user = self.db.User.one(dict(email='bob@test.com'))
        self.assertEqual(user.last_name, data['last_name'].strip())

        # log out
        response = self.client.get('/auth/logout/',
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue('user=;' in response.headers['Set-Cookie'])

    def test_bookmarklet_with_cookie(self):
        today = datetime.date.today()
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        #guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        #cookie = 'guid=%s;' % guid_cookie
        guid_cookie = self.client.cookies['guid'].value
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(self.db.User.find({'guid':guid}).count(), 1)
        user = self.db.User.one({'guid':guid})

        response = self.client.get('/bookmarklet/')
        self.assertTrue('external_url' not in response.body)

        data = {'external_url': 'http://www.peterbe.com/page'}
        response = self.client.get('/bookmarklet/', data)
        self.assertTrue('value="%s"' % data['external_url'] in response.body)

        # post something now
        # ...but fail first
        data = dict()
        response = self.client.post('/bookmarklet/', data)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "'now' not sent. Javascript must be enabled")

        future = datetime.datetime.now() + datetime.timedelta(hours=2)
        data = dict(now=mktime(future.timetuple()))
        response = self.client.post('/bookmarklet/', data)
        self.assertEqual(response.code, 200)
        self.assertTrue('Error: No title entered' in response.body)

        data['title'] = u" Saving the day "
        response = self.client.post('/bookmarklet/', data)
        self.assertEqual(response.code, 200)
        self.assertTrue('Thanks!' in response.body)

        event = self.db.Event.one({'title':data['title'].strip(),
                              'user.$id':user._id})
        self.assertEqual(event.all_day, True)
        self.assertEqual(
          event.start.strftime('%Y%m%d%H%M'),
          future.strftime('%Y%m%d%H%M')
        )
        self.assertEqual(
          event.end.strftime('%Y%m%d%H%M'),
          future.strftime('%Y%m%d%H%M')
        )

        # now test posting something without a title but with a long description
        data['title'] = ''
        data['description'] = 'now test posting something without a title but '\
                              'with a long description with email@address.com '\
                              'in the description'
        past = future - datetime.timedelta(hours=2)
        data['now'] = mktime(past.timetuple())
        response = self.client.post('/bookmarklet/', data)
        event = self.db.Event.one({'user.$id':user._id,
                              'title': re.compile('^now')})

        self.assertTrue(event.title.endswith('...'))
        self.assertTrue(len(event.title) < len(event.description))
        self.assertEqual(event.description, data['description'])
        self.assertEqual(event.tags, [])

        # try again, writing on multiple lines
        data['description'] = 'Line one\nLine two\nLine three'
        response = self.client.post('/bookmarklet/', data)
        event = self.db.Event.one({'user.$id':user._id,
                              'title': re.compile('^Line')})
        self.assertEqual(event.title, u"Line one")
        self.assertEqual(event.description, u"Line two\nLine three")

        # one more time when the description is short
        data['description'] = "@mytag one word"
        response = self.client.post('/bookmarklet/', data)
        event = self.db.Event.one({'user.$id':user._id,
                              'title': data['description']})
        self.assertEqual(event.description, u"")
        self.assertEqual(event.tags, [u'mytag'])

        # try making it a half hour event
        data['length'] = '0.5'
        data['title'] = "half hour event"
        data['description'] = ''
        data['now'] = mktime(future.timetuple())
        response = self.client.post('/bookmarklet/', data)
        event = self.db.Event.one({'user.$id':user._id,
                              'title': data['title']})
        diff_seconds = (event.end - event.start).seconds
        self.assertEqual(diff_seconds, 60 * 30)
        self.assertTrue(not event.all_day)


    def test_bookmarklet_with_cookie_with_suggested_tags(self):
        today = datetime.date.today()

        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(self.db.User.find({'guid':guid}).count(), 1)
        self.assertTrue(self.db.User.one({'guid':guid}))

        response = self.client.get('/bookmarklet/')
        self.assertTrue('external_url' not in response.body)

        data = {'external_url': 'http://www.peterbe.com/page',
                'use_current_url': 'yes',
                'title': '@donecal is da @bomb',
                'now':mktime(today.timetuple())}
        response = self.client.post('/bookmarklet/', data)
        self.assertTrue('Thank' in response.body)
        event = self.db.Event.one(dict(title=data['title']))
        self.assertEqual(event.tags, [u'donecal', u'bomb'])
        self.assertEqual(event.external_url, data['external_url'])

        data = {'external_url': 'http://www.peterbe.com/some/other/page',}
        response = self.client.get('/bookmarklet/', data)
        self.assertTrue('value="@donecal @bomb "' in response.body)


    def test_help_pages(self):
        # index
        response = self.client.get('/help/')
        self.assertEqual(response.code, 200)
        self.assertTrue('Help' in response.body)

        # about
        response = self.client.get('/help/About')
        self.assertEqual(response.code, 200)
        self.assertTrue('Peter Bengtsson' in response.body)

        response = self.client.get('/help/abOUt')
        self.assertEqual(response.code, 200)
        self.assertTrue('Peter Bengtsson' in response.body)

        # Bookmarklet
        response = self.client.get('/help/Bookmarklet')
        self.assertEqual(response.code, 200)
        self.assertTrue('Bookmarklet' in response.body)

        # API
        response = self.client.get('/help/API')
        self.assertEqual(response.code, 200)
        self.assertTrue('API' in response.body)

        # start using the app and the API page will be different
        today = datetime.date.today()
        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])

        response = self.client.get('/help/API')
        self.assertEqual(response.code, 200)
        self.assertTrue(guid in response.body)
        self.assertTrue(response.body.split('<body')[1].count('https://') == 0)

        # now log in as a wealthy premium user
        user = self.db.User()
        user.email = u"test@test.com"
        user.premium = True
        user.set_password('secret')
        user.save()

        data = dict(email=user.email, password="secret")
        response = self.client.post('/auth/login/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        cookie = 'user=%s;' % user_cookie
        response = self.client.get('/help/API')
        self.assertEqual(response.code, 200)
        self.assertTrue(response.body.count('https://') >= 1)


    def test_reset_password(self):
        # sign up first
        data = dict(email="peterbe@gmail.com",
                    password="secret",
                    first_name="Peter",
                    last_name="Bengtsson")
        response = self.client.post('/user/signup/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)

        data.pop('password')
        user = self.db.users.User.one(data)
        self.assertTrue(user)


        response = self.client.get('/user/forgotten/')
        self.assertEqual(response.code, 200)

        response = self.client.post('/user/forgotten/', dict(email="bogus"))
        self.assertEqual(response.code, 400)

        response = self.client.post('/user/forgotten/', dict(email="valid@email.com"))
        self.assertEqual(response.code, 200)
        self.assertTrue('Error' in response.body)
        self.assertTrue('valid@email.com' in response.body)

        response = self.client.post('/user/forgotten/', dict(email="PETERBE@gmail.com"))
        self.assertEqual(response.code, 200)
        self.assertTrue('success' in response.body)
        self.assertTrue('peterbe@gmail.com' in response.body)

        sent_email = mail.outbox[-1]
        self.assertTrue('peterbe@gmail.com' in sent_email.to)

        links = [x.strip() for x in sent_email.body.split()
                 if x.strip().startswith('http')]
        from urlparse import urlparse
        link = [x for x in links if x.count('recover')][0]
        # pretending to click the link in the email now
        url = urlparse(link).path
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        self.assertTrue('name="password"' in response.body)

        data = dict(password='secret')

        response = self.client.post(url, data, follow_redirects=False)
        self.assertEqual(response.code, 302)

        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(user.guid, guid)
        cookie = 'user=%s;' % user_cookie

        response = self.client.get('/auth/logged_in.json', headers={'Cookie': cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue("Peter" in response.body)
        struct = json.loads(response.body)
        self.assertEqual(struct['user_name'], 'Peter')

    def test_auth_logged_in_json(self):
        response = self.client.get('/auth/logged_in.json')
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct.keys(), ['xsrf'])

        data = dict(email="peterbe@gmail.com",
                    password="secret",
                    first_name="Peter",
                    last_name="Bengtsson")
        response = self.client.post('/user/signup/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)

        data.pop('password')
        user = self.db.users.User.one(data)
        self.assertTrue(user)

        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        cookie = 'user=%s;' % user_cookie

        response = self.client.get('/auth/logged_in.json')
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['user_name'], 'Peter')
        user.premium = True
        user.save()

        response = self.client.get('/auth/logged_in.json')
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['user_name'], 'Peter')
        self.assertEqual(struct['premium'], True)


    def test_undo_delete_event(self):
        """you can delete an event and then get it back by following the undo link"""
        today = datetime.date.today()

        data = {'title': "Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']

        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie

        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(self.db.User.find({'guid':guid}).count(), 1)
        user = self.db.User.one({'guid':guid})

        self.assertEqual(self.db.Event.find({'user.$id':user._id}).count(), 1)
        data['id'] = event_id
        response = self.client.post('/event/delete/', data)
        self.assertEqual(response.code, 200)
        self.assertEqual(self.db.Event.find({'user.$id':user._id}).count(), 0)

        # the delete will have created a new special user
        undoer_guid = self._app.settings['UNDOER_GUID']
        undoer = self.db.User.one(dict(guid=undoer_guid))
        self.assertEqual(self.db.Event.find({'user.$id': undoer._id}).count(), 1)

        # to undo you just need to hit a URL
        # but you can't do it without a cookie
        other_client = TestClient(self)
        response = other_client.post('/event/undodelete/', {'id': event_id})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('error'))

        response = self.client.post('/event/undodelete/', {'id': event_id})
        self.assertEqual(response.code, 200)
        self.assertEqual(self.db.Event.find({'user.$id': undoer._id}).count(), 0)
        self.assertEqual(self.db.Event.find({'user.$id':user._id}).count(), 1)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['title'], data['title'])

    def test_change_settings_without_logging_in(self):
        # without even posting something, change your settings
        assert not self.db.UserSettings.find().count()

        data = dict(disable_sound=True, monday_first=True)
        # special client side trick
        data['anchor'] = '#month,2010,11,1'

        response = self.client.post('/user/settings/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue(response.headers['Location'].endswith(data['anchor']))

        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])

        self.assertEqual(self.db.User.find({'guid':guid}).count(), 1)
        user = self.db.User.one({'guid':guid})
        self.assertEqual(self.db.UserSettings.find({'user':user._id}).count(), 1)

        # pick up the cookie and continue to the home page
        response = self.client.get(response.headers['Location'])
        self.assertEqual(response.code, 200)
        # the settings we just made will be encoded as a JSON string inside the HTML
        self.assertTrue('"monday_first": true' in response.body)


    def test_share_tag_and_rename_tag(self):
        """suppose one of your tags is 'Tag' and you have that shared with someone.
        If you then enter a new event with the tag 'tAG' it needs to rename the tag
        on the share too"""
        today = datetime.date.today()
        data = {'title': "Foo @Tag",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        event = self.db.Event.one()
        assert event.tags == [u'Tag']
        user = self.db.User.one()

        share = self.db.Share()
        share.user = user._id
        share.tags = event.tags
        share.save()

        self.assertTrue(self.db.Share.one(dict(tags=[u'Tag'])))

        # Post another one
        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        data = {'title': "@tAG New one",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data, headers={'Cookie': cookie})
        self.assertEqual(response.code, 200)
        assert self.db.Event.find().count() == 2
        self.assertEqual(self.db.Event.find(dict(tags=[u'tAG'])).count(), 2)

        self.assertTrue(self.db.Share.one(dict(tags=[u'tAG'])))


    def test_feature_requests(self):
        user = self.db.User()
        user.email = u'test@com.com'
        user.save()
        feature_request = self.db.FeatureRequest()
        feature_request.author = user._id
        feature_request.title = u"More cheese"
        feature_request.save()

        assert feature_request.vote_weight == 0

        comment = self.db.FeatureRequestComment()
        comment.comment = u""
        comment.user = user._id
        comment.feature_request = feature_request
        comment.save()

        feature_request.vote_weight += 1
        feature_request.save()

        url = '/features/'

        data = dict(title=u'')
        response = self.client.post(url, data)
        self.assertEqual(response.code, 400) # no title

        # the default placeholder text
        data['title'] = u"Add your own new feature request"
        response = self.client.post(url, data)
        self.assertEqual(response.code, 400)

        # already taken
        data['title'] = u"more cheese"
        response = self.client.post(url, data)
        self.assertEqual(response.code, 400)

        data['title'] = u"New title"
        data['description'] = u"\nwww.google.com\ntest "
        response = self.client.post(url, data)
        self.assertEqual(response.code, 403) # not logged in

        # because we're not logged in we don't get the entry form at all
        response = self.client.get(url)
        self.assertTrue('<input name="title"' not in response.body)

        me = self.db.User()
        me.email = u'peter@test.com'
        me.set_password('secret')
        me.first_name = u"Peter"
        me.save()

        response = self.client.post('/auth/login/',
                             dict(email=me.email, password="secret"),
                             follow_redirects=False)
        self.assertEqual(response.code, 302)
        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(me.guid, guid)
        cookie = 'user=%s;' % user_cookie

        response = self.client.get(url)
        self.assertTrue('<input name="title"' in response.body)

        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)
        self.assertEqual(self.db.FeatureRequestComment.find().count(), 2)

        response = self.client.get(url)
        self.assertTrue('Thanks!' in response.body)
        self.assertTrue('<a href="http://www.google.com">www.google.com</a>' \
          in response.body) # linkifyied

        # now ajax submit one more comment to the first feature request
        data = {'id':'feature--%s' % feature_request._id,
                'comment': u"\tSure thing "}
        client2 = TestClient(self)
        response = client2.post(url + 'vote/up/', data)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('error'))

        response = self.client.post(url + 'vote/up/', data)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('vote_weights'))

        response = self.client.get(url)
        self.assertTrue("\tSure thing" not in response.body) # stripped
        self.assertTrue("Sure thing" in response.body)

        vote_weight_before = self.db.FeatureRequest\
          .one({'_id': feature_request._id}).vote_weight
        data['comment'] = "More sure thing!"
        response = self.client.post(url + 'vote/up/', data)
        self.assertEqual(response.code, 200)

        vote_weight_after = self.db.FeatureRequest\
          .one({'_id': feature_request._id}).vote_weight

        self.assertEqual(vote_weight_before, vote_weight_after)

        # or you can render just one single item
        data = {'id': str(feature_request._id)}
        response = self.client.get(url + 'feature.html', data)
        self.assertEqual(response.code, 200)
        self.assertTrue("Added by Peter" in response.body)
        self.assertTrue("More sure thing" in response.body)
        self.assertTrue("More cheese" in response.body)
        self.assertTrue("Thanks!" in response.body)
        self.assertTrue("seconds ago" in response.body)

        # but don't fuck with the id
        data['id'] = '_' * 100
        response = self.client.get(url + 'feature.html', data)
        self.assertEqual(response.code, 404)
        data['id'] = ''
        response = self.client.get(url + 'feature.html', data)
        self.assertEqual(response.code, 400)

        data = dict(title="more cheese")
        response = self.client.get(url + 'find.json', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct['feature_requests'])

        data = dict(title="Uh??")
        response = self.client.get(url + 'find.json', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(not struct['feature_requests'])

    def test_new_feature_requests_sends_email(self):
        me = self.db.User()
        me.email = u'peter@test.com'
        me.set_password('secret')
        me.first_name = u"Peter"
        me.save()

        response = self.client.post('/auth/login/',
                             dict(email=me.email, password="secret"),
                             follow_redirects=False)
        self.assertEqual(response.code, 302)
        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(me.guid, guid)
        cookie = 'user=%s;' % user_cookie

        url = '/features/'
        data = dict(title=u'This is my feature request', description="Great!")
        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)
        self.assertEqual(self.db.FeatureRequest.find().count(), 1)
        self.assertEqual(self.db.FeatureRequestComment.find().count(), 1)

        sent_email = mail.outbox[-1]
        self.assertEqual(sent_email.from_email, self._app.settings['webmaster'])
        self.assertEqual(sent_email.to, self._app.settings['admin_emails'])
        self.assertTrue('New feature request' in sent_email.subject)
        self.assertTrue('Description: Great!' in sent_email.body)
        self.assertTrue(data['title'] in sent_email.body)
        self.assertTrue(me.email in sent_email.body)
        self.assertTrue(me.first_name in sent_email.body)


    def test_sorting_hours_spent_stats(self):
        today = datetime.date.today()
        data = {'title': "@Tag1 bla bl a",
                'date': mktime(today.timetuple()),
                'all_day': '0'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        user = self.db.User.one()

        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        data = {'title': "@Tag2 yesterday",
                'date': mktime(today.timetuple()) - 100,
                'all_day': '0'}
        response = self.client.post('/events/', data, headers={'Cookie': cookie})
        self.assertEqual(response.code, 200)

        self.assertTrue(self.db.Event.find().count(), 2)
        self.assertTrue(self.db.Event.find({'all_day': False}).count(), 2)

        response = self.client.get('/events/stats.json', headers={'Cookie': cookie})
        struct = json.loads(response.body)
        hours_spent = struct['hours_spent']
        min_hours = MINIMUM_DAY_SECONDS / float(60 * 60)

        self.assertTrue(["Tag1", min_hours] in hours_spent)
        self.assertTrue(["Tag2", min_hours] in hours_spent)

        event = self.db.Event.one(dict(tags=u"Tag2"))
        event.end += datetime.timedelta(hours=1)
        event.save()

        response = self.client.get('/events/stats.json', headers={'Cookie': cookie})
        struct = json.loads(response.body)
        hours_spent = struct['hours_spent']
        # they should be ordered by the tag
        self.assertEqual(hours_spent[0], ['Tag1', min_hours])
        self.assertEqual(hours_spent[1], ['Tag2', min_hours + 1.0])

        # add a third one without a tag
        data = {'title': "No tag here",
                'date': mktime(today.timetuple()) - 100,
                'all_day': '0'}
        response = self.client.post('/events/', data, headers={'Cookie': cookie})
        self.assertEqual(response.code, 200)


        event = self.db.Event.one(dict(tags=[]))
        event.end += datetime.timedelta(hours=2)
        event.save()

        response = self.client.get('/events/stats.json', headers={'Cookie': cookie})
        struct = json.loads(response.body)
        hours_spent = struct['hours_spent']
        self.assertEqual(hours_spent[0], ['<em>Untagged</em>', min_hours + 2])
        self.assertEqual(hours_spent[1], ['Tag1', min_hours])
        self.assertEqual(hours_spent[2], ['Tag2', min_hours + 1.0])

    def test_changing_tag_prefix(self):
        today = datetime.date.today()

        self.assertEqual(self.db.User.find().count(), 0)
        data = {'title': "@tag1 and #tag2 Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('event'))
        self.assertTrue(isinstance(struct['event'].get('start'), float))
        self.assertTrue(isinstance(struct['event'].get('end'), float))
        self.assertEqual(struct['event']['start'], struct['event']['end'])
        self.assertEqual(struct['event'].get('title'), data['title'])
        self.assertEqual(struct.get('tags'), [u'@tag1',u'@tag2'])

        guid_cookie = self.decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])

        # the user hasn't yet proven that he prefers all hash_tags so there
        # shouldn't exist any user settings yet
        self.assertTrue(not self.db.UserSettings.one())
        data = {'title': "#tag2 and #tag3 Bar", # clearly prefers '#' as prefix
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct.get('tags'), [u'#tag2',u'#tag3'])

        user_settings = self.db.UserSettings.one()

        self.assertTrue(user_settings.hash_tags)

        # get all events out including all tags and expect it to contain
        # ['#tag1', '#tag2']


        data = dict(start=mktime(today.timetuple()),
                    end=mktime((today + datetime.timedelta(days=1)).timetuple()))

        data['include_tags'] = 'yes'
        response = self.client.get('/events.json', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['tags'], ["#tag1", "#tag2", "#tag3"])

        # now change your mind again
        data = {'title': "@tag3 alone", # clearly prefers '#' as prefix
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.client.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct.get('tags'), [u'@tag3'])

        data = dict(start=mktime(today.timetuple()),
                    end=mktime((today + datetime.timedelta(days=1)).timetuple()))

        data['include_tags'] = 'yes'
        response = self.client.get('/events.json', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['tags'], ["@tag1", "@tag2", "@tag3"])

    def test_rendering_with_or_without_https(self):
        response = self.client.get('/auth/logged_in.json', headers={'X-Scheme':'https'},
                            follow_redirects=False)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct['redirect_to'])
        self.assertTrue(struct['redirect_to'].startswith('http://'))
        #self.assertTrue(response.headers['Location'].startswith('http://'))

        user = self.db.User()
        user.email = u"test@test.com"
        user.premium = True
        user.set_password('secret')
        user.save()

        data = dict(email=user.email, password="secret")
        response = self.client.post('/auth/login/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        cookie = 'user=%s;' % user_cookie
        guid = base64.b64decode(user_cookie.split('|')[0])
        user = self.db.User.one({'guid':guid})
        assert user.premium

        response = self.client.get('/auth/logged_in.json', headers={'Cookie':cookie, 'X-Scheme':'https'},
                            follow_redirects=False)
        self.assertEqual(response.code, 200)

        response = self.client.get('/auth/logged_in.json', follow_redirects=False)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct['redirect_to'])
        self.assertTrue(struct['redirect_to'].startswith('https://'))

    def test_getting_events_with_bad_parameters(self):
        # this is based on an actual error that happened
        # {'end': ['288000000'], 'include_tags': ['all'], 'start': ['-2736000000']}

        url = '/events.json'
        data = dict(start='-2736000000',
                    end='288000000',
                    include_tags='all')
        response = self.client.get(url, data)
        self.assertEqual(response.code, 400)

    def test_google_openid_callback(self):
        url = '/auth/openid/google/'
        import apps.main.handlers
        apps.main.handlers.GoogleAuthHandler.get_authenticated_user = \
          mocked_get_authenticated_user

        data = {
          u'openid.assoc_handle': u'AOQobUdw52vqgNiH0NJF10tdIDrfXFI_jsBPAPbFWg7tJ6ZLU6AI7agN',
          u'openid.claimed_id': u'https://www.google.com/accounts/o8/id?id=AItOawmwnMmHH-_LJoEdOiFnzx-3lMWX62MG5Zk',
          u'openid.ext1.mode': u'fetch_response',
          u'openid.ext1.type.email': u'http://axschema.org/contact/email',
          u'openid.ext1.type.firstname': u'http://axschema.org/namePerson/first',
          u'openid.ext1.type.language': u'http://axschema.org/pref/language',
          u'openid.ext1.type.lastname': u'http://axschema.org/namePerson/last',
          u'openid.ext1.value.email': u'huseyinin@gmail.com',
          u'openid.ext1.value.firstname': u'H\xc3\xbcseyin',
          u'openid.ext1.value.language': u'en',
          u'openid.ext1.value.lastname': u'Mert',
          u'openid.identity': u'https://www.google.com/accounts/o8/id?id=AItOawmwnMmHH-_LJoEdOiFnzx-3lMWX62MG5Zk',
          u'openid.mode': u'id_res',
          u'openid.ns': u'http://specs.openid.net/auth/2.0',
          u'openid.ns.ext1': u'http://openid.net/srv/ax/1.0',
          u'openid.op_endpoint': u'https://www.google.com/accounts/o8/ud',
          u'openid.response_nonce': u'2011-05-24T20:41:44ZBVg6KFBvv5VpgA',
          u'openid.return_to': u'http://donecal.com/auth/openid/google/',
          u'openid.sig': u'e1GxK6Rlw/qnT+tdEEbyNiiSu94=',
          u'openid.signed': u'op_endpoint,claimed_id,identity,return_to,response_nonce,assoc_handle,ns.ext1,ext1.mode,ext1.type.firstname,ext1.value.firstname,ext1.type.email,ext1.value.email,ext1.type.language,ext1.value.language,ext1.type.lastname,ext1.value.lastname'
        }
        response = self.client.get(url, data)
        self.assertEqual(response.code, 302)
        user_cookie = self.decode_cookie_value('user', response.headers['Set-Cookie'])
        cookie = 'user=%s;' % user_cookie
        guid = base64.b64decode(user_cookie.split('|')[0])
        user = self.db.User.one({'guid':guid})
        self.assertEqual(user.first_name, u'H\xc3\xbcseyin')

    def test_render_report_basic(self):
        url = self.reverse_url('report')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('Error' in response.body)
        self.assertTrue('need to be logged in' in response.body)

        user = self.db.User()
        user.email = u"test@test.com"
        user.set_password('secret')
        user.save()

        data = dict(email=user.email, password="secret")
        response = self.client.post('/auth/login/', data)
        self.assertEqual(response.code, 302)

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('Error' in response.body)
        self.assertTrue('until you have some events entered' in response.body)

        today = datetime.datetime.today()
        yesterday = today - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)

        event = self.db.Event()
        event.user = user
        event.title = u"Testing @at"
        event.all_day = True
        event.start = yesterday
        event.end = yesterday
        event.save()

        event = self.db.Event()
        event.user = user
        event.title = u"Tomorrow"
        event.all_day = True
        event.start = tomorrow
        event.end = tomorrow
        event.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('Error' not in response.body)

    def test_report_export(self):
        url = self.reverse_url('report_export', '.xls')
        response = self.client.get(url)
        self.assertEqual(response.code, 403)

        user = self.db.User()
        user.email = u"test@test.com"
        user.set_password('secret')
        user.save()

        data = dict(email=user.email, password="secret")
        response = self.client.post('/auth/login/', data)
        self.assertEqual(response.code, 302)

        # create some events
        today = datetime.datetime.today()
        tomorrow = today + datetime.timedelta(days=1)
        yesterday = today - datetime.timedelta(days=1)
        event1 = self.db.Event()
        event1.user = user
        event1.title = u"Testing @at"
        event1.all_day = True
        event1.start = yesterday
        event1.end = yesterday
        event1.save()

        event2 = self.db.Event()
        event2.user = user
        event2.title = u"Tomorrow"
        event2.all_day = True
        event2.start = tomorrow
        event2.end = tomorrow
        event2.save()

        event3 = self.db.Event()
        event3.user = user
        event3.title = u"Long Time Ago"
        event3.all_day = True
        event3.start = yesterday - datetime.timedelta(days=2)
        event3.end = yesterday - datetime.timedelta(days=2)
        event3.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 400)

        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        data = {
          'start': mktime(yesterday.timetuple()),
          'end': mktime((tomorrow + datetime.timedelta(days=1)).timetuple()),
        }
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-type'],
                         'application/vnd.ms-excel; charset=UTF-8')

        url = self.reverse_url('report_export', '.csv')
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-type'],
                         'application/msexcel-comma; charset=UTF-8')
        self.assertTrue(event1.title in response.body)
        self.assertTrue(event2.title in response.body)
        self.assertTrue(event3.title not in response.body)

    def test_report_data(self):
        url = self.reverse_url('report_data', '.json')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        user = self._login()

        # create some events
        today = datetime.datetime.today()
        tomorrow = today + datetime.timedelta(days=1)
        yesterday = today - datetime.timedelta(days=1)
        event1 = self.db.Event()
        event1.user = user
        event1.title = u"Testing @at"
        event1.all_day = True
        event1.start = yesterday
        event1.end = yesterday
        event1.save()

        event2 = self.db.Event()
        event2.user = user
        event2.title = u"Tomorrow #Boston"
        event2.tags = [u'Boston']
        event2.all_day = True
        event2.start = tomorrow
        event2.end = tomorrow
        event2.save()

        event3 = self.db.Event()
        event3.user = user
        event3.title = u"Long Time Ago"
        event3.all_day = True
        event3.start = yesterday - datetime.timedelta(days=2)
        event3.end = yesterday - datetime.timedelta(days=2)
        event3.save()

        event4 = self.db.Event()
        event4.user = user
        event4.title = u"Long Time Ago @washington"
        event4.tags = [u'washington']
        event4.all_day = False
        event4.start = datetime.datetime.now()
        event4.end = datetime.datetime.now() + datetime.timedelta(hours=1)
        event4.save()

        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        data = {
#          'start': mktime(yesterday.timetuple()),
#          'end': mktime((tomorrow + datetime.timedelta(days=1)).timetuple()),
        }
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-type'],
                         'application/json; charset=UTF-8')
        struct = json.loads(response.body)
        self.assertEqual(struct['hours_spent'], [['washington', 1.0]])
        self.assertEqual(struct['days_spent'], [
          ['<em>Untagged</em>', 2.0],
          ['Boston', 1.0],
        ])

        data['start'] = mktime(today.timetuple())
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['days_spent'], [
          ['Boston', 1.0],
        ])

        data['end'] = mktime(tomorrow.timetuple())
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['days_spent'], [])
        self.assertEqual(struct['hours_spent'], [['washington', 1.0]])

        data['with_colors'] = 'yes'
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct['hours_colors'])
        self.assertTrue(not struct['days_colors'])

        data['interval'] = '1 week'
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['ticks'], [1])
        self.assertEqual(struct['data'], [[1.0], [0]])
        self.assertEqual(struct['tags'],
                         ['washington', '<em>Untagged</em>'])

        del data['interval']
        url = self.reverse_url('report_data', '.js')
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-type'],
                         'text/javascript; charset=UTF-8')

        url = self.reverse_url('report_data', '.xml')
        del data['with_colors']
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-type'],
                         'text/xml; charset=UTF-8')

        url = self.reverse_url('report_data', '.txt')
        response = self.client.get(url, data)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-type'],
                         'text/plain; charset=UTF-8')
        self.assertTrue('washington' in response.body)

        del data['start']
        response = self.client.get(url, data)
        self.assertTrue('*Untagged*' in response.body)

    def test_get_user_settings_javascript(self):
        url = self.reverse_url('user_settings', '.js')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-type'],
                         'text/javascript; charset=UTF-8')
        self.assertTrue('"ampm_format": false' in response.body)

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('"ampm_format": false' in response.body)

        user_settings, = self.db.UserSettings.find()
        user_settings.ampm_format = True
        user_settings.save()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('"ampm_format": true' in response.body)

    def test_share_key_not_found(self):
        url = self.reverse_url('share_key', 'junk')
        response = self.client.get(url)
        self.assertEqual(response.code, 404)
        # same if you're logged in
        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 404)

        user, = self.db.User.find()
        share = self.db.Share()
        share.user = user._id
        share.save()
        assert share.key

        url = self.reverse_url('share_key', share.key)
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.client.cookies.get('shares') is None)
        # log in as someone else and use the same URL
        self._login(email=u'other@person.com')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.client.cookies.get('shares') is not None)
        shares_cookie = self.client.cookies.get('shares').value
        self.assertEqual(base64.b64decode(shares_cookie.split('|')[0]),
                         share.key)


import mock_data
def mocked_get_authenticated_user(self, callback):
    callback(mock_data.MOCK_GOOGLE_USER)
