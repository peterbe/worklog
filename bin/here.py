import site
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
path = lambda *a: os.path.join(ROOT,*a)
site.addsitedir(path('.'))
site.addsitedir(path('vendor'))
