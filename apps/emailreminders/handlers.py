import re
from cStringIO import StringIO
import datetime
from pymongo.objectid import InvalidId, ObjectId
import tornado.web

from mongokit import ValidationError
from utils.decorators import login_required
from utils import parse_datetime, niceboolean
from utils.routes import route
from apps.main.handlers import BaseHandler, EventsHandler
from models import EmailReminder
from utils.send_mail import send_email
from reminder_utils import ParseEventError, parse_time, \
  parse_duration, parse_email_line
from settings import EMAIL_REMINDER_SENDER, EMAIL_REMINDER_REPLY_TO

class ParseEventError(Exception):
    pass

@route('/emailreminders/$')
class EmailRemindersHandler(BaseHandler):
    
    def get(self):
        options = self.get_base_options()
        
        weekdays = list(EmailReminder.WEEKDAYS)
        monday_first = False
        
        edit_reminder = self.get_edit_reminder()
        
        # default
        options['weekday_reminders'] = dict()
        options['count_reminders'] = 0
        options['all_reminder_classnames'] = dict()
        
        background_colors = iter(("#ff5800", "#0085cc",
                    "#c747a3","#26B4E3", "#bd70c7", "#cddf54", "#FBD178" ))
        
        user = self.get_current_user()
        if user:
            _base_search = {'user.$id': user._id}
            weekday_reminders = dict()
            for weekday in EmailReminder.WEEKDAYS:
                _reminders = self.db.EmailReminder\
                  .find(dict(_base_search, weekdays=weekday))
                  
                weekday_reminders[weekday] = _reminders.sort('time')
                options['count_reminders'] += _reminders.count()
                
            options['weekday_reminders'] = weekday_reminders
            
            user_settings = self.db.UserSettings.one({'user.$id': user._id})
            if user_settings:
                monday_first = user_settings.monday_first
                
            for reminder in self.db.EmailReminder.find(_base_search):
                options['all_reminder_classnames'][str(reminder._id)] = \
                  background_colors.next()
                  
        if not monday_first:
            # make it start with the Sunday
            weekdays.insert(0, weekdays[-1])
            weekdays.pop()
            
        options['weekdays'] = weekdays
        
        options['all_reminder_classnames'] = options['all_reminder_classnames'].items()
        options['edit_reminder'] = edit_reminder
        
        self.render('emailreminders/index.html', **options)
        
    def get_edit_reminder(self):
        edit_reminder = None
        if self.get_argument('edit', None):
            user = self.get_current_user()
            if not user:
                raise tornado.web.HTTPError(403, "not logged in")
            
            try:
                edit_reminder = self.db.EmailReminder\
                  .one({'_id': ObjectId(self.get_argument('edit'))})
            except InvalidId:
                raise tornado.web.HTTPError(400, "Invalid ID")
            
            if not edit_reminder:
                raise tornado.web.HTTPError(404, "Not found")
            
            if edit_reminder.user._id != user._id:
                raise tornado.web.HTTPError(404, "Not yours")
            
        return edit_reminder
        
        
    @login_required
    def post(self):
        
        edit_reminder = self.get_edit_reminder()
        if edit_reminder:
            if self.get_argument('delete', False):
                edit_reminder.delete()
                return self.redirect('/emailreminders/')
            
        weekdays = self.get_arguments('weekdays')
        assert isinstance(weekdays, list), type(weekdays)
        time_hour = int(self.get_argument('time_hour'))
        time_minute = int(self.get_argument('time_minute'))
        tz_offset = int(self.get_argument('tz_offset'))
        
        user = self.get_current_user()
        if edit_reminder:
            email_reminder = edit_reminder
        else:
            email_reminder = self.db.EmailReminder()
            email_reminder.user = user
        email_reminder.weekdays = weekdays
        email_reminder.time = (time_hour, time_minute)
        email_reminder.tz_offset = tz_offset
        email_reminder.set_next_send_date()
        try:
            email_reminder.save()
        except ValidationError, msg:
            raise tornado.web.HTTPError(400, str(msg))
        
        # XXX: flash message?
        self.redirect('/emailreminders/')

        
