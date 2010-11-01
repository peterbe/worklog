from models import UserSettings
from mongokit import Connection
con = Connection()
con.register([UserSettings])


collection = con.worklog.user_settings
print "Fixing", collection.UserSettings.find({'offline_mode':{'$exists': False}}).count(), "objects"
for each in collection.UserSettings.find({'offline_mode':{'$exists': False}}):
    each['offline_mode'] = False
    each.save()
