import datetime
import tornado.web
import tornado.escape
from tornado_utils.timesince import smartertimesince
from tornado_utils import format_time_ampm
from utils.truncate import truncate_words
import markdown
from tornado_utils.tornado_static import (
  StaticURL, Static, PlainStaticURL, PlainStatic, Static64
)

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
    def render(self, user=None):
        return self.render_string("modules/footer.html",
          calendar_link=self.request.path != '/',
          user=user,
         )

class TruncateWords(tornado.web.UIModule):
    def render(self, string, max_words=20):
        return truncate_words(string, max_words)

class TruncateString(tornado.web.UIModule):
    def render(self, string, max_length=30):
        if len(string) > max_length:
            return string[:max_length] + '...'
        return string

class Settings(tornado.web.UIModule):
    def render(self, settings):
        return self.render_string("modules/settings.html",
           settings_json=tornado.escape.json_encode(settings),
           debug=self.handler.application.settings['debug']
         )

class TimeSince(tornado.web.UIModule):
    def render(self, date, date2=None):
        return smartertimesince(date, date2)

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





class RenderText(tornado.web.UIModule):
    def render(self, text, format='plaintext'):
        if format == 'markdown':
            return markdown.markdown(text, safe_mode="escape")
        else:
            # plaintext
            html = '<p>%s</p>' % tornado.escape.linkify(text).replace('\n','<br>\n')

        return html

class ShowFeatureRequest(tornado.web.UIModule):
    def render(self, feature_request):
        comments = []
        _search = {'feature_request.$id': feature_request._id}
        thanks_instead = False
        user = self.handler.get_current_user()
        votes_count = feature_request.db.FeatureRequestComment.find(_search).count()
        for feature_request_comment in feature_request\
          .db.FeatureRequestComment.find(_search).sort('add_date', 1):
            if feature_request_comment.comment:
                comment = dict(comment=feature_request_comment.comment,
                           first_name=feature_request_comment.user.first_name)
                comments.append(comment)
            if user:
                # if you recently submitted this comment, set thanks_instead=True
                if user == feature_request_comment.user:
                    # how long ago?
                    diff = datetime.datetime.now() - feature_request_comment.modify_date
                    if not diff.days and diff.seconds < 60:
                        thanks_instead = True
        return self.render_string('featurerequests/feature_request.html',
            feature_request=feature_request,
            comments=comments,
            votes_count=votes_count,
            thanks_instead=thanks_instead)


class _Link(dict):
    __slots__ = ('label','link','is_on')
    def __init__(self, label, link, is_on):
        self.label = label
        self.link = link
        self.is_on = is_on

class HelpSeeAlsoLinks(tornado.web.UIModule):
    def render(self):
        links = []
        current_path = self.request.path
        # add a is_on bool
        for each in self.handler.get_see_also_links():
            link = each['link']
            if not link.startswith('/help'):
                link = '/help' + link
            is_on = link == current_path
            links.append(dict(link=link,
                              label=each['label'],
                              is_on=is_on))

        return self.render_string("help/see_also.html",
          links=links
        )

class HelpPageTitle(tornado.web.UIModule):
    def render(self):
        links = []
        current_path = self.request.path
        for each in self.handler.get_see_also_links():
            link = each['link']
            if not link.startswith('/help'):
                link = '/help' + link
            if link == current_path:
                return "%s - DoneCal" % each['label']

        return "Help on DoneCal"

class ShowUserName(tornado.web.UIModule):
    def render(self, user, first_name_only=False, anonymize_email=False):
        if first_name_only:
            name = user.first_name
        else:
            name = u'%s %s' % (user.first_name, user.last_name)
            name = name.strip()

        if not name:
            name = user.email
            if not name:
                name = "*Someone anonymous*"
            elif anonymize_email:
                name = name[:3] + '...@...' + name.split('@')[1][3:]
        return name


class ShowTime(tornado.web.UIModule):
    def render(self, time_):
        assert isinstance(time_, list), type(time_)
        assert len(time_) == 2, len(time_)
        ampm_format = False

        user = self.handler.get_current_user()
        if user:
            user_settings = self.handler\
              .get_current_user_settings(user=user, fast=True)
            if user_settings:
                ampm_format = \
                  user_settings.get('ampm_format', ampm_format)


        if ampm_format:
            return format_time_ampm(time_)
            #if h > 12:
            #    h -= 12
            #    ampm = 'pm'
            #else:
            #    ampm = 'am'
            #if m:
            #    return "%s.%s%s" % (h, m, ampm)
            #else:
            #    return "%s%s" % (h, ampm)
        else:
            h = time_[0]
            m = time_[1]
            if not m:
                m = '00'
            return "%s:%s" % (h, m)


class CheckoutCode(tornado.web.UIModule):
    def render(self, code, currency):
        for product in self.handler.get_products():
            if product['code'] == code:
                price = product['price']
                description = product['description']

        return self.render_string("premium/checkout.html",
          code=code,
          currency=currency,
          price=price,
          description=description,
        )
