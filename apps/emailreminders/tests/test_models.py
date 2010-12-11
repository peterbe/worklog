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
        
    def test_create_email_reminder_with_invalid_data(self):
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
        
    def test_setting_next_send_date(self):
        user = self.db.User()
        
        now = datetime.datetime.utcnow()
        # assuming English locale for running tests
        assert now.strftime('%A') in EmailReminder.WEEKDAYS
        tomorrow = now + datetime.timedelta(days=1)
        email_reminder = self.db.EmailReminder()
        email_reminder.user = user
        email_reminder.time = (12, 30)
        email_reminder.weekdays = [unicode(tomorrow.strftime('%A'))]
        email_reminder.tz_offset = -5
        email_reminder.set_next_send_date()
        
        # this is easy because the next send date is simply tomorrow plus 5 hours
        expect = datetime.datetime(tomorrow.year, 
                                   tomorrow.month,
                                   tomorrow.day,
                                   12+5,
                                   30)#tomorrow - datetime.timedelta(days=1)
        #print email_reminder._next_send_date
        #print expect
        self.assertEqual(email_reminder._next_send_date.strftime('%Y%m%d%H%M'),
                         expect.strftime('%Y%m%d%H%M'))

        # The method email_reminder.set_next_send_date() makes it possible to
        # override what date is "now". This is useful if you want to force it to
        # think today is something else.
        before = email_reminder._next_send_date
        email_reminder.set_next_send_date(email_reminder._next_send_date)
        self.assertTrue(before + datetime.timedelta(days=7), email_reminder._next_send_date)
        self.assertEqual([email_reminder._next_send_date.strftime('%A')],
                         email_reminder.weekdays) 
        
    def test_setting_next_send_date_harder(self):
        user = self.db.User()
        
        now = datetime.datetime.utcnow()
        # assuming English locale for running tests
        assert now.strftime('%A') in EmailReminder.WEEKDAYS
        tomorrow = now + datetime.timedelta(days=1)
        email_reminder = self.db.EmailReminder()
        email_reminder.user = user
        email_reminder.time = (2, 30)
        email_reminder.weekdays = [unicode(tomorrow.strftime('%A'))]
        email_reminder.tz_offset = -5.5
        email_reminder.validate()
        
        email_reminder.set_next_send_date()
        # Tomorrow at 02.30 local time at - 5.5h means Today at 8:00
        
        expect = datetime.datetime(tomorrow.year, 
                                   tomorrow.month,
                                   tomorrow.day,
                                   8, 0, 0)
        
        self.assertEqual(email_reminder._next_send_date.strftime('%Y/%m/%d %H:%M'),
                         expect.strftime('%Y/%m/%d %H:%M'))

    def test_setting_next_send_date_harder2(self):
        user = self.db.User()
        
        now = datetime.datetime.utcnow()
        # assuming English locale for running tests
        assert now.strftime('%A') in EmailReminder.WEEKDAYS
        tomorrow = now + datetime.timedelta(days=1)
        email_reminder = self.db.EmailReminder()
        email_reminder.user = user
        email_reminder.time = (22, 30)
        email_reminder.weekdays = [unicode(tomorrow.strftime('%A'))]
        email_reminder.tz_offset = 5
        email_reminder.validate()
        
        email_reminder.set_next_send_date()
        # Tomorrow at 02.30 local time at -5h means Today at 21:30
        
        expect = datetime.datetime(tomorrow.year, 
                                   tomorrow.month,
                                   tomorrow.day,
                                   17, 30, 0)
        assert expect.strftime('%d%A') == (now + datetime.timedelta(days=1)).strftime('%d%A')
        
        self.assertEqual(email_reminder._next_send_date.strftime('%Y%m%d%H%M'),
                         expect.strftime('%Y%m%d%H%M'))
                         
        