import tornado.web
from utils.timesince import smartertimesince

try:
    import pygments
    import pygments.lexers
    from pygments.formatters import HtmlFormatter
    __pygments__ = True
except ImportError:
    __pygments__ = False
    #code = 'print "Hello World"'
    #print highlight(code, PythonLexer(), HtmlFormatter())
    

class Footer(tornado.web.UIModule):
    def render(self):
        return self.render_string("modules/footer.html",
          calendar_link=self.request.path != '/'
         )
         
class Settings(tornado.web.UIModule):
    def render(self, settings):
        return self.render_string("modules/settings.html",
           settings_json=tornado.escape.json_encode(settings),
         )

class EventPreview(tornado.web.UIModule):
    def render(self, event):
        add_ago = smartertimesince(event.add_date)
        user_name = ''
        if event.user.first_name:
            user_name = event.user.first_name
        elif event.user.email:
            user_name = event.user.email
        return self.render_string("modules/eventpreview.html",
          event=event, add_ago=add_ago, user_name=user_name
         )
         
         
class Syntax(tornado.web.UIModule):
    def render(self, code, lexer_name):
        if __pygments__:
            lexer = pygments.lexers.get_lexer_by_name(lexer_name)
            code = pygments.highlight(code, lexer, HtmlFormatter())
            
        else:
            code = code.replace('<','&lt;').replace('>','&gt;')\
              .replace('"','&quot;').replace('\n', '<br>')
            code = '<pre>%s</pre>' % code
        return code
    