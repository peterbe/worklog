from apps.main.models import UserSettings
from mongokit import Connection
con = Connection()
con.register([UserSettings])


collection = con.worklog.user_settings
print "Fixing", collection.UserSettings.find({'ampm_format':{'$exists': False}}).count(), "objects"
for each in collection.UserSettings.find({'ampm_format':{'$exists': False}}):
    each['ampm_format'] = False
    each.save()
