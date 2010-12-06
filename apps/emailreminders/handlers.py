import tornado.web

from mongokit import ValidationError
from utils.decorators import login_required
from utils.routes import route
from apps.main.handlers import BaseHandler

@route('/emailreminders/$')
class EmailRemindersHandler(BaseHandler):
    
    def get(self):
        options = self.get_base_options()
        self.render('emailreminders/index.html', **options)
        
    @login_required
    def post(self):
        weekdays = self.get_arguments('weekdays')
        assert isinstance(weekdays, list), type(weekdays)
        time_hour = int(self.get_argument('time_hour'))
        time_minute = int(self.get_argument('time_minute'))
        tz_offset = int(self.get_argument('tz_offset'))
        
        
        user = self.get_current_user()
        email_reminder = self.db.EmailReminder()
        email_reminder.user = user
        email_reminder.weekdays = weekdays
        email_reminder.time = (time_hour, time_minute)
        email_reminder.tz_offset = tz_offset
        try:
            email_reminder.save()
        except ValidationError, msg:
            raise tornado.web.HTTPError(400, str(msg))
        
        # XXX: flash message?
        self.redirect('/emailreminders/')

        
        
        
