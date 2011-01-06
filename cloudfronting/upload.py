#!/usr/bin/env python
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

def create_domain(base_domain, use_https=False, comment=''):
    AWS_ACCESS_KEY = 'AKIAIRKHWFILXYLI3UCQ'
    AWS_ACCESS_SECRET = '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'
    cf = CloudFront(AWS_ACCESS_KEY, AWS_ACCESS_SECRET)
    connection = cf.get_connection()
    dist = connection.create_custom_distribution(base_domain, True, 
      use_https=use_https,
      comment=comment,
    )
    return dist.domain_name

def invalidate_files(distribution_id, file_paths):
    print "distribution_id", distribution_id
    print "file_paths", file_paths
    raise NotImplementedError("work harder!!!")
    
if __name__=='__main__':
    import sys
    args = sys.argv[1:]
    if '-c' in args or '--create' in args:
        comment = raw_input("Comment? (optional): ")
        if comment:
            comment = comment.strip()
        print create_domain('donecal.com', use_https=False, comment=comment)
    elif '-i' in args or '--invalidate' in args:
        print invalidate_files(args[1], args[1:])
    else:
        raise SystemError('invalid args. read source code')