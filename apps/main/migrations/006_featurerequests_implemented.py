from apps.main.models import FeatureRequest
from mongokit import Connection
con = Connection()
con.register([FeatureRequest])


db = con.worklog
print "Fixing", db.FeatureRequest.find({'implemented':{'$exists': False}}).count(), "objects"
for each in db.FeatureRequest.find({'implemented':{'$exists': False}}):
    each['implemented'] = False
    each.save()
