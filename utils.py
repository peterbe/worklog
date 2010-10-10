import re
import bcrypt
import datetime

class DatetimeParseError(Exception):
    pass

_timestamp_regex = re.compile('\d{13}|\d{10}\.\d{0,4}|\d{10}')
def parse_datetime(datestr):
    _parsed = _timestamp_regex.findall(datestr)
    if _parsed:
        datestr = _parsed[0]
        if len(datestr) >= len('1285041600000'):
            return datetime.datetime.fromtimestamp(float(datestr)/1000)
        if len(datestr) >= len('1283140800'):
            return datetime.datetime.fromtimestamp(float(datestr))
    
    
    raise DatetimeParseError(datestr)


def encrypt_password(raw_password, log_rounds=10): 
    salt = bcrypt.gensalt(log_rounds=log_rounds)
    hsh = bcrypt.hashpw(raw_password, salt)
    algo = 'bcrypt'
    return u'%s$bcrypt$%s' % (algo, hsh)   