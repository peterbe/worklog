from utils.routes import route
from apps.main.handlers import BaseHandler

@route('/(iphone|android)/$')
class SmartphoneHandler(BaseHandler):
    def get(self, device_name):
        options = self.get_base_options()
        if options.get('user'):
            options['available_tags'] = self.get_all_available_tags(options['user'])
        self.render('smartphone/index.html', **options)
        
        
#@route('/smartphone/auth/login/')
#class SmartphoneAuthLoginHander(AuthLoginHandler):
#    
#    def post(self):
#        super(SmartphoneAuthLoginHander, self).post()
        
        