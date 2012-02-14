import datetime
from pymongo.objectid import ObjectId
from apps.main.models import BaseDocument, register
#git log master --date=short --pretty=format:"%h%x09%an%x09%ad%x09%s"


@register
class GitHubRepo(BaseDocument):
    __collection__ = 'githubrepos'
    structure = {
      'username': unicode,
      'repo': unicode,
      'branch': unicode,
      'full_url': unicode,
      'last_pull_date': datetime.datetime,
      'last_load_date': datetime.datetime,
    }
    required_fields = ['username', 'repo']
    default_values = {
      'branch': u'master',
    }

#git log master --date=short --pretty=format:"%h%x09%an%x09%ad%x09%s"
