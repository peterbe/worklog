from utils.routes import route
from apps.main.handlers import BaseHandler

@route('/(iphone|android)/$')
class SmartphoneHandler(BaseHandler):
    def get(self, device_name):
        options = self.get_base_options()
        
        template = 'smartphone/index.html'
        if options.get('user'):
            options['available_tags'] = self.get_all_available_tags(options['user'])
            template = 'smartphone/logged_in.html'

        self.render(template, **options)
        
        
#@route('/smartphone/auth/login/')
#class SmartphoneAuthLoginHander(AuthLoginHandler):
#    
#    def post(self):
#        super(SmartphoneAuthLoginHander, self).post()
        
        