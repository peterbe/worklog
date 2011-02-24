import os
import re
from collections import defaultdict
def run(directory, verbose):
    names = defaultdict(list)
    for f in os.listdir(directory):
        ff = os.path.join(directory, f)
        if os.path.isdir(ff):
            run(ff, verbose)
        elif os.path.isfile(ff):
            wo = re.sub('\d{10}\.', '', f)
            d = int(re.findall('(\d{10})\.', f)[0])
            names[wo].append((d, ff))
    #from pprint import pprint
    #pprint(dict(names))
    for name, versions in names.items():
        #print name
        versions.sort()
        versions.reverse()
        #pprint(versions[1:])
        for ts, oldname in versions[1:]:
            #print "\t", oldname
            if verbose:
                print "DELETE", oldname
            os.remove(oldname)
    return 0
if __name__ == '__main__':
    import sys
    directory = sys.argv[1]
    args = sys.argv[2:]
    if '-v' in args or '--verbose' in args:
        verbose = True
    else:
        verbose = False
    sys.exit(run(directory, verbose))