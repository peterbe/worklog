from hashlib import md5
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
    
class UserSettings(BaseDocument):
    structure = {
      'user': User,
      'monday_first': bool,
      'hide_weekend': bool,
    }
    use_autorefs = True
    
    required_fields = ['user']
    default_values = {
      'monday_first': False,
      'hide_weekend': False,
    }
    
    indexes = [
      {'fields': 'user',
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
    
class Share(BaseDocument):
    structure = {
      'user': User,
      'key': unicode,
      'tags': [unicode],
      'users': [User],
    }
    default_values = {
      'key': lambda:unicode(md5(unicode(uuid.uuid4())).hexdigest()),
    }
    
    use_autorefs = True
    required_fields = ['user']

    indexes = [
      {'fields': ['user']},
      {'fields': ['key'], 'unique': True},
    ]
    
    @classmethod
    def generate_new_key(cls, collection, min_length=6):
        new_key = unicode(md5(unicode(uuid.uuid4())).hexdigest()[:min_length])
        while collection.Share.find(dict(key=new_key)).count():
            new_key = unicode(md5(unicode(uuid.uuid4())).hexdigest()[:min_length])
        return new_key
        
        
        
        
    
      