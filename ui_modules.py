import datetime
import re
from base64 import encodestring
import stat
import cPickle
from time import time
import os
from tempfile import gettempdir
import tornado.web
import tornado.escape
from cStringIO import StringIO
from utils.timesince import smartertimesince
from subprocess import Popen, PIPE
from utils import mkdir
from utils.truncate import truncate_words

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
    
    
################################################################################    
# Global variable where we store the conversions so we don't have to do them 
# again every time the UI module is rendered with the same input
_name_conversion = {}

class StaticURL(tornado.web.UIModule):

    def render(self, *static_urls):
        # the following 4 lines will have to be run for every request. Since 
        # it's just a basic lookup on a dict it's going to be uber fast.
        basic_name = ''.join(static_urls)
        already = _name_conversion.get(basic_name)
        if already:
            return already
        
        new_name = self._combine_filename(static_urls)
        # If you run multiple tornados (on different ports) it's possible
        # that another process has already dealt with this static URL.
        # Therefore we now first of all need to figure out what the final name
        # is going to be 
        youngest = 0
        full_paths = []
        old_paths = {} # maintain a map of what the filenames where before
        for path in static_urls:
            full_path = os.path.join(
              self.handler.settings['static_path'], path)
            #f = open(full_path)
            mtime = os.stat(full_path)[stat.ST_MTIME]
            if mtime > youngest:
                youngest = mtime
            full_paths.append(full_path)
            old_paths[full_path] = path
            
        n, ext = os.path.splitext(new_name)
        new_name = "%s.%s%s" % (n, youngest, ext)
        
        destination = file(new_name, 'w')
        
        do_optimize_static_content = self.handler.settings\
          .get('optimize_static_content', True)
          
        if do_optimize_static_content:
            closure_location = self.handler\
              .settings.get('CLOSURE_LOCATION')
            yui_location = self.handler\
              .settings.get('YUI_LOCATION')
        
        for full_path in full_paths:
            f = open(full_path)
            code = f.read()
            if full_path.endswith('.js'):
                if len(full_paths) > 1:
                    destination.write('/* %s */\n' % os.path.basename(full_path))
                if do_optimize_static_content and not self._already_optimized_filename(full_path):
                    if closure_location:
                        code = run_closure_compiler(code, closure_location, 
                      verbose=self.handler.settings.get('debug', False))
                    elif yui_location:
                        code = run_yui_compressor(code, 'js', yui_location, 
                      verbose=self.handler.settings.get('debug', False))
            elif full_path.endswith('.css'):
                if len(full_paths) > 1:
                    destination.write('/* %s */\n' % os.path.basename(full_path))
                if do_optimize_static_content and not self._already_optimized_filename(full_path):
                    if yui_location:
                        code = run_yui_compressor(code, 'css', yui_location, 
                          verbose=self.handler.settings.get('debug', False))
                # do run this after the run_yui_compressor() has been used so that 
                # code that is commented out doesn't affect
                code = self._replace_css_images_with_static_urls(
                  code,
                  os.path.dirname(old_paths[full_path])
                  )
            else:
                raise ValueError("Unknown extension %s" % full_path)
            destination.write(code)
            destination.write("\n")
            
        destination.close()
        prefix = self.handler.settings.get('combined_static_url_prefix', '/combined/')
        new_name = os.path.join(prefix, os.path.basename(new_name))
        _name_conversion[basic_name] = new_name
        return new_name
    

    def _combine_filename(self, names, max_length=60):
        # expect the parameter 'names' be something like this:
        # ['css/foo.css', 'css/jquery/datepicker.css']
        # The combined filename is then going to be 
        # "/tmp/foo.datepicker.css"
        first_ext = os.path.splitext(names[0])[-1]
        save_dir = self.handler.application.settings.get('combined_static_dir')
        if save_dir is None:
            save_dir = gettempdir()
        save_dir = os.path.join(save_dir, 'combined')
        mkdir(save_dir)
        combined_name = []
        for name in names:
            name, ext = os.path.splitext(os.path.basename(name))
            if ext != first_ext:
                raise ValueError("Mixed file extensions (%s, %s)" %\
                 (first_ext, ext))
            combined_name.append(name)
        if sum(len(x) for x in combined_name) > max_length:
            combined_name = [x.replace('.min','.m').replace('.pack','.p')
                             for x in combined_name]
            combined_name = [re.sub(r'-[\d\.]+', '', x) for x in combined_name]
            while sum(len(x) for x in combined_name) > max_length:
                try:
                    combined_name = [x[-2] == '.' and x[:-2] or x[:-1]
                                 for x in combined_name]
                except IndexError:
                    break
        
        combined_name.append(first_ext[1:])
        return os.path.join(save_dir, '.'.join(combined_name))
    
    def _replace_css_images_with_static_urls(self, css_code, rel_dir):
        def replacer(match):
            filename = match.groups()[0]
            if (filename.startswith('"') and filename.endswith('"')) or \
              (filename.startswith("'") and filename.endswith("'")):
                filename = filename[1:-1]
            if 'data:image' in filename or filename.startswith('http://'):
                return filename
            # It's really quite common that the CSS file refers to the file 
            # that doesn't exist because if you refer to an image in CSS for
            # a selector you never use you simply don't suffer.
            # That's why we say not to warn on nonexisting files
            new_filename = self.handler.static_url(os.path.join(rel_dir, filename))
            return match.group().replace(filename, new_filename)
        _regex = re.compile('url\(([^\)]+)\)')
        css_code = _regex.sub(replacer, css_code)
        
        return css_code
    
    def _already_optimized_filename(self, file_path):
        file_name = os.path.basename(file_path)
        for part in ('.min.', '.minified.', '.pack.', '-jsmin.'):
            if part in file_name:
                return True
        print "NOT", repr(file_name)
        return False

    
