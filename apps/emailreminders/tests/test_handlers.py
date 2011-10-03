import os
import re
from time import mktime
import datetime
from apps.main.tests.base import BaseHTTPTestCase
from utils.http_test_client import TestClient
from utils import format_time_ampm
import utils.send_mail as mail

class LoginError(Exception):
    pass


class EmailRemindersTestCase(BaseHTTPTestCase):

    def setUp(self):
        super(EmailRemindersTestCase, self).setUp()
        self.client = TestClient(self)

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
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        assert 'peter@test.com' in response.body

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
        self.assertEqual(email_reminder.weekdays,
                         [EmailReminder.MONDAY, EmailReminder.WEDNESDAY])
        self.assertEqual(email_reminder.time, [13,0])
        self.assertEqual(email_reminder.tz_offset, -3)
        edit_url = "?edit=%s" % email_reminder._id

        # reload the page again and expect to see something about this reminder
        # in there
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue(edit_url in response.body)

    def test_simple_client_get(self):
        bob = self.db.User()
        bob.email = u'Bob@Builder.com'
        bob.set_password('secret')
        bob.save()
        self.client.login(bob.email, 'secret')
        url = '/emailreminders/'
        response = self.client.get(url)
        assert response.code == 200
        self.assertTrue(bob.email in response.body)

    def test_editing_setup_reminder(self):
        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.set_password('secret')
        bob.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (10,0)
        email_reminder.tz_offset = -5.5
        email_reminder.save()

        url = '/emailreminders/?edit=%s' % email_reminder._id
        response = self.client.get(url)
        self.assertEqual(response.code, 403) # because you're not logged in
        self.client.login(bob.email, 'secret')

        url = '/emailreminders/?edit=%s' % email_reminder._id
        response = self.client.get(url)
        self.assertEqual(response.code, 200) # because you *are* logged in

        bad_url = '/emailreminders/?edit=%s' % ('_' * 100)
        response = self.client.get(bad_url)
        self.assertEqual(response.code, 400) # invalid id

        bad_url = '/emailreminders/?edit=%s' % \
          str(email_reminder._id).replace('0','1')
        #print "*"*100
        #print
        #print bad_url
        response = self.client.get(bad_url)
        self.assertEqual(response.code, 404) # valid but not found

        greg = db.User()
        greg.email = u'greg@Builder.com'
        greg.save()

        email_reminder2 = db.EmailReminder()
        email_reminder2.user = greg._id
        today = datetime.date.today()
        email_reminder2.weekdays = [unicode(today.strftime('%A'))]
        email_reminder2.time = (11,0)
        email_reminder2.tz_offset = 0
        email_reminder2.save()

        # XXX This test is broken because my TestClient isn't able to
        # handle two cookies at the same time.
        # When doing a post Tornado seems to struggle to keep both
        # '_xsrf' and 'user' :(
        return

        bad_url = '/emailreminders/?edit=%s' % \
          str(email_reminder2._id)
        response = self.client.get(bad_url)
        self.assertEqual(response.code, 404) # valid but not yours

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('name="delete"' in response.body)
        from apps.emailreminders.models import EmailReminder
        data = dict(weekdays=[EmailReminder.MONDAY,
                              EmailReminder.WEDNESDAY],
                    edit=str(email_reminder._id),
                    tz_offset=-4.5,
                    time_minute=45,
                    time_hour=11,
                    )

        response = self.client.post(url, data)
        self.assertEqual(response.code, 302)

    def test_posting_email_in(self):
        url = '/emailreminders/receive/'
        body = ['From: bob@builder.com']
        body += ['To: reminder@donecal.com']
        body += ['Subject: [DoneCal] what did you do today?']
        body += ['']
        body += ['This is a test on @tagg']
        body += ['']
        body += ['On 23 Dec someone wrote']
        body += ['> INSTRUCTIONS:']
        body += ['> BLa bla bla']

        response = self.post(url, '\r\n'.join(body))
        self.assertTrue('Not recognized from user' in response.body)
        # because there is no user called bob@builder.com it would send an
        # error reply
        sent_email = mail.outbox[-1]
        self.assertTrue(sent_email.to, ['bob@builder.com'])
        self.assertEqual(sent_email.subject, body[2].replace('Subject:', 'Re:'))
        from settings import EMAIL_REMINDER_SENDER
        self.assertTrue(sent_email.from_email, EMAIL_REMINDER_SENDER)
        self.assertTrue('> This is a test on @tagg' in sent_email.body)
        self.assertTrue('Not a registered account: bob@builder.com' in sent_email.body)

        # try again, this time with bob set up
        bob = self.db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()

        # try again, but this time it will fail because this user doesn't have any
        # email reminders set up
        response = self.post(url, '\r\n'.join(body))
        self.assertTrue('Not a reply to an email reminder' in response.body)

        # set one up!
        email_reminder = self.db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (11,30)
        email_reminder.tz_offset = 0.0
        email_reminder.save()

        body[1] = 'To: reminder+%s@donecal.com' % email_reminder._id

        sent_email = mail.outbox[-1]
        self.assertTrue(
          "This is not a reply to an email reminder from your account" \
          in sent_email.body)

        # Try again, now it should work
        response = self.post(url, '\r\n'.join(body))
        self.assertTrue('Created' in response.body)
        self.assertEqual(self.db.Event.find().count(), 1)
        event = self.db.Event.one()
        self.assertEqual(event.title, u'This is a test on @tagg')
        self.assertEqual(event.tags, [u'tagg'])
        self.assertEqual(event.user.first_name, u"Bob")
        self.assertTrue(event.all_day)
        self.assertTrue(event.start.strftime('%Y%m%d %H%M'),
                        today.strftime('%Y%m%d %H%M'))
        self.assertTrue(event.end.strftime('%Y%m%d %H%M'),
                        today.strftime('%Y%m%d %H%M'))
        self.assertEqual(event.description, u'')
        self.assertEqual(event.external_url, None)

    def test_posting_email_in_invalid_entry(self):
        url = '/emailreminders/receive/'
        body = ['From: bob@builder.com']
        body += ['To: reminder@donecal.com']
        body += ['Subject: [DoneCal] what did you do today?']
        body += ['']
        body += ['13:30pm This wont work']
        body += ['']
        body += ['On 23 Dec someone wrote']
        body += ['> INSTRUCTIONS:']
        body += ['> BLa bla bla']

        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (11,30)
        email_reminder.tz_offset = 0.0
        email_reminder.save()

        body[1] = 'To: reminder+%s@donecal.com' % email_reminder._id

        response = self.post(url, '\r\n'.join(body))
        self.assertTrue("Parse event error" in response.body)
        sent_email = mail.outbox[-1]
        self.assertTrue(sent_email.to, ['bob@builder.com'])
        self.assertTrue(str(email_reminder._id) in sent_email.from_email)
        self.assertEqual(sent_email.subject, body[2].replace('Subject:', 'Re:'))
        self.assertTrue('Error message' in sent_email.body)

    def test_posting_email_in__from_real_user(self):
        url = '/emailreminders/receive/'
        body = ['From: bob@builder.com']
        body += ['To: reminder@donecal.com']
        body += ['Subject: [DoneCal] what did you do today?']
        body += ['']
        body += ['3h #rcpch working on the pdf creation']
        body += ['']
        body += ['1h #snapexpense excel exports and zip for complete report']
        body += ['']
        body += ['0.5 h #lc working on bug report and responding to feature requests']
        body += ['13:30pm This wont work']
        body += ['']
        body += ['On 23 Dec someone wrote']
        body += ['> INSTRUCTIONS:']
        body += ['> BLa bla bla']

        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (11,30)
        email_reminder.tz_offset = 0.0
        email_reminder.save()

        body[1] = 'To: reminder+%s@donecal.com' % email_reminder._id

        response = self.post(url, '\r\n'.join(body))
        self.assertEqual(response.body.count('Created'), 3)
        self.assertEqual(db.Event.find().count(), 3)
        self.assertEqual(db.Event.find({'tags':'rcpch'}).count(), 1)
        self.assertEqual(db.Event.find({'tags':'snapexpense'}).count(), 1)
        self.assertEqual(db.Event.find({'tags':'lc'}).count(), 1)

    def test_posting_email_in_one_valid_one_invalid_entry(self):
        url = '/emailreminders/receive/'
        body = ['From: bob@builder.com']
        body += ['To: reminder@donecal.com']
        body += ['Subject: [DoneCal] what did you do today?']
        body += ['']
        body += ['13:30pm This wont work']
        body += ['']
        body += ['3:30pm 60min This will work']
        body += ['']
        body += ['On 23 Dec someone wrote']
        body += ['> INSTRUCTIONS:']
        body += ['> BLa bla bla']

        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (11,30)
        email_reminder.tz_offset = 0.0
        email_reminder.save()

        body[1] = 'To: reminder+%s@donecal.com' % email_reminder._id

        response = self.post(url, '\r\n'.join(body))
        self.assertTrue('Created' in response.body)
        self.assertTrue('Parse event error' in response.body)
        self.assertEqual(db.Event.find().count(), 1)
        event = db.Event.one()
        self.assertEqual(event.title, 'This will work')
        self.assertTrue(not event.all_day)
        length = event.end - event.start
        self.assertEqual(length.seconds/60, 60)

    def test_posting_email_in_with_description(self):
        url = '/emailreminders/receive/'
        body = ['From: bob@builder.com']
        body += ['To: reminder@donecal.com']
        body += ['Subject: [DoneCal] what did you do today?']
        body += ['']
        body += ['This is the title']
        body += ['This is the description']
        body += ['']
        body += ['On 23 Dec someone wrote']
        body += ['> INSTRUCTIONS:']
        body += ['']
        body += ['> BLa bla bla']

        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (11,30)
        email_reminder.tz_offset = 0.0
        email_reminder.save()

        body[1] = 'To: DoneCal <reminder+%s@donecal.com>' % email_reminder._id

        response = self.post(url, '\r\n'.join(body))
        self.assertEqual(db.Event.find().count(), 1)
        event = db.Event.one()
        self.assertEqual(event.title, 'This is the title')
        self.assertEqual(event.description, 'This is the description')

    def test_posting_email_in_stacked_after_each_other(self):
        url = '/emailreminders/receive/'
        body = ['From: bob@builder.com']
        body += ['To: reminder@donecal.com']
        body += ['Subject: [DoneCal] what did you do today?']
        body += ['']
        body += ['1h Doing']
        body += ['']
        body += ['2h Goofing']
        body += ['']
        body += ['On 23 Dec someone wrote']
        body += ['> INSTRUCTIONS:']
        body += ['']
        body += ['> BLa bla bla']

        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (11,30)
        email_reminder.tz_offset = 0.0
        email_reminder.save()

        body[1] = 'To: DoneCal <reminder+%s@donecal.com>' % email_reminder._id

        response = self.post(url, '\r\n'.join(body))
        self.assertEqual(db.Event.find().count(), 2)
        events = list(db.Event.find().sort('start', 1))
        self.assertEqual([x.title for x in events], [u'Doing', u'Goofing'])
        self.assertEqual([x.start.hour for x in events], [12, 13])
        first, last = events
        self.assertEqual(first.start.hour, 12)
        self.assertEqual(first.end.hour, 13)
        self.assertEqual(last.start.hour, 13)
        self.assertEqual(last.end.hour, 15)


    def test_posting_email_in_stacked_after_each_other_with_specific_start(self):
        url = '/emailreminders/receive/'
        body = ['From: bob@builder.com']
        body += ['To: reminder@donecal.com']
        body += ['Subject: [DoneCal] what did you do today?']
        body += ['']
        body += ['1h Doing']
        body += ['']
        body += ['2h Goofing']
        body += ['']
        body += ['On 23 Dec someone wrote']
        body += ['> INSTRUCTIONS:']
        body += ['']
        body += ['> BLa bla bla']

        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()
        bob_settings = db.UserSettings()
        bob_settings.user = bob._id
        bob_settings.first_hour = 6
        bob_settings.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (11,30)
        email_reminder.tz_offset = 0.0
        email_reminder.save()

        body[1] = 'To: DoneCal <reminder+%s@donecal.com>' % email_reminder._id

        response = self.post(url, '\r\n'.join(body))
        self.assertEqual(db.Event.find().count(), 2)
        events = list(db.Event.find().sort('start', 1))
        self.assertEqual([x.title for x in events], [u'Doing', u'Goofing'])
        self.assertEqual([x.start.hour for x in events], [6, 7])
        first, last = events
        self.assertEqual(first.start.hour, 6)
        self.assertEqual(first.end.hour, 7)
        self.assertEqual(last.start.hour, 7)
        self.assertEqual(last.end.hour, 9)

    def test_posting_email_in_with_duration_only(self):
        url = '/emailreminders/receive/'
        body = ['From: bob@builder.com']
        body += ['To: reminder@donecal.com']
        body += ['Subject: [DoneCal] what did you do yesterday?']
        body += ['']
        body += ['2 hours @tagg This is the title']
        body += ['']
        body += ['On 23 Dec someone wrote:']
        body += ['> INSTRUCTIONS:']
        body += ['> BLa bla bla']

        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (10,0)
        email_reminder.tz_offset = -5.5
        email_reminder.save()

        body[1] = 'To: reminder+%s@donecal.com' % email_reminder._id

        response = self.post(url, '\r\n'.join(body))
        self.assertTrue('Created' in response.body)
        self.assertEqual(db.Event.find().count(), 1)
        event = db.Event.one()

        self.assertEqual(event.title, '@tagg This is the title')
        self.assertTrue(not event.all_day)
        # the default time is 12.00 in local time.
        # so in this case, because this guy has a -5h offset
        # it should become 12.00 - (-5) = 17.00 GMT
        length = event.end - event.start
        minutes = length.seconds/60
        self.assertEqual(minutes, 60 * 2)
        n = datetime.datetime.now()
        twelve_plus_5 = datetime.datetime(n.year, n.month, n.day, 17, 0)
        # really don't know how this will hold up in BST!!
        self.assertEqual(event.start.strftime('%H'),
                         twelve_plus_5.strftime('%H'))

        # because the email reminder said 'What did you do yesterday?'
        # the start date should be yesterday
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.assertEqual(event.start.strftime('%Y%m%d'),
                         yesterday.strftime('%Y%m%d'))


    def test_sending_reminders(self):
        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (10,0)
        email_reminder.tz_offset = -5.5 # means 15.30 GMT
        email_reminder.save()
        email_reminder.set_next_send_date()
        self.assertEqual(email_reminder._next_send_date.strftime('%H'), '15')
        self.assertEqual(email_reminder._next_send_date.strftime('%M'), '30')
        email_reminder.save()
        fake_utcnow = email_reminder._next_send_date

        url = '/emailreminders/send/'
        url += '?now_utc=%s' % mktime(fake_utcnow.timetuple())
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        sent_email = mail.outbox[-1]
        self.assertTrue('What did you do' in sent_email.subject)
        self.assertTrue('yesterday' in sent_email.subject)
        self.assertTrue('INSTRUCTIONS' in sent_email.body)
        self.assertTrue('edit=%s' % email_reminder._id  in sent_email.body)
        self.assertEqual(sent_email.to, [bob.email])
        from_email = 'reminder+%s@donecal.com' % email_reminder._id
        self.assertTrue('<%s>' % from_email in sent_email.from_email)

        # by default, the setting to this user is to use the 24h time format
        ampm_example_regex = re.compile('\d\d:\d\d(am|pm)')
        self.assertTrue(not ampm_example_regex.findall(sent_email.body))
        _24hour_example_regex = re.compile('\d{1,2}:\d\d\s')
        self.assertTrue(_24hour_example_regex.findall(sent_email.body))

    def test_sending_reminders_to_a_premium_user(self):
        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.premium = True
        bob.first_name = u"Bob"
        bob.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (10,0)
        email_reminder.tz_offset = 0
        email_reminder.save()
        email_reminder.set_next_send_date()
        email_reminder.save()
        fake_utcnow = email_reminder._next_send_date

        url = '/emailreminders/send/'
        url += '?now_utc=%s' % mktime(fake_utcnow.timetuple())
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        sent_email = mail.outbox[-1]
        self.assertTrue(sent_email.body.count('https://'))
        self.assertTrue(not sent_email.body.count('http://'))

    def test_sending_reminder_with_summary(self):
        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()

        user_settings = db.UserSettings()
        user_settings.user = bob._id
        user_settings.ampm_format = True
        user_settings.save()


        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (10,0)
        email_reminder.tz_offset = 0
        email_reminder.include_instructions = False
        email_reminder.include_summary = True
        email_reminder.save()
        email_reminder.set_next_send_date()
        email_reminder.save()
        fake_utcnow = email_reminder._next_send_date

        # for this to work we need to add some events to include.
        # Because we're sending the email reminder before noon it doesn't make
        # sense to summorize what has already been done today.

        event1 = db.Event()
        event1.user = bob
        event1.all_day = True
        event1.start = fake_utcnow - datetime.timedelta(minutes=60)
        event1.end = fake_utcnow - datetime.timedelta(minutes=60)
        event1.title = u"Done today"
        event1.save()

        event2 = db.Event()
        event2.user = bob
        event2.all_day = True
        event2.start = fake_utcnow - datetime.timedelta(days=1)
        event2.end = fake_utcnow - datetime.timedelta(days=1)
        event2.title = u"Done all day yesterday"
        event2.save()

        event3 = db.Event()
        event3.user = bob
        event3.all_day = False
        event3.start = fake_utcnow - datetime.timedelta(days=1)
        event3.end = fake_utcnow - datetime.timedelta(days=1) + datetime.timedelta(minutes=90)
        event3.title = u"Done specific time yesterday"
        event3.save()

        # add another one so we make sure the order is right
        event3b = db.Event()
        event3b.user = bob
        event3b.all_day = False
        event3b.start = event3.start - datetime.timedelta(minutes=60)
        event3b.end = event3.end - datetime.timedelta(minutes=60)
        event3b.title = u"Specific time yesterday earlier"
        event3b.save()

        event4 = db.Event()
        event4.user = bob
        event4.all_day = True
        event4.start = fake_utcnow - datetime.timedelta(days=2)
        event4.end = fake_utcnow - datetime.timedelta(days=2)
        event4.title = u"Done long time ago"
        event4.save()

        url = '/emailreminders/send/'
        url += '?now_utc=%s' % mktime(fake_utcnow.timetuple())
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        sent_email = mail.outbox[-1]

        self.assertTrue('yesterday' in sent_email.subject)

        self.assertTrue('Done all day yesterday' in sent_email.body)
        self.assertTrue('(All day) ' in sent_email.body)
        self.assertTrue('Done specific time yesterday' in sent_email.body)
        self.assertTrue(u"Specific time yesterday earlier" in sent_email.body)
        self.assertTrue(format_time_ampm(event3.start) in sent_email.body)
        self.assertTrue("Done long time ago" not in sent_email.body)
        self.assertTrue('Done today' not in sent_email.body)
        self.assertTrue('INSTRUCTIONS' not in sent_email.body)

        self.assertTrue(sent_email.body.find("Specific time yesterday earlier") < \
                        sent_email.body.find('Done specific time yesterday'))

        # by default, the setting to this user is to use the 24h time format
        ampm_example_regex = re.compile('\d{1,2}:\d\d(am|pm)')
        ampm_example_regex2 = re.compile('\d{1,2}(am|pm)')
        self.assertTrue(ampm_example_regex.findall(sent_email.body) or \
                        ampm_example_regex2.findall(sent_email.body))
        _24hour_example_regex = re.compile('\d{1,2}:\d\d\s')
        self.assertTrue(not _24hour_example_regex.findall(sent_email.body))

        self.assertEqual(db.Event.find({'user.$id': bob._id}).count(), 5)

        # now reply to it
        body = ['From: bob@builder.com']
        body += ['To: %s' % sent_email.from_email]
        body += ['Subject: Re: %s' % sent_email.subject]
        body += ['']
        body += ['2 hours @tagg This is the title']
        body += ['']
        body += ['On 23 Dec someone wrote:']

        body.extend(['> %s' % x for x in sent_email.body.splitlines()])
        #body += ['> INSTRUCTIONS:']
        #body += ['> BLa bla bla']

        url = '/emailreminders/receive/'
        response = self.post(url, '\r\n'.join(body))
        self.assertTrue('Created' in response.body)

        self.assertEqual(db.Event.find({'user.$id': bob._id}).count(), 6)


    def test_sending_reminder_with_summary_about_today(self):
        db = self.get_db()
        bob = db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()

        user_settings = db.UserSettings()
        user_settings.user = bob._id
        user_settings.ampm_format = True
        user_settings.save()

        email_reminder = db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (19,0)
        email_reminder.tz_offset = 0
        email_reminder.include_instructions = False
        email_reminder.include_summary = True
        email_reminder.save()
        email_reminder.set_next_send_date()
        email_reminder.save()
        fake_utcnow = email_reminder._next_send_date

        # for this to work we need to add some events to include.
        # Because we're sending the email reminder before noon it doesn't make
        # sense to summorize what has already been done today.

        event1 = db.Event()
        event1.user = bob
        event1.all_day = True
        event1.start = fake_utcnow - datetime.timedelta(minutes=60)
        event1.end = fake_utcnow - datetime.timedelta(minutes=60)
        event1.title = u"Done today"
        event1.save()

        event2 = db.Event()
        event2.user = bob
        event2.all_day = True
        event2.start = fake_utcnow - datetime.timedelta(days=1)
        event2.end = fake_utcnow - datetime.timedelta(days=1)
        event2.title = u"Done all day yesterday"
        event2.save()

        event3 = db.Event()
        event3.user = bob
        event3.all_day = False
        event3.start = fake_utcnow - datetime.timedelta(days=1)
        event3.end = fake_utcnow - datetime.timedelta(days=1) + datetime.timedelta(minutes=90)
        event3.title = u"Done specific time yesterday"
        event3.save()

        # add another one so we make sure the order is right
        event3b = db.Event()
        event3b.user = bob
        event3b.all_day = False
        event3b.start = event3.start - datetime.timedelta(minutes=60)
        event3b.end = event3.end - datetime.timedelta(minutes=60)
        event3b.title = u"Specific time yesterday earlier"
        event3b.save()

        event4 = db.Event()
        event4.user = bob
        event4.all_day = True
        event4.start = fake_utcnow - datetime.timedelta(days=2)
        event4.end = fake_utcnow - datetime.timedelta(days=2)
        event4.title = u"Done long time ago"
        event4.save()

        url = '/emailreminders/send/'
        url += '?now_utc=%s' % mktime(fake_utcnow.timetuple())
        response = self.client.get(url)
        self.assertEqual(response.code, 200)


        sent_email = mail.outbox[-1]

        self.assertTrue('today' in sent_email.subject)
        self.assertTrue('Done all day yesterday' not in sent_email.body)
        self.assertTrue('(All day) ' in sent_email.body)
        self.assertTrue('Done specific time yesterday' not in sent_email.body)
        self.assertTrue(u"Specific time yesterday earlier" not in sent_email.body)
        self.assertTrue("Done long time ago" not in sent_email.body)
        self.assertTrue('Done today' in sent_email.body)
        self.assertTrue('INSTRUCTIONS' not in sent_email.body)

    def test_receive_david_bug(self):
        test_file = os.path.join(os.path.dirname(__file__), '2011-02-23_003928_692010.email')
        body = open(test_file).read()
        assert len(body)
        url = '/emailreminders/receive/'
        response = self.post(url, body)
        #print response.body
        self.assertTrue('Created' not in response.body)
        self.assertTrue('Not recognized' in response.body and \
          'denghui.cn@gmail.com' in response.body)

        # set up the user and try again
        db = self.get_db()
        user = db.User()
        user.email = u'denghui.cn@gmail.com'
        user.first_name = u"David"
        user.save()

        response = self.post(url, body)
        self.assertTrue('Not a reply to an email reminder' in response.body)

        # got to set up an email reminder that we can attach this reply to
        # This is in the sample email <reminder+4d32343474a1f87fa2000000@donecal.com>
        email_reminder = db.EmailReminder()
        email_reminder.user = user._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (8,0)
        email_reminder.tz_offset = 0
        email_reminder.include_instructions = True
        email_reminder.include_summary = False
        email_reminder.save()
        email_reminder.set_next_send_date()
        email_reminder.save()
        body = body.replace('4d32343474a1f87fa2000000',
                            str(email_reminder._id))
        response = self.post(url, body)
        self.assertTrue('Created' in response.body)
        event = db.Event.one({'user.$id':user._id})
        self.assertTrue(event)

    def test_receive_peter_swedish_bug(self):
        test_file = os.path.join(os.path.dirname(__file__), '2011-02-23_114902_621456.email')
        body = open(test_file).read()
        assert len(body)
        url = '/emailreminders/receive/'
        response = self.post(url, body)
        self.assertTrue('Not recognized' in response.body)

        db = self.get_db()
        user = db.User()
        user.email = u'peterbe@gmail.com'
        user.first_name = u"Peter"
        user.save()

        response = self.post(url, body)
        self.assertTrue('Not a reply to an email reminder' in response.body)

        email_reminder = db.EmailReminder()
        email_reminder.user = user._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (8,0)
        email_reminder.tz_offset = 0
        email_reminder.include_instructions = True
        email_reminder.include_summary = False
        email_reminder.save()
        email_reminder.set_next_send_date()
        email_reminder.save()
        body = body.replace('4d11e7b674a1f8361200006c',
                            str(email_reminder._id))
        response = self.post(url, body)
        self.assertTrue('Created' in response.body)
        events = db.Event.find({'user.$id':user._id})
        self.assertEqual(events.count(), 2)

    def test_receive_minute_time_bug(self):
        test_file = os.path.join(os.path.dirname(__file__), '2011-05-17_220706_318577.email')
        body = open(test_file).read()
        assert len(body)
        url = '/emailreminders/receive/'
        response = self.post(url, body)
        self.assertTrue('Not recognized' in response.body)

        user = self.db.User()
        user.email = u'peterbe@gmail.com'
        user.first_name = u"Peter"
        user.save()

        response = self.post(url, body)
        self.assertTrue('Not a reply to an email reminder' in response.body)

        email_reminder = self.db.EmailReminder()
        email_reminder.user = user._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (8,0)
        email_reminder.tz_offset = 0
        email_reminder.include_instructions = True
        email_reminder.include_summary = False
        email_reminder.save()
        email_reminder.set_next_send_date()
        email_reminder.save()
        body = body.replace('4dd2ca7c74a1f8034c000039',
                            str(email_reminder._id))
        response = self.post(url, body)
        self.assertTrue('Created' in response.body)
        events = self.db.Event.find({'user.$id':user._id})
        self.assertEqual(events.count(), 1)
        event = self.db.Event.one()
        self.assertEqual((event.end - event.start).seconds, 3600)
        self.assertEqual(event.title, u'Fate: configurar scanner WC35')

    def test_receive_charset_bug(self):
        test_file = os.path.join(os.path.dirname(__file__), '2011-09-19_090052_194569.email')
        body = open(test_file).read()
        assert len(body)
        url = '/emailreminders/receive/'
        response = self.post(url, body)
        self.assertTrue('Not recognized' in response.body)

        user = self.db.User()
        user.email = u'peterbe@gmail.com'
        user.first_name = u"Peter"
        user.save()

        response = self.post(url, body)
        self.assertTrue('Not a reply to an email reminder' in response.body)

        email_reminder = self.db.EmailReminder()
        email_reminder.user = user._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (8,0)
        email_reminder.tz_offset = 0
        email_reminder.include_instructions = True
        email_reminder.include_summary = False
        email_reminder.save()
        email_reminder.set_next_send_date()
        email_reminder.save()
        body = body.replace('4dd2ca7c74a1f8034c000039',
                            str(email_reminder._id))
        response = self.post(url, body)

        self.assertTrue('Created' in response.body)
        events = self.db.Event.find({'user.$id':user._id})
        self.assertEqual(events.count(), 2)
        for event in self.db.Event.find():
            t1 = u'\u62b1\u6b49\uff0c\u60a8\u7684\u90ae\u4ef6\u88ab'\
                 u'\u9000\u56de\u6765\u4e86\u2026\u2026'
            t2 = u'\u5efa\u8bae\u89e3\u51b3\u65b9\u6848\uff1a'
            self.assertTrue(event.title in (t1, t2))


    def test_receive_gautier_time_bug(self):
        test_file = os.path.join(os.path.dirname(__file__), '2011-03-28_170726_751460.email')
        body = open(test_file).read()
        assert len(body)
        url = '/emailreminders/receive/'
        response = self.post(url, body)
        self.assertTrue('Not recognized' in response.body)

        db = self.get_db()
        user = db.User()
        user.email = u'peterbe@gmail.com'
        user.first_name = u"Peter"
        user.save()

        response = self.post(url, body)
        self.assertTrue('Not a reply to an email reminder' in response.body)

        email_reminder = db.EmailReminder()
        email_reminder.user = user._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (8,0)
        email_reminder.tz_offset = 0
        email_reminder.include_instructions = True
        email_reminder.include_summary = False
        email_reminder.save()
        email_reminder.set_next_send_date()
        email_reminder.save()
        body = body.replace('4d90a11374a1f8470e00005c',
                            str(email_reminder._id))
        response = self.post(url, body)
        self.assertTrue('Created' in response.body)
        events = db.Event.find({'user.$id':user._id})
        self.assertEqual(events.count(), 2)

    def test_posting_email_in_not_a_reply(self):
        url = '/emailreminders/receive/'
        body = ['From: bob@builder.com']
        body += ['To: reminder@donecal.com']
        body += ['Subject: [DoneCal] what did you do today?']
        body += ['']
        body += ['Just some nice text']
        body += ['INSTRUCTIONS']
        body += ['bla bla']
        body += ['']

        response = self.post(url, '\r\n'.join(body))
        self.assertTrue('Not recognized from user' in response.body)
        # try again, this time with bob set up
        bob = self.db.User()
        bob.email = u'Bob@Builder.com'
        bob.first_name = u"Bob"
        bob.save()
        response = self.post(url, '\r\n'.join(body))
        self.assertTrue('Not a reply to an email reminder' in response.body)

        email_reminder = self.db.EmailReminder()
        email_reminder.user = bob._id
        today = datetime.date.today()
        email_reminder.weekdays = [unicode(today.strftime('%A'))]
        email_reminder.time = (11,30)
        email_reminder.tz_offset = 0.0
        email_reminder.save()

        body[1] = 'To: reminder+%s@donecal.com' % email_reminder._id

        response = self.post(url, '\r\n'.join(body))
        self.assertTrue('Not a reply email' in response.body)
