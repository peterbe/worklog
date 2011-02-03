from apps.main.models import UserSettings
from mongokit import Connection
con = Connection()
con.register([UserSettings])


collection = con.worklog.user_settings
print "Fixing", collection.UserSettings.find({'newsletter_opt_out':{'$exists': False}}).count(), "objects"
for each in collection.UserSettings.find({'newsletter_opt_out':{'$exists': False}}):
    each['newsletter_opt_out'] = False
    each.save()
