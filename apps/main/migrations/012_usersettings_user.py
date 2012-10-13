from bson.objectid import ObjectId
from apps.main.models import User, UserSettings, connection
import settings

db = connection[settings.DATABASE_NAME]
collection = db.UserSettings.collection
collection.drop_indexes()

c = 0
for msg in db.UserSettings.find():
    if type(msg['user']) is not ObjectId:
        msg['user'] = msg['user'].id
        msg.save()
        c += 1

print "Fixed", c
