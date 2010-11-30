from models import Event
from mongokit import Connection
con = Connection()
con.register([Event])

collection = con.worklog.events
print "Fixing", collection.Event.find({'url':{'$exists': True}}).count(), "objects"
for each in collection.Event.find({'url':{'$exists': True}}):
    del each['url']
    each.save()