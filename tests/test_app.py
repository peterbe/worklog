import base64
import unittest
from time import mktime, time
import re
import datetime
from mongokit import Connection
import simplejson as json
from tornado.web import RequestHandler, _O

#import app
from base import BaseHTTPTestCase
from utils import encrypt_password
from models import Event, User

        
class ApplicationTestCase(BaseHTTPTestCase):
    
    def _decode_cookie_value(self, key, cookie_value):
        try:
            return re.findall('%s=([\w=\|]+);' % key, cookie_value)[0]
        except IndexError:
            raise ValueError("couldn't find %r in %r" % (key, cookie_value))
    
    def test_homepage(self):
        response = self.get('/')
        self.assertTrue('id="calendar"' in response.body)
        
    def test_posting_events(self):
        db = self.get_db()
        today = datetime.date.today()
        
        self.assertEqual(db.User.find().count(), 0)
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('event'))
        self.assertTrue(isinstance(struct['event'].get('start'), float))
        self.assertTrue(isinstance(struct['event'].get('end'), float))
        self.assertEqual(struct['event']['start'], struct['event']['end'])
        self.assertEqual(struct['event'].get('title'), 'Foo')
        self.assertEqual(struct.get('tags'), [])
        
        self.assertEqual(db.Event.find().count(), 1)
        event = db.Event.one()
        self.assertTrue(isinstance(event.start, datetime.datetime))
        
        first_of_this_month = datetime.datetime(today.year, today.month, 1)
        if today.month == 12:
            last_of_this_month = datetime.datetime(today.year + 1, 1, 1)
        else:
            last_of_this_month = datetime.datetime(today.year, today.month + 1, 1)
        last_of_this_month -= datetime.timedelta(days=1)
        
        self.assertEqual(db.Event.find({
          'start':{'$gte':first_of_this_month},
          'end':{'$lte': last_of_this_month}
          }).count(),
          1)
        self.assertEqual(db.User.find().count(), 1)
        
        
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(db.User.find({'guid':guid}).count(), 1)
        
        # with a tag this time
        data = {'title': "@fryit Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data, headers={'Cookie':cookie})
        struct = json.loads(response.body)
        self.assertTrue(struct.get('event'))
        self.assertEqual(struct.get('tags'), ['@fryit'])
        
        self.assertEqual(db.Event.find({
          'tags':'fryit'
        }).count(), 1)

        self.assertEqual(db.User.find().count(), 1)
        
        # change your preference for case on the fryit tag
        data = {'title': "@FryIT working on @Italy",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data, headers={'Cookie':cookie})
        struct = json.loads(response.body)
        self.assertTrue(struct.get('event'))
        self.assertEqual(struct.get('tags'), ['@Italy', '@FryIT'])
        
        self.assertEqual(db.User.find().count(), 1)
        
        self.assertEqual(db.Event.find({
          'tags':'FryIT'
        }).count(), 2)
        
        # Post with another tag that is contained in one of the existing ones
        data = {'title': "@It Experiment",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data, headers={'Cookie':cookie})
        
        self.assertEqual(db.User.find().count(), 1)
        # change the other ones from before
        self.assertEqual(db.Event.find({
          'tags':'FryIT'
        }).count(), 2)
        
        self.assertEqual(db.Event.find({
          'tags':'It'
        }).count(), 1)
        
    def test_editing_event(self):
        db = self.get_db()
        today = datetime.datetime.today()
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']
        
        event_obj = db.Event.one(dict(title="Foo"))
        self.assertTrue(event_obj.all_day)
        
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(db.User.find({'guid':guid}).count(), 1)
        
        # move it 
        data = {'id': event_id,
                'all_day': 'true', # still
                'days': '-1',
                'minutes': 0}
        response = self.post('/event/move', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        new_start = struct['event']['start']
        self.assertEqual(new_start, struct['event']['end'])
        new_start = datetime.datetime.fromtimestamp(new_start)
        self.assertEqual((today - new_start).days, 1)

        event_obj = db.Event.one(dict(title="Foo"))
        self.assertTrue(event_obj.all_day)
        
        # resize it
        data = {'id': event_id,
                'all_day': '',
                'days': '3',
                'minutes': 0}
        response = self.post('/event/resize', data, headers={'Cookie':cookie})
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
        response = self.post('/event/resize', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('error'))
        
        # render the edit template
        data = {'id': event_id}
        #response = self.get('/event.html', headers={'Cookie':cookie})
        #self.assertEqual(response.code, 404)
        #response = self.get('/event/edit', data, headers={'Cookie':cookie})
        #self.assertEqual(response.code, 200)
        #self.assertTrue('value="Foo"' in response.body)
        
        # edit title
        data['title'] = 'New title'
        response = self.post('/event/edit', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['title'], data['title'])
        self.assertTrue('description' not in struct['event'])
        self.assertTrue(db.Event.one({'title':'New title'}))

        data['description'] = '\nA longer description\n'
        response = self.post('/event/edit', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['description'], data['description'].strip())
        self.assertTrue(db.Event.one({'description': data['description'].strip()}))
        
        # edit URL (wrong)
        data = {'id': event_id,
                'title': 'New title',
                'external_url': 'junk'}
        response = self.post('/event/edit', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 400)
        # edit URL (right)
        data['external_url'] = 'http://www.peterbe.com'
        response = self.post('/event/edit', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['external_url'], data['external_url'])
        
        # delete
        data = {'id': '___'}
        response = self.post('/event/delete', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 404)
        
        data['id'] = event_id
        response = self.post('/event/delete', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        
        self.assertTrue(not db.Event.find().count())
        
    def test_getting_event_for_edit_json(self):
        db = self.get_db()
        today = datetime.datetime.today()
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']
        
        event_obj = db.Event.one(dict(title="Foo"))
        self.assertTrue(event_obj.all_day)
        
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(db.User.find({'guid':guid}).count(), 1)
        
        url = '/event.json'
        response = self.get(url, dict(id=event_id))
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('error'))
        
        response = self.get(url, dict(id=event_id), headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct.get('title'), data['title'])
        self.assertTrue('description' not in struct)
        
        event_obj.description = u"A description"
        event_obj.save()
        
        response = self.get(url, dict(id=event_id), headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['description'], event_obj.description)
        
    def test_get_event_stats(self):
        db = self.get_db()
        today = datetime.date.today()
        
        response = self.get('/events/stats.json')
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct,
          {'hours_spent': [], 'days_spent': []})
        
        self.assertEqual(db.User.find().count(), 0)
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data)
        self.assertEqual(response.code, 200)
        
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        
        response = self.get('/events/stats.json', headers={'Cookie':cookie})
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
        response = self.post('/events', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        
        response = self.get('/events/stats.json', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct.get('hours_spent'), [['tagged', 1.0]])
        
        data = {'title': "Foo3 @tagged",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        event = db.Event.one(dict(title=data['title']))
        event.end += datetime.timedelta(days=2)
        event.save()
        
        response = self.get('/events/stats.json', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        days_spent = struct['days_spent']
        self.assertEqual(len(days_spent), 2)
        numbers = [x[1] for x in days_spent]
        self.assertEqual(numbers, [1.0, 3.])
        
        response = self.get('/events/stats.txt', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue('*Untagged*' in response.body)
        self.assertEqual(response.body.count('1.0'), 2)
        self.assertEqual(response.body.count('3.0'), 1)
                
        
    def test_previewing_posted_events(self):
        db = self.get_db()
        today = datetime.date.today()
        
        self.assertEqual(db.User.find().count(), 0)
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']
        
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(db.User.find({'guid':guid}).count(), 1)
        
        response = self.get('/event?id=%s' % event_id)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('error')) # not logged in
        
        response = self.get('/event.html?id=%s' % event_id, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue(data['title'] in response.body)
        self.assertTrue("by peter" not in response.body.lower())
        self.assertTrue("added seconds ago" in response.body.lower())
        
        event = db.Event.one(dict(title=data['title']))
        event.add_date -= datetime.timedelta(minutes=3)
        event.save()
        
        user = db.User.one({'guid':guid})
        user.email = u"peter@fry-it.com"
        user.save()
        
        response = self.get('/event.html?id=%s' % event_id, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue(data['title'] in response.body)
        self.assertTrue("peter@fry-it.com" in response.body)
        self.assertTrue("Added 3 minutes ago" in response.body)

        user.first_name = u"Peter"
        user.save()
        
        self.assertTrue("Peter" not in response.body)
        response = self.get('/event.html?id=%s' % event_id, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue("by Peter" in response.body)
        
        response = self.get('/event.html?id=______' , headers={'Cookie':cookie})
        self.assertEqual(response.code, 404)
        
        
    def test_previewing_shared_event(self):
        db = self.get_db()
        # post one yourself first so that you become someone
        today = datetime.datetime.today()
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']
        
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        
        # try to preview someone else's event
        user2 = db.User()
        user2.email = u"ashley@test.com"
        user2.save()
        
        event = db.Event()
        event.user = user2
        event.title = u"Testing @at"
        event.all_day = True
        event.start = datetime.datetime.today()
        event.end = datetime.datetime.today()
        event.save()
        event_id = str(event._id)
        
        
        # you can't view this one yet
        response = self.get('/event?id=%s' % event_id, headers={'Cookie':cookie})
        self.assertEqual(response.code, 403)
        
        # user2 needs to create a share
        user3 = db.User()
        user3.email = u"else@test.com"
        user3.save()
        
        user = db.User.one({'guid':guid})
        
        share = db.Share()
        share.user = user2
        share.users = [user3]
        share.save()
        
        response = self.get('/?share=%s' % share.key, headers={'Cookie':cookie},
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        shares_cookie = self._decode_cookie_value('shares', response.headers['Set-Cookie'])
        
        cookie += ';shares=%s' % shares_cookie
        response = self.get('/event?id=%s' % event_id, headers={'Cookie':cookie})
        # shared but not shared with this user
        
        self.assertEqual(response.code, 403)
        
        share.users = []
        share.save()
        
        response = self.get('/event?id=%s' % event_id, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        
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
        
    def test_view_shared_calendar(self):
        db = self.get_db()
        
        user = db.User()
        user.email = u"peter@fry-it.com"
        user.save()
        
        event = db.Event()
        event.user = user
        event.title = u"Title"
        event.start = datetime.datetime(2010,10, 13)
        event.end = datetime.datetime(2010,10, 13)
        event.all_day = True
        event.tags = [u"tag"]
        event.save()
        
        share = db.Share()
        share.user = user
        share.save()
        
        url = '/?share=%s' % share.key
        response = self.get(url, follow_redirects=False)
        self.assertEqual(response.code, 302)
        shares_cookie = self._decode_cookie_value('shares', response.headers['Set-Cookie'])
        cookie = 'shares=%s;' % shares_cookie
        data = dict(start=mktime(datetime.datetime(2010,10,1).timetuple()),
                    end=mktime(datetime.datetime(2010,10,30).timetuple()))
        response = self.get('/events.json', data, headers={'Cookie':cookie, 'A':"A"})
        
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['events'][0]['title'], event.title)
        self.assertEqual(struct['tags'], [u"@tag"])

        
    def test_user_settings(self):
        response = self.get('/user/settings/')
        self.assertEqual(response.code, 200)
        # nothing is checked
        self.assertTrue(not response.body.count('checked'))
        self.assertTrue('name="hide_weekend"' in response.body)
        self.assertTrue('name="monday_first"' in response.body)
        self.assertTrue('name="disable_sound"' in response.body)

        response = self.get('/user/settings.js')
        self.assertEqual(response.code, 200)
        json_str = re.findall('{.*?}', response.body)[0]
        settings = json.loads(json_str)
        self.assertEqual(settings['hide_weekend'], False)
        self.assertEqual(settings['monday_first'], False)
        
        data = {'hide_weekend':True,
                'disable_sound':True}
        response = self.post('/user/settings/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        guid = base64.b64decode(guid_cookie.split('|')[0])
       
        db = self.get_db()
        user = db.User.one(dict(guid=guid))
        user_settings = db.UserSettings.one({
          'user.$id': user._id
        })
        self.assertTrue(user_settings.hide_weekend)
        self.assertTrue(user_settings.disable_sound)
        self.assertFalse(user_settings.monday_first)
        
    
    def test_share_calendar(self):
        response = self.get('/share/')
        self.assertEqual(response.code, 200)
        self.assertTrue("don't have anything" in response.body)
        
        db = self.get_db()
        today = datetime.date.today()
        
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events', data)
        self.assertEqual(response.code, 200)
        
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])

        response = self.get('/share/', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue("can't share yet" in response.body.lower())
        
        user = db.User.one(dict(guid=guid))
        user.first_name = u"peter"
        user.save()
        
        response = self.get('/share/', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        
        # expect there to be a full URL in the HTML
        url = re.findall('value="(.*)"', response.body)[0]
        key = re.findall('share=(.*)', url)[0]
        share = db.Share.one(dict(key=key))
        self.assertTrue(share)
        self.assertEqual(share.user, user)
        
        # so a new user can start using this
        response = self.get('/', dict(share=key), follow_redirects=False)
        self.assertEqual(response.code, 302)
        shares_cookie = self._decode_cookie_value('shares', response.headers['Set-Cookie'])
        cookie = 'shares=%s;' % shares_cookie
        
        # I can now toggle this share to be hidden
        response = self.post('/share/', dict(), headers={'Cookie': cookie})
        self.assertEqual(response.code, 404)
        
        response = self.post('/share/', dict(key='bullshit'), headers={'Cookie': cookie})
        self.assertEqual(response.code, 404)
        
        response = self.post('/share/', dict(key=key), headers={'Cookie': cookie})
        self.assertEqual(response.code, 200)
        hidden_shares_cookie = self._decode_cookie_value('hidden_shares', response.headers['Set-Cookie'])
        hidden_shares = base64.b64decode(hidden_shares_cookie.split('|')[0])
        
        self.assertEqual(hidden_shares, key)
        cookie += response.headers['Set-Cookie']
        response = self.get('/', headers={'Cookie': cookie})
        # a setting for 'hidden_shares' is going to appear in the rendered HTML
        self.assertTrue('hidden_shares' in response.body)
        # so will the share key
        self.assertTrue(share.key in response.body)
        
        
    def test_signup(self):
        # the get method is just used to validate if an email is used another 
        # user
        response = self.get('/user/signup/')
        self.assertEqual(response.code, 404)
        
        data = {'validate_email': 'peter@test.com'}
        response = self.get('/user/signup/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, dict(ok=True))
        
        user = self.get_db().users.User()
        user.email = u"Peter@Test.com"
        user.save()
        
        data = {'validate_email': 'peter@test.com'}
        response = self.get('/user/signup/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct, dict(error='taken'))
        
        data = dict(email="peterbe@gmail.com", 
                    password="secret",
                    first_name="Peter",
                    last_name="Bengtsson")
        response = self.post('/user/signup/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        
        data.pop('password')
        user = self.get_db().users.User.one(data)
        self.assertTrue(user)
        
        # a secure cookie would have been set containing the user id
        user_cookie = self._decode_cookie_value('user', response.headers['Set-Cookie'])
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(user.guid, guid)

    def test_change_account(self):
        db = self.get_db()
        
        user = db.User()
        user.email = u"peter@fry-it.com"
        user.first_name = u"Ptr"
        user.password = encrypt_password(u"secret")
        user.save()
        
        other_user = db.User()
        other_user.email = u'peterbe@gmail.com'
        other_user.save()
        
        data = dict(email=user.email, password="secret")
        response = self.post('/auth/login/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        user_cookie = self._decode_cookie_value('user', response.headers['Set-Cookie'])
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(user.guid, guid)
        cookie = 'user=%s;' % user_cookie
        
        response = self.get('/user/account/', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue('value="Ptr"' in response.body)
        
        # not logged in
        response = self.post('/user/account/', {})
        self.assertEqual(response.code, 403)
        
        # no email supplied
        response = self.post('/user/account/', {}, headers={'Cookie':cookie})
        self.assertEqual(response.code, 404)
        
        data = {'email':'bob'}
        response = self.post('/user/account/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 400)

        data = {'email':'PETERBE@gmail.com'}
        response = self.post('/user/account/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 400)
        
        data = {'email':'bob@test.com', 'last_name': '  Last Name \n'}
        response = self.post('/user/account/', data, headers={'Cookie':cookie}, 
                             follow_redirects=False)
        self.assertEqual(response.code, 302)
        
        user = db.User.one(dict(email='bob@test.com'))
        self.assertEqual(user.last_name, data['last_name'].strip())
        
        # log out
        response = self.get('/auth/logout/', headers={'Cookie':cookie}, 
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue('user=;' in response.headers['Set-Cookie'])
        self.assertTrue('guid=;' in response.headers['Set-Cookie'])
        self.assertTrue('shares=;' in response.headers['Set-Cookie'])
        self.assertTrue('hidden_shares=;' in response.headers['Set-Cookie'])
        
        

        