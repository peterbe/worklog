TITLE = u"DoneCal"
APPS = (
  'main',
  'smartphone',
  'emailreminders',
)

LOGIN_URL = "/auth/login"

COOKIE_SECRET = "11oETzKsXQAGaYdkL5gmGeJJFuYh7EQnp2XdTP1o/Vo="

WEBMASTER = 'noreply@donecal.com'

EMAIL_REMINDER_SENDER = 'reminder@donecal.com'
EMAIL_REMINDER_REPLY_TO = 'reminder+%(id)s@donecal.com'