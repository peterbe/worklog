from mongokit import RequireFieldError, ValidationError
import datetime
#import sys; sys.path.insert(0, '..')
import unittest
from apps.emailreminders.models import EmailReminder
from apps.main.tests.base import BaseModelsTestCase

class ModelsTestCase(BaseModelsTestCase):
    def setUp(self):
        super(ModelsTestCase, self).setUp()
        self.db.connection.register([EmailReminder])
        
    
    def test_create_email_reminder(self):
        user = self.db.User()
        
        email_reminder = self.db.EmailReminder()
        email_reminder.user = user
        email_reminder.time = (12, 30)
        email_reminder.tz_offset = -5
        email_reminder.validate()
        email_reminder.save()
        
        self.assertEqual(email_reminder.weekdays,
          [EmailReminder.MONDAY,
           EmailReminder.TUESDAY,
           EmailReminder.WEDNESDAY,
           EmailReminder.THURSDAY,
           EmailReminder.FRIDAY]
        )
        
    def test_creat_email_reminder_with_invalid_data(self):
        user = self.db.User()
        email_reminder = self.db.EmailReminder()
        self.assertRaises(ValidationError, email_reminder.validate)
        email_reminder.user = user
        self.assertRaises(ValidationError, email_reminder.validate)
        email_reminder.time = (25, 30)
        self.assertRaises(ValidationError, email_reminder.validate)
        email_reminder.time = (23, 60)
        self.assertRaises(ValidationError, email_reminder.validate)
        email_reminder.time = (0, -10)
        self.assertRaises(ValidationError, email_reminder.validate)
        email_reminder.time = (-1, 10)
        self.assertRaises(ValidationError, email_reminder.validate)
        email_reminder.time = (16, 00)
        email_reminder.weekdays = [u"something", u"else"]
        self.assertRaises(ValidationError, email_reminder.validate)
        email_reminder.weekdays = [EmailReminder.MONDAY, EmailReminder.TUESDAY]
        email_reminder.tz_offset = 100
        self.assertRaises(ValidationError, email_reminder.validate)
        email_reminder.tz_offset = 2
        email_reminder.validate()
        
        