class Static(StaticURL):
    """given a list of static resources, return the whole HTML tag"""
    def render(self, *static_urls):
        extension = static_urls[0].split('.')[-1]
        if extension == 'css':
            template = '<link rel="stylesheet" type="text/css" href="%(url)s">'
        elif extension == 'js':
            template = '<script type="text/javascript" src="%(url)s"></script>'
        else:
            raise NotImplementedError
        url = super(Static, self).render(*static_urls)
        return template % dict(url=url)
    
    
def run_closure_compiler(code, jar_location, verbose=False):
    if verbose:
        t0 = time()
    r = _run_closure_compiler(code, jar_location)
    if verbose:
        t1 = time()
        a, b = len(code), len(r)
        c = round(100 * float(b) / a, 1)
        print "Closure took", round(t1 - t0, 4), 
        print "seconds to compress %d bytes into %d (%s%%)" % (a, b, c)
    return r

def _run_closure_compiler(jscode, jar_location, advanced_optmization=False):
    cmd = "java -jar %s " % jar_location
    if advanced_optmization:
        cmd += " --compilation_level ADVANCED_OPTIMIZATIONS "
    proc = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    try:
        (stdoutdata, stderrdata) = proc.communicate(jscode)
    except OSError, msg:
        # see comment on OSErrors inside _run_yui_compressor()
        stderrdata = \
          "OSError: %s. Try again by making a small change and reload" % msg
    if stderrdata:
        return "/* ERRORS WHEN RUNNING CLOSURE COMPILER\n" + stderrdata + '\n*/\n' + jscode 
   
    return stdoutdata

def run_yui_compressor(code, type_, jar_location, verbose=False):
    if verbose:
        t0 = time()
    r = _run_yui_compressor(code, type_, jar_location)
    if verbose:
        t1 = time()
        a, b = len(code), len(r)
        c = round(100 * float(b) / a, 1)
        print "YUI took", round(t1 - t0, 4), 
        print "seconds to compress %d bytes into %d (%s%%)" % (a, b, c)
    return r

def _run_yui_compressor(code, type_, jar_location):    
    cmd = "java -jar %s --type=%s" % (jar_location, type_)
    proc = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    try:
        (stdoutdata, stderrdata) = proc.communicate(code)
    except OSError, msg:
        # Sometimes, for unexplicable reasons, you get a Broken pipe when
        # running the popen instance. It's always non-deterministic problem
        # so it probably has something to do with concurrency or something
        # really low level. 
        stderrdata = \
          "OSError: %s. Try again by making a small change and reload" % msg
        
    if stderrdata:
        return "/* ERRORS WHEN RUNNING YUI COMPRESSOR\n" + stderrdata + '\n*/\n' + code
    
    return stdoutdata
    

class PlainStaticURL(tornado.web.UIModule):
    def render(self, url):
        return self.handler.static_url(url)

class PlainStatic(tornado.web.UIModule):
    """Render the HTML that displays a static resource without any optimization
    or combing.
    """

    def render(self, *static_urls):
        extension = static_urls[0].split('.')[-1]
        if extension == 'css':
            template = '<link rel="stylesheet" type="text/css" href="%(url)s">'
        elif extension == 'js':
            template = '<script type="text/javascript" src="%(url)s"></script>'
        else:
            raise NotImplementedError

        html = []
        for each in static_urls:
            url = self.handler.static_url(each)
            html.append(template % dict(url=url))
        return "\n".join(html)
        
    
_base64_conversion_file = '.base64-image-conversions.pickle'
try:
    _base64_conversions = cPickle.load(file(_base64_conversion_file))
    #raise IOError
except IOError:
    _base64_conversions = {}
    
class Static64(tornado.web.UIModule):
    def render(self, image_path):
        already = _base64_conversions.get(image_path)
        if already:
            return already
        
        template = 'data:image/%s;base64,%s'
        extension = os.path.splitext(os.path.basename(image_path))
        extension = extension[-1][1:]
        assert extension in ('gif','png'), extension
        full_path = os.path.join(
              self.handler.settings['static_path'], image_path)
        data = encodestring(file(full_path,'rb').read()).replace('\n','')#.replace('\n','\\n')
        result = template % (extension, data)
        
        _base64_conversions[image_path] = result
        cPickle.dump(_base64_conversions, file(_base64_conversion_file, 'wb'))
        return result
        
        
        
class RenderText(tornado.web.UIModule):
    def render(self, text, format='plaintext'):
        if format == 'markdown':
            raise NotImplementedError('markdown?')
        else:
            # plaintext
            html = '<p>%s</p>' % tornado.escape.linkify(text).replace('\n','<br>\n')
            
        return html
    
class ShowFeatureRequest(tornado.web.UIModule):
    def render(self, feature_request):
        comments = []
        _search = {'feature_request.$id': feature_request._id,
                   'comment':{'$ne': u''}}
        thanks_instead = False
        user = self.handler.get_current_user()
        for feature_request_comment in feature_request\
          .db.FeatureRequestComment.find(_search).sort('add_date', 1):
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