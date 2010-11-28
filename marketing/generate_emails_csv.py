from mongokit import *
from models import *
con.register([Event,User])
users =db.User.find({'email':{'$ne':None}})
emails=[]
for user in users:
    c=db.Event.find({'user.$id':user._id}).count()
    emails.append((user.email, c, user.first_name, user.last_name, user.add_date))
    
import csv
out=open('emails.csv','w')
writer=csv.writer(out)
writer.writerow(['Email','# events', 'First', 'Last', 'Add date'])
for email, count, first, last, date in emails:
    row=[email.encode('utf8'), count, first.encode('utf8'), last.encode('utf8'), date.isoformat()]
    writer.writerow(row)
out.close()
    
