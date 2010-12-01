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
        response = self.post('/events/', data)
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
        response = self.post('/events/', data, headers={'Cookie':cookie})
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
        response = self.post('/events/', data, headers={'Cookie':cookie})
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
        response = self.post('/events/', data, headers={'Cookie':cookie})
        
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
        response = self.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        event_id = struct['event']['id']
        
        event_obj = db.Event.one(dict(title="Foo"))
        event_user = event_obj.user
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
        response = self.post('/event/move/', data, headers={'Cookie':cookie})
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
        response = self.post('/event/resize/', data, headers={'Cookie':cookie})
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
        response = self.post('/event/resize/', data, headers={'Cookie':cookie})
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
        response = self.post('/event/edit/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['title'], data['title'])
        self.assertTrue('description' not in struct['event'])
        self.assertTrue(db.Event.one({'title':'New title'}))

        data['description'] = '\nA longer description\n'
        response = self.post('/event/edit/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['description'], data['description'].strip())
        self.assertTrue(db.Event.one({'description': data['description'].strip()}))
        
        # edit URL (wrong)
        data = {'id': event_id,
                'title': 'New title',
                'external_url': 'junk'}
        response = self.post('/event/edit/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 400)
        # edit URL (right)
        data['external_url'] = 'http://www.peterbe.com'
        response = self.post('/event/edit/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['external_url'], data['external_url'])
        
        # delete
        data = {'id': '___'}
        response = self.post('/event/delete/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 404)
        
        data['id'] = event_id
        response = self.post('/event/delete/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        
        search = {'user.$id': event_user._id}
        self.assertTrue(not db.Event.find(search).count())
        
        
    def test_getting_event_for_edit_json(self):
        db = self.get_db()
        today = datetime.datetime.today()
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data)
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
        response = self.post('/events/', data)
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
        response = self.post('/events/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        
        response = self.get('/events/stats.json', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct.get('hours_spent'), [['tagged', 1.0]])
        
        data = {'title': "Foo3 @tagged",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data, headers={'Cookie':cookie})
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
        response = self.post('/events/', data)
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
        response = self.post('/events/', data)
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
        response = self.get('/event/?id=%s' % event_id, headers={'Cookie':cookie})
        self.assertEqual(response.code, 403)
        
        # user2 needs to create a share
        user3 = db.User()
        user3.email = u"else@test.com"
        user3.save()
        
        self.assertTrue(db.User.one({'guid':guid}))
        
        share = db.Share()
        share.user = user2
        share.users = [user3]
        share.save()
        
        response = self.get('/?share=%s' % share.key, headers={'Cookie':cookie},
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        shares_cookie = self._decode_cookie_value('shares', response.headers['Set-Cookie'])
        
        cookie += ';shares=%s' % shares_cookie
        response = self.get('/event/?id=%s' % event_id, headers={'Cookie':cookie})
        # shared but not shared with this user
        
        self.assertEqual(response.code, 403)
        
        share.users = []
        share.save()
        
        response = self.get('/event/', {'id': event_id}, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
    
    def test_sharing_with_yourself(self):
        """test using the share on yourself"""
        db = self.get_db()
        # post one yourself first so that you become someone
        today = datetime.datetime.today()
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        #event_id = struct['event']['id']
        
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])

        user = db.User.one()
        self.assertEqual(user.guid, guid)
        user.email = u'test@peterbe.com'
        user.save()
        
        share = db.Share()
        share.user = user
        share.key = u'foo'
        share.save()
        
        # use it yourself
        response = self.get('/?share=%s' % share.key, headers={'Cookie':cookie},
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue('Set-Cookie' not in response.headers) # because no cookie is set
        #shares_cookie = self._decode_cookie_value('shares', response.headers['Set-Cookie'])
        
        user2 = db.User()
        user2.email = u'one@two.com'
        user2.save()
        
        share2 = db.Share()
        share2.user = user2
        share2.key = u'foo2'
        share2.save()
        
        response = self.get('/?share=%s' % share2.key, headers={'Cookie':cookie},
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        #self.assertTrue('Set-Cookie' not in response.headers) # because no cookie is set
        shares_cookie = self._decode_cookie_value('shares', response.headers['Set-Cookie'])
        cookie += 'shares=%s;' % shares_cookie
        shares = base64.b64decode(shares_cookie.split('|')[0])
        self.assertEqual(shares, 'foo2')
        
        user3 = db.User()
        user3.email = u'ass@three.com'
        user3.save()
        
        share3 = db.Share()
        share3.user = user3
        share3.key = u'foo3'
        share3.save()
        
        response = self.get('/?share=%s' % share3.key, headers={'Cookie':cookie},
                            follow_redirects=False)
        self.assertEqual(response.code, 302)
        shares_cookie = self._decode_cookie_value('shares', response.headers['Set-Cookie'])
        shares = base64.b64decode(shares_cookie.split('|')[0])
        self.assertEqual(shares, 'foo2,foo3')
        
        
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
        self.assertEqual(struct, dict(events=[]))

        data['include_tags'] = 'yes'
        response = self.get(url, data)
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
        event.tags = [u"tag1"]
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
        response = self.get('/events.json', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['events'][0]['title'], event.title)
        self.assertTrue('tags' not in struct)
        
        data['include_tags'] = 'yes'
        response = self.get('/events.json', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        #self.assertEqual(struct['tags'], [u"@tag1"])
        self.assertEqual(struct['tags'], [])

        event2 = db.Event()
        event2.user = user
        event2.title = u"Title 2"
        event2.start = datetime.datetime(2010,10, 14)
        event2.end = datetime.datetime(2010,10, 14)
        event2.all_day = True
        event2.tags = [u"tag2"]
        event2.save()
        
        share.tags = [u'tag2']
        share.save()
        
        response = self.get('/events.json', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['events'][0]['title'], event2.title)
        
        

        
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
        
        data = {'title': "@tag1 @tag2 Foo",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data)
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
        url = re.findall('value="http(.*)"', response.body)[0]
        key = re.findall('share=(.*)', url)[0]
        share = db.Share.one(dict(key=key))
        self.assertTrue(share)
        self.assertEqual(share.user, user)
        
        data = {'id': str(share._id), 'tags':'tag2'}
        response = self.post('/share/edit/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        share = db.Share.one(dict(_id=share._id))
        self.assertEqual(share.tags, [u'tag2'])
        
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

    def test_bookmarklet_with_cookie(self):
        db = self.get_db()
        today = datetime.date.today()
        
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data)
        self.assertEqual(response.code, 200) 
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(db.User.find({'guid':guid}).count(), 1)
        user = db.User.one({'guid':guid})
        
        response = self.get('/bookmarklet/', headers={'Cookie':cookie})
        self.assertTrue('external_url' not in response.body)

        data = {'external_url': 'http://www.peterbe.com/page'}
        response = self.get('/bookmarklet/', data, headers={'Cookie':cookie})
        self.assertTrue('value="%s"' % data['external_url'] in response.body)

        # post something now
        # ...but fail first
        data = dict()
        response = self.post('/bookmarklet/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, "'now' not sent. Javascript must be enabled")
        
        future = datetime.datetime.now() + datetime.timedelta(hours=2)
        data = dict(now=mktime(future.timetuple()))
        response = self.post('/bookmarklet/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue('Error: No title entered' in response.body)
        
        data['title'] = u" Saving the day "
        response = self.post('/bookmarklet/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue('Thanks!' in response.body)
        
        event = db.Event.one({'title':data['title'].strip(),
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
        response = self.post('/bookmarklet/', data, headers={'Cookie':cookie})
        event = db.Event.one({'user.$id':user._id, 
                              'title': re.compile('^now')})

        self.assertTrue(event.title.endswith('...'))
        self.assertTrue(len(event.title) < len(event.description))
        self.assertEqual(event.description, data['description'])
        self.assertEqual(event.tags, [])
        
        # try again, writing on multiple lines
        data['description'] = 'Line one\nLine two\nLine three'
        response = self.post('/bookmarklet/', data, headers={'Cookie':cookie})
        event = db.Event.one({'user.$id':user._id, 
                              'title': re.compile('^Line')})
        self.assertEqual(event.title, u"Line one")
        self.assertEqual(event.description, u"Line two\nLine three")
        
        # one more time when the description is short
        data['description'] = "@mytag one word"
        response = self.post('/bookmarklet/', data, headers={'Cookie':cookie})
        event = db.Event.one({'user.$id':user._id,
                              'title': data['description']})
        self.assertEqual(event.description, u"")
        self.assertEqual(event.tags, [u'mytag'])
        
        # try making it a half hour event
        data['length'] = '0.5'
        data['title'] = "half hour event"
        data['description'] = ''
        data['now'] = mktime(future.timetuple())
        response = self.post('/bookmarklet/', data, headers={'Cookie':cookie})
        event = db.Event.one({'user.$id':user._id,
                              'title': data['title']})
        diff_seconds = (event.end - event.start).seconds
        self.assertEqual(diff_seconds, 60 * 30)
        self.assertTrue(not event.all_day)
        
        
    def test_bookmarklet_with_cookie_with_suggested_tags(self):
        db = self.get_db()
        today = datetime.date.today()
        
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data)
        self.assertEqual(response.code, 200) 
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(db.User.find({'guid':guid}).count(), 1)
        self.assertTrue(db.User.one({'guid':guid}))
        
        response = self.get('/bookmarklet/', headers={'Cookie':cookie})
        self.assertTrue('external_url' not in response.body)

        data = {'external_url': 'http://www.peterbe.com/page',
                'use_current_url': 'yes',
                'title': '@donecal is da @bomb',
                'now':mktime(today.timetuple())}
        response = self.post('/bookmarklet/', data, headers={'Cookie':cookie})
        self.assertTrue('Thank' in response.body)
        event = db.Event.one(dict(title=data['title']))
        self.assertEqual(event.tags, [u'donecal', u'bomb'])
        self.assertEqual(event.external_url, data['external_url'])
        
        data = {'external_url': 'http://www.peterbe.com/some/other/page',}
        response = self.get('/bookmarklet/', data, headers={'Cookie':cookie})
        self.assertTrue('value="@donecal @bomb "' in response.body)
        
        
    def test_help_pages(self):
        # index
        response = self.get('/help/')
        self.assertEqual(response.code, 200)
        self.assertTrue('Help' in response.body)
        
        # about
        response = self.get('/help/About')
        self.assertEqual(response.code, 200)
        self.assertTrue('Peter Bengtsson' in response.body)
        
        response = self.get('/help/abOUt')
        self.assertEqual(response.code, 200)
        self.assertTrue('Peter Bengtsson' in response.body)        

        # Bookmarklet
        response = self.get('/help/Bookmarklet')
        self.assertEqual(response.code, 200)
        self.assertTrue('Bookmarklet' in response.body)
        
        # API
        response = self.get('/help/API')
        self.assertEqual(response.code, 200)
        self.assertTrue('API' in response.body)
        
        # start using the app and the API page will be different
        today = datetime.date.today()
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data)
        self.assertEqual(response.code, 200) 
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        
        response = self.get('/help/API', headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue(guid in response.body)
        
    def test_reset_password(self):
        # sign up first
        data = dict(email="peterbe@gmail.com", 
                    password="secret",
                    first_name="Peter",
                    last_name="Bengtsson")
        response = self.post('/user/signup/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        
        data.pop('password')
        user = self.get_db().users.User.one(data)
        self.assertTrue(user)
        
        
        response = self.get('/user/forgotten/')
        self.assertEqual(response.code, 200)
        
        response = self.post('/user/forgotten/', dict(email="bogus"))
        self.assertEqual(response.code, 400)

        response = self.post('/user/forgotten/', dict(email="valid@email.com"))
        self.assertEqual(response.code, 200)
        self.assertTrue('Error' in response.body)
        self.assertTrue('valid@email.com' in response.body)
        
        response = self.post('/user/forgotten/', dict(email="PETERBE@gmail.com"))
        self.assertEqual(response.code, 200)
        self.assertTrue('success' in response.body)
        self.assertTrue('peterbe@gmail.com' in response.body)
        
        sent_email = mail.outbox[0]
        self.assertTrue('peterbe@gmail.com' in sent_email.to)
        
        links = [x.strip() for x in sent_email.body.split() 
                 if x.strip().startswith('http')]
        from urlparse import urlparse
        link = [x for x in links if x.count('recover')][0]
        # pretending to click the link in the email now
        url = urlparse(link).path
        response = self.get(url)
        self.assertEqual(response.code, 200)

        self.assertTrue('name="password"' in response.body)
        
        data = dict(password='secret')
        
        response = self.post(url, data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        
        user_cookie = self._decode_cookie_value('user', response.headers['Set-Cookie'])
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(user.guid, guid)
        cookie = 'user=%s;' % user_cookie
        
        response = self.get('/', headers={'Cookie': cookie})
        self.assertTrue("Peter" in response.body)
        
        
        
    def test_undo_delete_event(self):
        """you can delete an event and then get it back by following the undo link"""
        
        db = self.get_db()
        today = datetime.date.today()
        
        data = {'title': "Foo", 
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data)
        self.assertEqual(response.code, 200) 
        struct = json.loads(response.body)
        event_id = struct['event']['id']
        
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        
        guid = base64.b64decode(guid_cookie.split('|')[0])
        self.assertEqual(db.User.find({'guid':guid}).count(), 1)
        user = db.User.one({'guid':guid})
        
        self.assertEqual(db.Event.find({'user.$id':user._id}).count(), 1)
        data['id'] = event_id
        response = self.post('/event/delete/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertEqual(db.Event.find({'user.$id':user._id}).count(), 0)
        
        # the delete will have created a new special user
        undoer_guid = self._app.settings['UNDOER_GUID']
        undoer = db.User.one(dict(guid=undoer_guid))
        self.assertEqual(db.Event.find({'user.$id': undoer._id}).count(), 1)
        
        # to undo you just need to hit a URL
        response = self.post('/event/undodelete/', {'id': event_id})
        # but you can't do it without a cookie
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('error'))
        
        response = self.post('/event/undodelete/', {'id': event_id}, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertEqual(db.Event.find({'user.$id': undoer._id}).count(), 0)
        self.assertEqual(db.Event.find({'user.$id':user._id}).count(), 1)
        struct = json.loads(response.body)
        self.assertEqual(struct['event']['title'], data['title'])
        
    def test_change_settings_without_logging_in(self):
        # without even posting something, change your settings
        db = self.get_db()
        assert not db.UserSettings.find().count()
        
        data = dict(disable_sound=True, monday_first=True)
        # special client side trick
        data['anchor'] = '#month,2010,11,1'
        
        response = self.post('/user/settings/', data, follow_redirects=False)
        self.assertEqual(response.code, 302)
        self.assertTrue(response.headers['Location'].endswith(data['anchor']))

        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        guid = base64.b64decode(guid_cookie.split('|')[0])
        
        self.assertEqual(db.User.find({'guid':guid}).count(), 1)
        user = db.User.one({'guid':guid})
        self.assertEqual(db.UserSettings.find({'user.$id':user._id}).count(), 1)
        
        # pick up the cookie and continue to the home page
        response = self.get(response.headers['Location'], headers={'Cookie': cookie})
        self.assertEqual(response.code, 200)
        # the settings we just made will be encoded as a JSON string inside the HTML
        self.assertTrue('"monday_first": true' in response.body)
        
        
    def test_share_tag_and_rename_tag(self):
        """suppose one of your tags is 'Tag' and you have that shared with someone.
        If you then enter a new event with the tag 'tAG' it needs to rename the tag 
        on the share too"""
        
        db = self.get_db()
        today = datetime.date.today()
        data = {'title': "Foo @Tag",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data)
        self.assertEqual(response.code, 200)
        event = db.Event.one()
        assert event.tags == [u'Tag']
        user = db.User.one()
        
        share = db.Share()
        share.user = user
        share.tags = event.tags
        share.save()
        
        self.assertTrue(db.Share.one(dict(tags=[u'Tag'])))
        
        # Post another one
        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        data = {'title': "@tAG New one",
                'date': mktime(today.timetuple()),
                'all_day': 'yes'}
        response = self.post('/events/', data, headers={'Cookie': cookie})
        self.assertEqual(response.code, 200)
        assert db.Event.find().count() == 2
        self.assertEqual(db.Event.find(dict(tags=[u'tAG'])).count(), 2)
        
        self.assertTrue(db.Share.one(dict(tags=[u'tAG'])))
        
        
    def test_feature_requests(self):
        db = self.get_db()
        
        user = db.User()
        user.email = u'test@com.com'
        user.save()
        feature_request = db.FeatureRequest()
        feature_request.author = user
        feature_request.title = u"More cheese"
        feature_request.save()
        
        assert feature_request.vote_weight == 0
        
        comment = db.FeatureRequestComment()
        comment.comment = u""
        comment.user = user
        comment.feature_request = feature_request
        comment.save()
        
        feature_request.vote_weight += 1
        feature_request.save()

        url = '/features/'
        
        data = dict(title=u'')
        response = self.post(url, data)
        self.assertEqual(response.code, 404) # no title
        
        # the default placeholder text
        data['title'] = u"Add your own new feature request"
        response = self.post(url, data)
        self.assertEqual(response.code, 400)
        
        # already taken
        data['title'] = u"more cheese"
        response = self.post(url, data)
        self.assertEqual(response.code, 400)
        
        data['title'] = u"New title"
        data['description'] = u"\nwww.google.com\ntest "
        response = self.post(url, data)
        self.assertEqual(response.code, 403) # not logged in
        
        # because we're not logged in we don't get the entry form at all
        response = self.get(url)
        self.assertTrue('<input name="title"' not in response.body)
        
        me = db.User()
        me.email = u'peter@test.com'
        me.set_password('secret')
        me.first_name = u"Peter"
        me.save()
        
        response = self.post('/auth/login/', 
                             dict(email=me.email, password="secret"),
                             follow_redirects=False)
        self.assertEqual(response.code, 302)
        user_cookie = self._decode_cookie_value('user', response.headers['Set-Cookie'])
        guid = base64.b64decode(user_cookie.split('|')[0])
        self.assertEqual(me.guid, guid)
        cookie = 'user=%s;' % user_cookie
        
        response = self.get(url, headers={'Cookie':cookie})
        self.assertTrue('<input name="title"' in response.body)

        response = self.post(url, data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertEqual(db.FeatureRequestComment.find().count(), 2)
        
        response = self.get(url, headers={'Cookie':cookie})
        self.assertTrue('Thanks!' in response.body)
        self.assertTrue('<a href="http://www.google.com">www.google.com</a>' \
          in response.body) # linkifyied
        
        # now ajax submit one more comment to the first feature request
        
        data = {'id':'feature--%s' % feature_request._id,
                'comment': u"\tSure thing "}
        response = self.post(url + 'vote/up/', data)
        struct = json.loads(response.body)
        self.assertTrue(struct.get('error'))
        
        response = self.post(url + 'vote/up/', data, headers={'Cookie':cookie})
        struct = json.loads(response.body)
        self.assertTrue(struct.get('vote_weights'))
        
        response = self.get(url, headers={'Cookie':cookie})
        self.assertTrue("\tSure thing" not in response.body) # stripped
        self.assertTrue("Sure thing" in response.body)
        
        vote_weight_before = db.FeatureRequest\
          .one({'_id': feature_request._id}).vote_weight
        data['comment'] = "More sure thing!"
        response = self.post(url + 'vote/up/', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        
        vote_weight_after = db.FeatureRequest\
          .one({'_id': feature_request._id}).vote_weight
          
        self.assertEqual(vote_weight_before, vote_weight_after)
        
        # or you can render just one single item
        data = {'id': str(feature_request._id)}
        response = self.get(url + 'feature.html', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 200)
        self.assertTrue("Added by Peter" in response.body)
        self.assertTrue("More sure thing" in response.body)
        self.assertTrue("More cheese" in response.body)
        self.assertTrue("Thanks!" in response.body)
        self.assertTrue("seconds ago" in response.body)
        
        # but don't fuck with the id
        data['id'] = '_' * 100
        response = self.get(url + 'feature.html', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 404)
        data['id'] = ''
        response = self.get(url + 'feature.html', data, headers={'Cookie':cookie})
        self.assertEqual(response.code, 404)
        
        data = dict(title="more cheese")
        response = self.get(url + 'find.json', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct['feature_requests'])
        
        data = dict(title="Uh??")
        response = self.get(url + 'find.json', data)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(not struct['feature_requests'])
        
        
    def test_sorting_hours_spent_stats(self):
        
        db = self.get_db()
        today = datetime.date.today()
        data = {'title': "@Tag1 bla bl a",
                'date': mktime(today.timetuple()),
                'all_day': '0'}
        response = self.post('/events/', data)
        self.assertEqual(response.code, 200)
        user = db.User.one()

        guid_cookie = self._decode_cookie_value('guid', response.headers['Set-Cookie'])
        cookie = 'guid=%s;' % guid_cookie
        data = {'title': "@Tag2 yesterday",
                'date': mktime(today.timetuple()) - 100,
                'all_day': '0'}
        response = self.post('/events/', data, headers={'Cookie': cookie})
        self.assertEqual(response.code, 200)
        
        self.assertTrue(db.Event.find().count(), 2)
        self.assertTrue(db.Event.find({'all_day': False}).count(), 2)
        
        response = self.get('/events/stats.json', headers={'Cookie': cookie})
        struct = json.loads(response.body)
        hours_spent = struct['hours_spent']
        self.assertTrue(["Tag1", 1.0] in hours_spent)
        self.assertTrue(["Tag2", 1.0] in hours_spent)
        
        event = db.Event.one(dict(tags=u"Tag2"))
        event.end += datetime.timedelta(hours=1)
        event.save()
        
        response = self.get('/events/stats.json', headers={'Cookie': cookie})
        struct = json.loads(response.body)
        hours_spent = struct['hours_spent']
        # they should be ordered by the tag
        self.assertEqual(hours_spent[0], ['Tag1', 1.0])
        self.assertEqual(hours_spent[1], ['Tag2', 2.0])
        
        # add a third one without a tag
        data = {'title': "No tag here",
                'date': mktime(today.timetuple()) - 100,
                'all_day': '0'}
        response = self.post('/events/', data, headers={'Cookie': cookie})
        self.assertEqual(response.code, 200)
        
        
        event = db.Event.one(dict(tags=[]))
        event.end += datetime.timedelta(hours=2)
        event.save()
        
        response = self.get('/events/stats.json', headers={'Cookie': cookie})
        struct = json.loads(response.body)
        hours_spent = struct['hours_spent']
        self.assertEqual(hours_spent[0], ['<em>Untagged</em>', 3.0])
        self.assertEqual(hours_spent[1], ['Tag1', 1.0])
        self.assertEqual(hours_spent[2], ['Tag2', 2.0])

            
        
        
        
        