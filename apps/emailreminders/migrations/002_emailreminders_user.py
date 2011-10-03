from pymongo.objectid import ObjectId
from apps.main.models import connection
import apps.emailreminders.models
import settings

db = connection[settings.DATABASE_NAME]
collection = db.EmailReminder.collection
collection.drop_indexes()

c = 0
for msg in db.EmailReminder.find():
    if type(msg['user']) is not ObjectId:
        msg['user'] = msg['user'].id
        msg.save()
        c += 1

print "Fixed", c
