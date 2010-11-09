from models import Event
from mongokit import Connection
con = Connection()
con.register([Event])


db = con.worklog
print "Fixing", db.Event.find({'description':{'$exists': False}}).count(), "objects"
for each in db.Event.find({'description':{'$exists': False}}):
    each['description'] = u""
    each.save()
