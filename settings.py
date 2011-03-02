TITLE = u"DoneCal"
APPS = (
  'main',
  'smartphone',
  'emailreminders',
  'eventlog',
)

LOGIN_URL = "/auth/login"

COOKIE_SECRET = "11oETzKsXQAGaYdkL5gmGeJJFuYh7EQnp2XdTP1o/Vo="

WEBMASTER = 'noreply@donecal.com'
ADMIN_EMAILS = ['peterbe@gmail.com']

EMAIL_REMINDER_SENDER = 'reminder+%(id)s@donecal.com'
EMAIL_REMINDER_NOREPLY = 'noreplyplease@donecal.com'

# if you do this, for the static files, instead of getting something like
# '/static/foo.png?v=123556' we get '/static/v-123556/foo.png'
EMBED_STATIC_URL_TIMESTAMP = True