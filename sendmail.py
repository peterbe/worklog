#!/usr/bin/env python
import sys
import datetime
import urllib2
import os.path

import logging
LOG_DIR = '/tmp'
LOG_FILENAME = 'sendmail.py.log'
logging.basicConfig(filename=os.path.join(LOG_DIR, LOG_FILENAME),
                    level=logging.DEBUG,
                    datefmt="%Y-%m-%d %H:%M:%S",
                    format="%(asctime)s %(levelname)s %(name)s %(message)s",
                   )


def main(domain=None, protocol=None):
    if not domain:
        domain = 'donecal.com'
    if not protocol:
        protocol = 'http'
    now = datetime.datetime.now()
    save_as_file = os.path.join(LOG_DIR, 
      now.strftime('%Y-%m-%d_%H%M%S_%f.email'))
    open(save_as_file, 'w').write(sys.stdin.read())
    logging.debug("Incoming email (%s)" % save_as_file)
    url = '%s://%s/emailreminders/receive/' % (protocol, domain)
    req = urllib2.Request(url, open(save_as_file).read())
    try:
        response = urllib2.urlopen(req)
        logging.info(response.read())
    except:
        logging.error(
          "Error on opening receiver. Look into %s" % save_as_file,
          exc_info=True)
    
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