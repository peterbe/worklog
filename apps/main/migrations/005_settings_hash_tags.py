from apps.main.models import UserSettings
from mongokit import Connection
con = Connection()
con.register([UserSettings])

collection = con.worklog.user_settings
print "Fixing", collection.UserSettings.find({'hash_tags':{'$exists': False}}).count(), "objects"
for each in collection.UserSettings.find({'hash_tags':{'$exists': False}}):
    each['hash_tags'] = False
    each.save()