@route('/emailreminders/send/$')
class SendEmailRemindersHandler(BaseHandler):
    """Can be fired from a cronjob every 15 minutes without having to be worried
    about accidentally sending the same user the same email. A log is used to 
    safeguard against possible duplicate sendings.
    """
    
    def get(self):
        # this should perhaps use a message queue instead
        now_utc = datetime.datetime.utcnow()
        dry_run = niceboolean(self.get_argument('dry_run', False))
        if self.get_argument('now_utc', None):
            now_utc = parse_datetime(self.get_argument('now_utc'))
            
        search = dict(_next_send_date={'$lte':now_utc})
        for email_reminder in self.db.EmailReminder.find(search):
            self.write("TO: %s\n" % email_reminder.user.email)
            self._send_reminder(email_reminder, dry_run=dry_run)
            
            if not dry_run:
                email_reminder.set_next_send_date(now_utc)
                email_reminder.save()
                
                email_reminder_log = self.db.EmailReminderLog()
                email_reminder_log.email_reminder = email_reminder
                email_reminder_log.save()
            
        self.write("Done\n")
        
    def _send_reminder(self, email_reminder, dry_run=False):
        
        subject = u"[DoneCal]"
        if email_reminder.time[0] > 12:
            about_today = True
            subject += " What did you do today?"
        else:
            about_today = False
            subject += u" What did you do yesterday?"
            
        first_name = email_reminder.user.first_name
        
        email_reminder_edit_url = 'http://%s/emailreminders/' % self.request.host
        email_reminder_edit_url += '?edit=%s' % email_reminder._id
        body = self.render_string("emailreminders/send_reminder.txt",
                                  email_reminder=email_reminder,
                                  first_name=first_name,
                                  about_today=about_today,
                                  email_reminder_edit_url=\
                                  email_reminder_edit_url)
                                   
        reply_to = EMAIL_REMINDER_REPLY_TO % {'id': str(email_reminder._id)}
        send_email(self.application.settings['email_backend'],
                   subject, 
                   body,
                   EMAIL_REMINDER_SENDER,
                   [email_reminder.user.email],
                   headers={'Reply-To': reply_to},
                   )

