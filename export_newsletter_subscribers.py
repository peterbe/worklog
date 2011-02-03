from apps.main.models import User, UserSettings
from mongokit import Connection
con = Connection()
con.register([User, UserSettings])
db = con.worklog

for user_settings in db.UserSettings.find({'newsletter_opt_out':False}):
    user = user_settings.user
    if user.email is None:
        continue
    bits = [user.email]
    bits.append(user.first_name and user.first_name or u'')
    bits.append(user.last_name and user.last_name or u'')
    out = "\t".join(bits)
    print out.encode('utf8')
