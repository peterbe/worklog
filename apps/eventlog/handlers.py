from utils.decorators import login_required
from apps.main.handlers import BaseHandler
from utils.routes import route

@route('/log/$')
class EventLogHandler(BaseHandler):
    DEFAULT_BATCH_SIZE = 100
    
    @login_required
    def get(self):
        options = self.get_base_options()
        user = self.get_current_user()
        superuser = user.email == 'peterbe@gmail.com'
        search = {'user.$id': user._id}
        if superuser:
            search = dict()
        event_logs = self.db.EventLog.find(search)
        options['count_event_logs'] = event_logs.count()
        options['superuser'] = superuser
        
        page = int(self.get_argument('page', 1))
        batch_size = self.DEFAULT_BATCH_SIZE
        skip = (page - 1) * batch_size
        options['page'] = page
        options['skip'] = skip
        options['pages'] = range(1, 1 + options['count_event_logs'] / batch_size)
        options['event_logs'] = list(event_logs.sort('add_date', -1).skip(skip).limit(batch_size))
        
        self.render("eventlog/index.html", **options)