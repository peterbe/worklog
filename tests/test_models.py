import datetime
#import sys; sys.path.insert(0, '..')
import unittest
from models import User, Event, UserSettings

class ModelsTestCase(unittest.TestCase):
    _once = False
    def setUp(self):
        if not self._once:
            self._once = True
            from mongokit import Connection
            con = Connection()
            con.register([User, Event, UserSettings])
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
        
    def test_create_event(self):
        user = self.db.users.User()
        event = self.db.events.Event()
        event.user = user
        event.title = u"Test"
        event.all_day = True
        event.start = datetime.datetime.today()
        event.end = datetime.datetime.today()
        event.save()
        
        self.assertEqual(self.db.events.Event.find().count(), 1)
        event = self.db.events.Event.one()
        
        assert self.db.events.Event.find({"user.$id":event.user._id}).count() == 1
        
        
    def test_user_settings(self):
        user = self.db.users.User()
        settings = self.db.users.UserSettings()
        from mongokit import RequireFieldError
        self.assertRaises(RequireFieldError, settings.save)
        settings.user = user
        settings.save()
        
        self.assertFalse(settings.monday_first)
        self.assertFalse(settings.hide_weekend)
        
        