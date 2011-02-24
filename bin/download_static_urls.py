#!/usr/bin/env python
from time import time
import lxml.html
from lxml import etree
from lxml.cssselect import CSSSelector
from urllib import urlopen
from urlparse import urlparse

def wrap(url, uri):
    if uri.startswith('/'):
        parts = list(urlparse(url))
        parts[2] = uri
        url = parts[0]
        url += '://'
        if parts[2].startswith('//'):
            url += parts[2][2:]
        else:
            url += parts[1]
            url += parts[2]
    return url

def get_static_urls(url):
    html = urlopen(url).read()
    parser = etree.HTMLParser()
    tree = etree.fromstring(html.strip(), parser).getroottree()
    page = tree.getroot()
    for link in CSSSelector('link')(page):
        yield wrap(url, link.attrib['href'])
        
    for link in CSSSelector('script')(page):
        
        try:
            src = wrap(url, link.attrib['src'])
            if not src.count('googleapis'):
                yield wrap(url, link.attrib['src'])
        except KeyError:
            # block
            pass
        
    
def main(*args):
    for arg in args:
        for url in get_static_urls(arg):
            #print url
            #continue
            t0=time()
            content = urlopen(url).read()
            t1=time()
            t = round((t1-t0) * 1000, 2)
            print ("%s Kb" % (len(content)/1024)).ljust(10),
            print ("%sms"%t).ljust(10),
            print url#, "%sms"%t, "%s Kb" % (len(content)/1024)
    return 0
if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))