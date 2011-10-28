TITLE = u"DoneCal"
APPS = (
  'main',
  'smartphone',
  'emailreminders',
  'eventlog',
  'qunit',
)

DATABASE_NAME = "worklog"

LOGIN_URL = "/auth/login/"

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

COOKIE_SECRET = "11o3TzKsxQAGAYdkl5gmGEJJFu4h7EQnp1XdTP10/"

WEBMASTER = 'noreply@donecal.com'
ADMIN_EMAILS = ['peterbe@gmail.com']

EMAIL_REMINDER_SENDER = 'reminder+%(id)s@donecal.com'
EMAIL_REMINDER_NOREPLY = 'noreplyplease@donecal.com'

# commented out because it's on by default but driven by dont_embed_static_url option instead
## if you do this, for the static files, instead of getting something like
## '/static/foo.png?v=123556' we get '/static/v-123556/foo.png'
#EMBED_STATIC_URL_TIMESTAMP = True

try:
    from local_settings import *
except ImportError:
    pass
