from models import UserSettings
from mongokit import Connection
con = Connection()
con.register([UserSettings])


collection = con.worklog.user_settings
print "Fixing", collection.UserSettings.find({'disable_sound':{'$exists': False}}).count(), "objects"
for each in collection.UserSettings.find({'disable_sound':{'$exists': False}}):
    each['disable_sound'] = False
    each.save()