@route('/emailreminders/receive/$')
class ReceiveEmailReminder(EventsHandler):

    def post(self):
        message = self.request.body
        from email import Parser
        parser = Parser.Parser()
        msg = parser.parsestr(message)
        
        ## Check that it was sent from someone we know
        from_user = None
        for from_email in parse_email_line(msg['From']):
            from_user = self.find_user(from_email)
            
        if not from_user:
            # only bother to reply if the email appears to be sent from
            # us originally
            if 'INSTRUCTIONS' in msg.get_payload(decode=True) and 'DoneCal' in msg['Subject']:
                self.error_reply("Not a registered account: %s" % msg['From'], msg)
            
            self.write("Not recognized from user (%r)" % msg['From'])
            return
        
        if not self.db.EmailReminder.find({'user.$id': from_user._id}).count():
            if 'INSTRUCTIONS' in msg.get_payload(decode=True) and 'DoneCal' in msg['Subject']:
                err_msg = u"You don't have any email reminders set up.\n"\
                          u"To set some up, go to http://%s/emailreminders/" % \
                           self.request.host
                self.error_reply(err_msg , msg)
                
            self.write("No email reminders set up")
            return
            
        
        ## Check that it's sent to the right address
        email_tos = parse_email_line(msg['To'])
        
        email_reminder = None
        
        if EMAIL_REMINDER_SENDER.lower() in [x.lower() for x in email_tos]:
            # easy pass!
            pass
        else:
            # need to turn then reply to address into a regex
            reply_to_parts = EMAIL_REMINDER_REPLY_TO % dict(id='XXX')
            reply_to_parts = reply_to_parts.split('@')
            assert len(reply_to_parts) == 2
            regex = re.compile(re.escape(reply_to_parts[0]) + '(\w+)' \
              + re.escape(reply_to_parts[1]), re.I)
            for email_to in email_tos:
                if regex.findall(email_to):
                    raise NotImplementedError(regex.findall(email_to))
                
        #for key, value in msg.items():
        #    print key
        body = msg.get_payload(decode=True)
        from formatflowed import decode
        character_set = msg.get_charset()
        CRLF = '\r\n'
        body = body.replace('\n', CRLF)
        try:
            if character_set:
                textflow = decode(body, character_set=character_set)
            else:
                textflow = decode(body)
        except LookupError:
            if not character_set:
                raise
            # _character_set is quite likly 'iso-8859-1;format=flowed'
            _character_set = _character_set.split(';')[0].strip()
            textflow = decode(body, character_set=character_set)
            
        new_text = StringIO()
        for segment in textflow:
            if not segment[0]['quotedepth']:
                # level zero
                new_text.write(segment[1])
        
        new_text = new_text.getvalue()
        if email_reminder:
            if email_reminder.time[0] > 12:
                about_today = True
            else:
                about_today = False
        else:
            if 'today' in msg['Subject']:
                about_today = True
            else:
                about_today = False
                
        count_new_events = 0
        for text in new_text.strip().split('\n\n'):
            try:
                event = self.parse_and_create_event(from_user, text, about_today)
                if event:
                    self.write("Created %r\n" % event.title)
                    count_new_events += 1
            except ParseEventError, exception_message:
                if 'INSTRUCTIONS' in msg.get_payload(decode=True) and \
                 'DoneCal' in msg['Subject']:
                    err_msg = "Failed to create an event from this line:\n\t%s\n" \
                      % text
                    err_msg += "(Error message: %s)\n" % exception_message
                    self.error_reply(err_msg, msg)
            
        self.write("\n")
        
    def parse_and_create_event(self, user, text, about_today):
        """parse the text (which can be more than one line) and return either a
        newly created event object or nothing.
        """
        print repr(text)
        text, time_ = parse_time(text)
            
        if time_:
            # if the time part was the first word, then maybe the duration is
            # the next first word
            text, duration = parse_duration(text)
            # remember, duration is always in minutes!
        else:
            duration = None
        
        if len(text.splitlines()) > 1:
            title = text.splitlines()[0]
            description = '\n'.join(text.splitlines()[1:])
        else:
            title = text
            description = u''
        
        if time_:
            all_day = False
        else:
            all_day = True
            
        if about_today:
            start_base = datetime.datetime.today()
        else:
            start_base = datetime.datetime.today() - datetime.timedelta(days=1)
            
        if all_day:
            start = end = start_base
        else:
            start = start_base
            start = datetime.datetime(start.year, start.month, start.day, 
                                      time_[0], time[1])
            if not duration:
                duration = MINIMUM_DAY_SECONDS / 60
            end = start + datetime.timedelta(minutes=duration)
            
        if isinstance(title, str):
            try:
                title = title.decode("utf-8")
            except UnicodeDecodeError:
                raise ParseEventError("Title not a valid UTF-8 string")
            
        if isinstance(description, str):
            try:
                description = description.decode("utf-8")
            except UnicodeDecodeError:
                raise ParseEventError("Description not a valid UTF-8 string")
            
        event, not_duplicate = self.create_event(
          user, 
          title=title, 
          description=description,
          all_day=all_day, 
          start=start, 
          end=end,
        )
        
        return event
        
    
    def error_reply(self, error_message, msg):
        """send an email reply"""
        body = msg.get_payload(decode=True)
        body = body.replace('\r\n', '\n')
        body = '\n'.join(['> %s' % line for line in body.splitlines()])
        body = u'Error in receiving email.\n   %s\n\nPlease try again.\n\n' \
          % error_message + body
        subject = "Re: %s" % msg['Subject']
        
        send_email(self.application.settings['email_backend'],
                   subject, 
                   body,
                   EMAIL_REMINDER_SENDER,
                   [msg['From']],
                   )
        
        #self.error_reply("Not a registered account: %s" % msg['From'], msg)

