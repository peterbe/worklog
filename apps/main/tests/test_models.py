from mongokit import RequireFieldError, ValidationError
import datetime
#import sys; sys.path.insert(0, '..')
from base import BaseModelsTestCase

class ModelsTestCase(BaseModelsTestCase):
    
    def test_create_user(self):
        user = self.db.User()
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
        event.user = user
        event.title = u"Test"
        event.all_day = True
        event.start = datetime.datetime.today()
        event.end = datetime.datetime.today()
        event.validate()
        event.save()
        
        self.assertEqual(self.db.events.Event.find().count(), 1)
        event = self.db.events.Event.one()
        
        assert self.db.events.Event.find({"user.$id":event.user._id}).count() == 1
    
    def test_create_event_wrongly(self):
        user = self.db.users.User()
        user.save()
        event = self.db.events.Event()
        event.user = user
        event.title = u"Test"
        event.all_day = True
        event.start = datetime.datetime.today() + datetime.timedelta(seconds=1)
        event.end = datetime.datetime.today()
        self.assertRaises(ValidationError, event.validate)
        self.assertRaises(ValidationError, event.save)
        
        # but it can be equal
        event.start = datetime.datetime.today()
        event.end = datetime.datetime.today()
        event.validate()
        event.save()
        
    def test_user_settings(self):
        user = self.db.User()
        settings = self.db.UserSettings()
        
        self.assertRaises(RequireFieldError, settings.save)
        settings.user = user
        settings.save()
        
        self.assertFalse(settings.monday_first)
        self.assertFalse(settings.hide_weekend)
        
        model = self.db.UserSettings
        self.assertEqual(model.find({'user.$id': user._id}).count(), 1)
        
    def test_create_share(self):
        user = self.db.User()
        share = self.db.Share()
        share.user = user
        share.save()
        
        self.assertEqual(share.tags, [])
        
        new_key = Share.generate_new_key(self.db[Share.__collection__], min_length=4)
        self.assertTrue(len(new_key) == 4)
        share.key = new_key
        share.save()
        
        self.assertTrue(self.db.Share.one(dict(key=new_key)))
        
    def test_create_feature_request(self):
        user = self.db.User()
        user.email = u'test@dot.com'
        user.save()
        
        feature_request = self.db.FeatureRequest()
        feature_request.author = user
        #self.assertRaises(RequireFieldError, feature_request.save)
        #feature_request.description = u"Bla bla"
        feature_request.save()
        
        frc = self.db.FeatureRequestComment()
        frc.feature_request = feature_request
        frc.save()
        self.assertEqual(frc.vote_weight, 1)
        
        
        