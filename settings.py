TITLE = u"DoneCal"
APPS = (
  'main',
  'smartphone',
  'emailreminders',
)

LOGIN_URL = "/auth/login"

COOKIE_SECRET = "11oETzKsXQAGaYdkL5gmGeJJFuYh7EQnp2XdTP1o/Vo="

WEBMASTER = 'noreply@donecal.com'

EMAIL_REMINDER_SENDER = 'reminder+%(id)s@donecal.com'