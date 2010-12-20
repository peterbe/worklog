#!/usr/bin/env python

import code, re

if __name__ == '__main__':
    
    from apps.main.models import *
    from mongokit import Connection
    from pymongo.objectid import InvalidId, ObjectId
    con = Connection()
    db = con.worklog
    print "AVAILABLE:"
    print '\n'.join(['\t%s'%x for x in locals().keys() 
                     if re.findall('[A-Z]\w+|db|con', x)])
    print "Database available as 'db'"
    code.interact(local=locals())