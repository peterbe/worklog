import uuid
import datetime
from mongokit import Document

class BaseDocument(Document):
    structure = {
      'add_date': datetime.datetime,
      'modify_date': datetime.datetime,
    }
    
    default_values = {
      'add_date': datetime.datetime.now,
      'modify_date': datetime.datetime.now
    }
    
    use_dot_notation = True
    
class User(BaseDocument):
    structure = {
      'guid': unicode,
      'username': unicode,
      'email': unicode,
      'password': unicode,
      'first_name': unicode,
      'last_name': unicode,
    }
    
    required_fields = ['guid']
    default_values = {
      'guid': lambda:unicode(uuid.uuid4()),
    }
    
    indexes = [
      {'fields': 'guid',
       'unique': True},
    ]

class Event(BaseDocument):
    structure = {
      'user': User,
      'title': unicode,
      'all_day': bool,
      'start': datetime.datetime,
      'end': datetime.datetime,
      'tags': [unicode],
      'url': unicode,
    }
    use_autorefs = True
    required_fields = ['user', 'title', 'all_day', 'start', 'end']

    indexes = [
      {'fields': ['user', 'start', 'end']},
    ]    
    
class Test:
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
        #from mongokit import DBRef
        #from pymongo.dbref import DBRef as pDBRef
        #print repr(DBRef), repr(pDBRef)
        #user_ref = DBRef('users', user['_id'])
        #print repr(user_ref)
        #assert self.db.events.Event.find({'user': user_ref}).count() == 1
        
        
        
    
#if __name__ == '__main__':
    