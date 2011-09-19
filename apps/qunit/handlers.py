from glob import glob
import os
import tornado.web

from tornado_utils.routes import route

@route('/qunit/?')
class QUnitHandler(tornado.web.RequestHandler):
    def get(self):
        tmpl_dir = os.path.normpath(os.path.join(__file__, '../../templates/qunit'))
        tmpls = glob(tmpl_dir + '/*.html')

        options = {'urls':[]}
        for tmpl in tmpls:
            if tmpl.endswith('index.html'):
                continue
            basename = os.path.basename(tmpl)
            options['urls'].append(self.reverse_url('qunit_file', basename))

        self.render('qunit/index.html', **options)

@route('/qunit/(\w+\.html)', name="qunit_file")
class QUnitHandler(tornado.web.RequestHandler):
    def get(self, filename):
        self.render(os.path.join('qunit', filename))
