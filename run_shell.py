#!/usr/bin/env python

import code, re

if __name__ == '__main__':
    
    from apps.main.models import *
    from apps.main import models
    
    from apps.emailreminders.models import EmailReminder
    from mongokit import Connection, Document as mongokit_Document
    from pymongo.objectid import InvalidId, ObjectId
    con = Connection()
    
    import settings
    model_classes = []
    for app_name in settings.APPS:
        _models = __import__('apps.%s' % app_name, globals(), locals(),
                                 ['models'], -1)
        try:
            models = _models.models
        except AttributeError:
            # this app simply doesn't have a models.py file
            continue
        for name in [x for x in dir(models) if re.findall('[A-Z]\w+', x)]:
            thing = getattr(models, name)
            if issubclass(thing, mongokit_Document):
                model_classes.append(thing)
                
    con.register(model_classes)

                
    db = con.worklog
    print "AVAILABLE:"
    print '\n'.join(['\t%s'%x for x in locals().keys() 
                     if re.findall('[A-Z]\w+|db|con', x)])
    print "Database available as 'db'"
    code.interact(local=locals())