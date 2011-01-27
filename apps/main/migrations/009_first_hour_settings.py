from apps.main.models import UserSettings
from mongokit import Connection
con = Connection()
con.register([UserSettings])


collection = con.worklog.user_settings
print "Fixing", collection.UserSettings.find({'first_hour':{'$exists': False}}).count(), "objects"
for each in collection.UserSettings.find({'first_hour':{'$exists': False}}):
    each['first_hour'] = 8
    each.save()
