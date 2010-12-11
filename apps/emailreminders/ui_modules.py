import tornado.web

class ShowWeekdayReminders(tornado.web.UIModule):
    def render(self, weekday, weekday_reminders):
        reminders = weekday_reminders.get(weekday, [])
        return self.render_string("emailreminders/show_weekday_reminders.html", reminders=reminders)
    
    
