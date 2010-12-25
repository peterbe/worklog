#!/usr/bin/env python
import boto

def create_domain(base_domain, use_https=False):
    AWS_ACCESS_KEY = 'AKIAIRKHWFILXYLI3UCQ'
    AWS_ACCESS_SECRET = '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'
    cf = CloudFront(AWS_ACCESS_KEY, AWS_ACCESS_SECRET)
    connection = cf.get_connection()
    dist = connection.create_custom_distribution(base_domain, True, use_https=use_https)
    print dist.domain_name
    
if __name__=='__main__':
    create_domain('donecal.com', use_https=True)