from apps.main.tests.base import BaseHTTPTestCase, TestClient

class LoginError(Exception):
    pass


class EmailRemindersTestCase(BaseHTTPTestCase):
    
    def setUp(self):
        super(EmailRemindersTestCase, self).setUp()
        self.client = TestClient(self)#self.get_app())
    
    def test_setting_up_reminders(self):
        db = self.get_db()
        url = '/emailreminders/'
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        
        # go straight into setting up an email reminder
        peter = db.User()
        peter.email = u'peter@test.com'
        peter.set_password('secret')
        peter.save()
        self.client.login('peter@test.com', 'secret')
        
        from apps.emailreminders.models import EmailReminder
        data = dict(weekdays=[EmailReminder.MONDAY, 
                              EmailReminder.WEDNESDAY],
                    time_hour=13,
                    time_minute=str(0),
                    tz_offset='-3',
                    )
        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)
        
        email_reminder = db.EmailReminder.one()
        self.assertEqual(email_reminder.user._id, peter._id)
        self.assertEqual(email_reminder.weekdays, [EmailReminder.MONDAY, 
                                                   EmailReminder.WEDNESDAY])
        self.assertEqual(email_reminder.time, [13,0])
        self.assertEqual(email_reminder.tz_offset, -3)
        
        edit_url = "?edit=%s" % email_reminder._id
        
        # reload the page again and expect to see something about this reminder
        # in there
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue(edit_url in response.body)
        
        
        
        