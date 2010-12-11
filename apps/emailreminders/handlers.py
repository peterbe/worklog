from pymongo.objectid import InvalidId, ObjectId
import tornado.web

from mongokit import ValidationError
from utils.decorators import login_required
from utils.routes import route
from apps.main.handlers import BaseHandler
from models import EmailReminder

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
    
    #def get_sendable_email_reminders(self):
    #    # Assume that right now is 'Thu, 1 Dec 2001, 00:15:00 GMT' in London.
    #    # That means it's simultaneously 'Wed, 30 Nov 2001, 19:15:00 EST' in
    #    # New York. If a user has set up to reminder to go Wednesdays at 7.15pm
    #    # then it means we can't
    
    def get(self):
        # this should perhaps use a message queue instead
        utc_now = datetime.datetime.now()
        search = dict(_next_send_date={'$lte':utc_now})
        for email_reminder in self.db.EmailReminder.find(search):
            print "TO %s" % email_reminder.user.email
            
        self.write("Done")
        
        
