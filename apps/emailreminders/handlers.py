import datetime
from pymongo.objectid import InvalidId, ObjectId
import tornado.web

from mongokit import ValidationError
from utils.decorators import login_required
from utils import parse_datetime, niceboolean
from utils.routes import route
from apps.main.handlers import BaseHandler
from models import EmailReminder
from utils.send_mail import send_email
from settings import EMAIL_REMINDER_SENDER, EMAIL_REMINDER_REPLY_TO

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
            
        from time import mktime
        print mktime(edit_reminder._next_send_date.timetuple())
            
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
        print "TO %s" % email_reminder.user.email
        
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
        
        
