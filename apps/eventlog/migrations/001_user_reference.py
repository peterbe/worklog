from pymongo.objectid import ObjectId
from apps.main.models import connection
import apps.eventlog.models
import settings

db = connection[settings.DATABASE_NAME]
collection = db.EventLog.collection
collection.drop_indexes()

c = 0
for msg in db.EventLog.find():
    if type(msg['user']) is ObjectId:
        pass
    else:
        if isinstance(msg, dict):
            msg['user'] = msg['user']['_id']
            msg.save()
            c += 1
        else:
            print repr(msg['user']), type(msg['user'])

print "Fixed", c
