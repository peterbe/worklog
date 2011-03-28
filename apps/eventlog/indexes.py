from pymongo import ASCENDING, DESCENDING
from models import EventLog
from mongokit import Connection
con = Connection()
con.register([EventLog])
db = con.worklog

def run():
    collection = db.EventLog.collection
    collection.ensure_index([('add_date',DESCENDING)])
    test()

def test():
    curs = db.EventLog.find().sort('add_date', DESCENDING).explain()['cursor']
    assert 'BtreeCursor' in curs