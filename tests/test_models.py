from bson import DBRef
import datetime
#import sys; sys.path.insert(0, '..')
import unittest
from models import User, Event, UserSettings, Share

class ModelsTestCase(unittest.TestCase):
    _once = False
    def setUp(self):
        if not self._once:
            self._once = True
            from mongokit import Connection
            con = Connection()
            con.register([User, Event, UserSettings, Share])
            self.db = con.test
            self._emptyCollections()
            
    def _emptyCollections(self):
        [self.db.drop_collection(x) for x 
         in self.db.collection_names() 
         if x not in ('system.indexes',)]
        
    def tearDown(self):
        self._emptyCollections()
        
    def test_create_user(self):
        user = self.db.users.User()
        assert user.guid
        assert user.add_date
        assert user.modify_date
        user.save()
        
        inst = self.db.users.User.one()
        assert inst.guid
        from utils import encrypt_password
        inst.password = encrypt_password('secret')
        inst.save()
        
        self.assertFalse(inst.check_password('Secret'))
        self.assertTrue(inst.check_password('secret'))
        
    def test_create_event(self):
        user = self.db.users.User()
        user.save()
        event = self.db.events.Event()
        event.user = user#DBRef('users', user['_id'])
        event.title = u"Test"
        event.all_day = True
        event.start = datetime.datetime.today()
        event.end = datetime.datetime.today()
        event.validate()
        event.save()
        
        self.assertEqual(self.db.events.Event.find().count(), 1)
        event = self.db.events.Event.one()
        
        assert self.db.events.Event.find({"user.$id":event.user._id}).count() == 1
        
        
    def test_user_settings(self):
        user = self.db.users.User()
        settings = self.db.user_settings.UserSettings()
        from mongokit import RequireFieldError
        self.assertRaises(RequireFieldError, settings.save)
        settings.user = user
        settings.save()
        
        self.assertFalse(settings.monday_first)
        self.assertFalse(settings.hide_weekend)
        
        model = self.db.user_settings.UserSettings
        self.assertEqual(model.find({'user.$id': user._id}).count(), 1)
        
    def test_create_share(self):
        user = self.db.users.User()
        share = self.db.shares.Share()
        share.user = user
        share.save()
        
        self.assertEqual(share.tags, [])
        
        new_key = Share.generate_new_key(self.db.shares, min_length=4)
        self.assertTrue(len(new_key) == 4)
        share.key = new_key
        share.save()
        
        self.assertTrue(self.db.shares.Share.one(dict(key=new_key)))
        
        
        