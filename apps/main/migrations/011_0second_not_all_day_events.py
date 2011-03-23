from apps.main.models import Event
from apps.main.config import MINIMUM_DAY_SECONDS
from mongokit import Connection
con = Connection()
con.register([Event])


collection = con.worklog.events
qs = collection.Event.find({'all_day':True, '$where':'this.start.getTime()==this.end.getTime()'})
print "Faxing", qs.count(), "objects"
for event in qs:
    assert event.start == event.end
    assert event.all_day
    # not all-day events with start==end *appear* like 2 hour events
    event.end += datetime.timedelta(hours=2)#seconds=MINIMUM_DAY_SECONDS)
    event.save()
