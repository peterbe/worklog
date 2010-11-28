#!/usr/bin/env python
import os
import boto


class CloudFront(object):
    def __init__(self, aws_access_key, aws_access_secret):
        self.aws_access_key = aws_access_key
        self.aws_access_secret = aws_access_secret
        self._cf_connection = None
        self._cf_distribution = None
        
    def get_connection(self):
        if self._cf_connection is None:
            self._cf_connection = boto.connect_cloudfront(self.aws_access_key,
                                                     self.aws_access_secret)
                 
        return self._cf_connection
    

def _upload_to_cloudfront(filepath):
    settings.AWS_ACCESS_KEY,
    settings.AWS_ACCESS_SECRET
    settings.AWS_STORAGE_BUCKET_NAME

    
#def upload(filepaths):
    #connection = Connection(key, secret)
    #for filepath in filepaths:
 
def test():
    AWS_ACCESS_KEY = 'AKIAIRKHWFILXYLI3UCQ'
    AWS_ACCESS_SECRET = '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'
    cf = CloudFront(AWS_ACCESS_KEY, AWS_ACCESS_SECRET)
    
    #     def create_custom_distribution(self, dns_name, enabled, caller_reference='',
    #                                    cnames=None, comment='',
    #                                    use_https=False, port=None ):
    
    connection = cf.get_connection()
    print "DIR IDENTITY/ORIGIN"
    print [x for x in dir(connection) if x.lower().count('identity') or x.lower().count('origin')]
    print "DIR CONNECTION CONFIG"
    print [x for x in dir(connection) if x.lower().count('config')]

    
    #print connection.set_origin_access_identity_info()
    
    dist = connection.create_custom_distribution('donecal.com', True)
    dist.update()
    #bar = connection.create_origin_access_identity()
    #oai = connection.get_origin_access_identity_info(bar)
    #print "DIR CONNECTION CONFIG"
    #print [x for x in dir(dist) if x.lower().count('config')]
    #dist.config.origin_access_identity = None
    #dist.update(origin_access_identity=oai)
    
    #print repr(dist)
    print dir(dist)
    
    filepath = 'combined/fullcalendar.calendar.1290946713.js'
    basename = os.path.basename(filepath)
    fp = open(filepath)
        
    # Because the name will always contain a timestamp we set faaar future
    # caching headers. Doesn't matter exactly as long as it's really far future.
    headers = {'Cache-Control':'max-age=315360000, public',
               'Expires': 'Thu, 31 Dec 2037 23:55:55 GMT',
    }
    
    #print "\t\t\tAWS upload(%s)" % basename
    obj = dist.add_object(basename, fp, headers=headers)
    
    url = obj.url()
    fp.close()
    return url

                                          
    #print dist.get_objects()
    
if __name__=='__main__':
    test()