from hashlib import md5
import uuid
import datetime
from mongokit import Document, ValidationError
from utils import encrypt_password

class BaseDocument(Document):
    structure = {
      'add_date': datetime.datetime,
      'modify_date': datetime.datetime,
    }

    default_values = {
      'add_date': datetime.datetime.now,
      'modify_date': datetime.datetime.now
    }
    use_autorefs = True
    use_dot_notation = True

class User(BaseDocument):
    __collection__ = 'users'
    structure = {
      'guid': unicode,
      'username': unicode,
      'email': unicode,
      'password': unicode,
      'first_name': unicode,
      'last_name': unicode,
      'premium': bool,
    }

    use_autorefs = True
    required_fields = ['guid']
    default_values = {
      'guid': lambda:unicode(uuid.uuid4()),
      'premium': False,
    }

    #indexes = [
    #  {'fields': 'guid',
    #   'unique': True},
    #]

    def set_password(self, raw_password):
        self.password = encrypt_password(raw_password)

    def check_password(self, raw_password):
        """
        Returns a boolean of whether the raw_password was correct. Handles
        encryption formats behind the scenes.
        """
        if '$bcrypt$' in self.password:
            import bcrypt
            hashed = self.password.split('$bcrypt$')[-1].encode('utf8')
            return hashed == bcrypt.hashpw(raw_password, hashed)
        else:
            raise NotImplementedError("No checking clear text passwords")

class UserSettings(BaseDocument):
    __collection__ = 'user_settings'
    structure = {
      'user': User,
      'monday_first': bool,
      'hide_weekend': bool,
      'disable_sound': bool,
      'offline_mode': bool,
      'hash_tags': bool, # whether to use #tagg instead of @tagg
      'ampm_format': bool,
      'first_hour': int,
      'newsletter_opt_out': bool,
    }
    use_autorefs = True

    required_fields = ['user']
    default_values = {
      'monday_first': False,
      'hide_weekend': False,
      'disable_sound': False,
      'offline_mode': False,
      'hash_tags': False,
      'newsletter_opt_out': False,
      'first_hour': 8,
    }

    validators = {
      'first_hour': lambda x: 0 <= int(x) < 24
    }

    #indexes = [
    #  {'fields': 'user.$id',
    #   'check': False,
    #   'unique': True},
    #]

    @staticmethod
    def get_bool_keys():
        return [key for (key, value)
                in UserSettings.structure.items()
                if value is bool]


class Event(BaseDocument):
    __collection__ = 'events'
    structure = {
      'user': User,
      'title': unicode,
      'all_day': bool,
      'start': datetime.datetime,
      'end': datetime.datetime,
      'tags': [unicode],
      'external_url': unicode,
      'description': unicode,
    }
    use_autorefs = True
    required_fields = ['user', 'title', 'all_day', 'start', 'end']

    #indexes = [
    #  {'fields': ['user.$id', 'start', 'end'], 'check':False},
    #]

    validators = {
      'title': lambda x: x.strip()
    }

    def validate(self, *args, **kwargs):
        if self['end'] < self['start']:
            raise ValidationError("end must be greater than start")
        super(Event, self).validate(*args, **kwargs)

    def chown(self, user, save=False):
        self.user = user
        if save:
            self.save()

class Share(BaseDocument):
    __collection__ = 'shares'
    structure = {
      'user': User,
      'key': unicode,
      'tags': [unicode],
      'users': [User],
    }
    default_values = {
      'key': lambda:unicode(md5(unicode(uuid.uuid4())).hexdigest()),
    }

    required_fields = ['user']

    #indexes = [
    #  {'fields': ['user.$id'], 'check':False},
    #  {'fields': ['key'], 'unique': True},
    #]

    @classmethod
    def generate_new_key(cls, collection, min_length=6):
        new_key = unicode(md5(unicode(uuid.uuid4())).hexdigest()[:min_length])
        while collection.Share.find(dict(key=new_key)).count():
            new_key = unicode(md5(unicode(uuid.uuid4())).hexdigest()[:min_length])
        return new_key

class FeatureRequest(BaseDocument):
      __collection__ = 'feature_requests'
      structure = {
        'title': unicode,
        'description': unicode,
        'vote_weight': int,
        'description_format': unicode,
        'response': unicode,
        'response_format': unicode,
        'author': User,
        'implemented': bool,
      }

      required_fields = [
        'author',
      ]

      default_values = {
        'vote_weight': 0,
        'description_format': u'plaintext',
        'response_format': u'markdown',
        'implemented': False,
      }



class FeatureRequestComment(BaseDocument):
    __collection__ = 'feature_request_comments'
    structure = {
      'feature_request': FeatureRequest,
      'user': User,
      'comment': unicode,
      'vote_weight': int,
    }

    required_fields = [
      'vote_weight',
    ]
    default_values = {
      'vote_weight': 1,
    }
