import bcrypt
import datetime


def parse_datetime(datestr):
    if datestr.isdigit():
        if len(datestr) >= len('1285041600000'):
            return datetime.datetime.fromtimestamp(float(datestr)/1000)
        if len(datestr) >= len('1283140800'):
            return datetime.datetime.fromtimestamp(float(datestr))
    
    raise NotImplementedError


def encrypt_password(raw_password, log_rounds=10): 
    salt = bcrypt.gensalt(log_rounds=log_rounds)
    hsh = bcrypt.hashpw(raw_password, salt)
    algo = 'bcrypt'
    return u'%s$bcrypt$%s' % (algo, hsh)   