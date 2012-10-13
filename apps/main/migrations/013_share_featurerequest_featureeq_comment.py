from bson.objectid import ObjectId
from apps.main.models import User, Share, FeatureRequest, FeatureRequestComment, connection
import settings

db = connection[settings.DATABASE_NAME]
collection = db.Share.collection
collection.drop_indexes()
collection = db.FeatureRequest.collection
collection.drop_indexes()
collection = db.FeatureRequestComment.collection
collection.drop_indexes()

c = 0
for msg in db.Share.find():
    if msg['users'] and type(msg['users'][0]) is not ObjectId:
        msg['users'] = [x.id for x in msg['users']]
    if type(msg['user']) is not ObjectId:
        msg['user'] = msg['user'].id
        msg.save()
        c += 1


print "Fixed", c, "shares"


c = 0
for msg in db.FeatureRequest.find():
    if type(msg['author']) is not ObjectId:
        msg['author'] = msg['author'].id
        msg.save()
        c += 1

print "Fixed", c, "feature requests"

c = 0
for msg in db.FeatureRequestComment.find():
    if type(msg['user']) is not ObjectId:
        msg['user'] = msg['user'].id
        msg.save()
        c += 1

print "Fixed", c, "feature request comments"
