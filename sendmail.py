#!/usr/bin/env python
import sys
import datetime
import urllib2

def main(domain=None, protocol=None):
    if not domain:
        domain = 'donecal.com'
    if not protocol:
        protocol = 'http'
    email_content = sys.stdin.read()
    f =open('/tmp/sendmail.py.log','a')
    f.write("%s\n" % datetime.datetime.now().isoformat())
    #f.write("ARGS: %s\n" % str(args))
    f.write(email_content)
    try:
        url = '%s://%s/emailreminders/receive/' % (protocol, domain)
        print repr(url)
        req = urllib2.Request(url, email_content)
        response = urllib2.urlopen(req)
        f.write(response.read())
    finally:
        
        f.write('\n')
        f.close()
    
def run(*args):
    domain = None
    protocol = None
    _next_is_domain = False
    _next_is_protocol = False
    for arg in args:
        if _next_is_domain:
            domain = arg
            _next_is_domain = False
        elif _next_is_protocol:
            protocol = arg
            _next_is_protocol = False
        elif arg in ('--domain', '-d'):
            _next_is_domain = True
        elif arg in ('--protocol', '-p'):
            _next_is_protocol = True
            
    main(domain=domain, protocol=protocol)

if __name__ == '__main__':
    import sys
    sys.exit(run(*sys.argv[1:]))