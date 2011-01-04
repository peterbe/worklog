from apps.emailreminders.models import EmailReminder
from mongokit import Connection
con = Connection()
con.register([EmailReminder])


collection = con.worklog[EmailReminder.__collection__]
print "Fixing", collection.EmailReminder.find({'include_instructions':{'$exists': False}}).count(), "objects"
for each in collection.EmailReminder.find({'include_instructions':{'$exists': False}}):
    each['include_instructions'] = True
    each['include_summary'] = False
    each.save()

