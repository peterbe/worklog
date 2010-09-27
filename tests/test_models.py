import datetime
#import sys; sys.path.insert(0, '..')
import unittest
from models import User, Event

class ModelsTestCase(unittest.TestCase):
    _once = False
    def setUp(self):
        if not self._once:
            from mongokit import Connection
            con = Connection()
            con.register([User, Event])
            self.db = con.test
        
    def tearDown(self):
        [self.db.drop_collection(x) for x 
         in self.db.collection_names() 
         if x not in ('system.indexes',)]
        
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
        
        assert self.db.events.Event.find().count() == 1
        event = self.db.events.Event.one()
        
        assert self.db.events.Event.find({"user.$id":event.user._id}).count() == 1