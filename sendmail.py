#!/usr/bin/env python
import sys
import datetime
import urllib2

def run(*args):
    email_content = sys.stdin.read()
    f =open('/tmp/sendmail.py.log','a')
    f.write("%s\n" % datetime.datetime.now().isoformat())
    f.write("ARGS: %s\n" % str(args))
    f.write(email_content)
    try:
        url = 'http://donecal.com/emailreminders/receive/'
        req = urllib2.Request(url, email_content)
        response = urllib2.urlopen(req)
        f.write(response.read())
    finally:
        
        f.write('\n')
        f.close()
    


if __name__ == '__main__':
    import sys
    sys.exit(run(*sys.argv[1:]))