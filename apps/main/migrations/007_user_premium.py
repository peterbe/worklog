from apps.main.models import User
from mongokit import Connection
con = Connection()
con.register([User])


db = con.worklog
print "Fixing", db.User.find({'premium':{'$exists': False}}).count(), "objects"
for each in db.User.find({'premium':{'$exists': False}}):
    each['premium'] = False
    each.save()
