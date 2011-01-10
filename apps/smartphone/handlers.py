from utils.routes import route
from apps.main.handlers import BaseHandler, AuthLoginHandler, CredentialsError

@route('/(iphone|android)/$')
class SmartphoneHandler(BaseHandler):
    def get(self, device_name):
        options = self.get_base_options()
        
        template = 'smartphone/index.html'
        #if options.get('user'):
        #    options['available_tags'] = self.get_all_available_tags(options['user'])
        #    template = 'smartphone/logged_in.html'

        self.render(template, **options)
        

@route('/(iphone|android)/auth/login/$')
class SmartphoneAuthLoginHandler(AuthLoginHandler):
    def post(self, device_name):
        # if this works it will set a cookie. Is that needed???
        # if not, consider rewriting AuthLoginHandler so that it can
        # check but not set a cookie or something
        try:
            user = self.check_credentials(self.get_argument('email'),
                                          self.get_argument('password'))
        except CredentialsError, msg:
            return self.write_json(dict(error="Error: %s" % msg))
            
        print "SIGNED", repr(self.create_signed_value('guid', user.guid))
        self.write_json(dict(guid=self.create_signed_value('guid', user.guid)))
        
@route('/(iphone|android)/checkguid/$')
class CheckGUIDHandler(BaseHandler):
    def get(self, __):
        guid = self.get_argument('guid')
        if guid.count('|') == 2:
            guid = self.get_secure_cookie('guid', value=guid)
        user = self.db.User.one({'guid': guid})
        self.write_json(dict(ok=bool(user)))

        
#@route(r'/(iphone|android)/events(\.json|\.js|\.xml|\.txt|/)?')
#class SmartphoneEventsHandler(EventsHandler):
#    def get(self, device_name, format=None):
        
        
#@route('/smartphone/auth/login/')
#class SmartphoneAuthLoginHander(AuthLoginHandler):
#    
#    def post(self):
#        super(SmartphoneAuthLoginHander, self).post()
        
        