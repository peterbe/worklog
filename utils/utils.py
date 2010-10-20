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


def niceboolean(value):
    if type(value) is bool:
        return value
    falseness = ('','no','off','false','none','0', 'f')
    return str(value).lower().strip() not in falseness



email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$', re.IGNORECASE)  # domain
def valid_email(email):
    return bool(email_re.search(email))
