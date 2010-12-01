from utils.routes import route
from apps.main.handlers import BaseHandler

@route('/(iphone|android)/$')
class SmartphoneHandler(BaseHandler):
    def get(self, device_name):
        options = dict()
        self.render('smartphone/index.html', **options)
        