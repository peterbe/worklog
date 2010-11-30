#!/usr/bin/env python
#


# python
import re
import os.path
from mongokit import Connection

# tornado
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options

# app
from utils.routes import route
from utils.git import get_git_revision

################################################################################

define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=8000, help="run on the given port", type=int)
define("database_name", default="worklog", help="mongodb database name")
define("prefork", default=False, help="pre-fork across all CPUs", type=bool)
define("showurls", default=False, help="Show all routed URLs", type=bool)
define("dont_combine", default=False, help="Don't combine static resources", type=bool)




class Application(tornado.web.Application):
    def __init__(self, 
                 database_name=None, 
                 xsrf_cookies=True, 
                 optimize_static_content=None):
        ui_modules_map = {}
        for app_name in ('apps.main',):
            _ui_modules = __import__(app_name, globals(), locals(), ['ui_modules'], -1)
            ui_modules = _ui_modules.ui_modules
    
            for name in [x for x in dir(ui_modules) if re.findall('[A-Z]\w+', x)]:
                thing = getattr(ui_modules, name)
                try:
                    if issubclass(thing, tornado.web.UIModule):
                        ui_modules_map[name] = thing
                except TypeError:
                    # most likely a builtin class or something
                    pass
            
        if options.dont_combine:
            ui_modules_map['Static'] = ui_modules_map['PlainStatic']
            ui_modules_map['StaticURL'] = ui_modules_map['PlainStaticURL']
            
        # unless explicitly set, then if in debug mode, disable optimization
        # of static content
        if optimize_static_content is None:
            optimize_static_content = not options.debug
            
        handlers = route.get_routes()
        settings = dict(
            title=u"DoneCal",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules=ui_modules_map,
            xsrf_cookies=xsrf_cookies,
            cookie_secret="11oETzKsXQAGaYdkL5gmGeJJFuYh7EQnp2XdTP1o/Vo=",
            login_url="/auth/login",
            debug=options.debug,
            optimize_static_content=optimize_static_content,
            git_revision=get_git_revision(),
            email_backend=options.debug and \
                 'utils.send_mail.backends.console.EmailBackend' \
              or 'utils.send_mail.backends.smtp.EmailBackend',
            webmaster='noreply@donecal.com',
            CLOSURE_LOCATION=os.path.join(os.path.dirname(__file__), 
                                      "static", "compiler.jar"),
            YUI_LOCATION=os.path.join(os.path.dirname(__file__),
                                      "static", "yuicompressor-2.4.2.jar"),
            UNDOER_GUID=u'UNDOER', # must be a unicode string
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        
        # Have one global connection to the blog DB across all handlers
        self.database_name = database_name and database_name or options.database_name
        self.con = Connection()
        self.con.register([Event, User, UserSettings, Share,
                           FeatureRequest, FeatureRequestComment])

from apps.main.models import *
from apps.main import handlers
from apps.smartphone import handlers
        
def main():
    tornado.options.parse_command_line()
    if options.showurls:
        for path, class_ in route.get_routes():
            print path
        return
    http_server = tornado.httpserver.HTTPServer(Application())
    print "Starting tornado on port", options.port
    if options.prefork:
        print "\tpre-forking"
        http_server.bind(options.port)
        http_server.start()
    else:
        http_server.listen(options.port)
    
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

    