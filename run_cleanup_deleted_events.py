#!/usr/bin/env python
import datetime
from mongokit import Connection
from apps.main.models import User, Event

def get_db():
    con = Connection()
    con.register([User, Event])
    return con['worklog']

def main(verbose=True):
    db = get_db()
    undoer = db.User.one({'guid': u"UNDOER"})
    search = {'user.$id': undoer._id}
    minute_ago = datetime.datetime.now()
    minute_ago -= datetime.timedelta(minutes=1)
    search['add_date'] = {'$lt': minute_ago}
    if verbose:
        print "Removing", db.Event.find(search).count(), "events"
        
    db[Event.__collection__].remove(search)
    
    

def run(*args):
    verbose = True
    if '-q' in args or '--quiet' in args:
        verbose = False
    main(verbose=verbose)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(run(*sys.argv[1:]))