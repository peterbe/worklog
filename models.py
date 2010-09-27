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
    
