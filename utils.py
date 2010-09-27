import datetime


def parse_datetime(datestr):
    if datestr.isdigit():
        if len(datestr) >= len('1285041600000'):
            return datetime.datetime.fromtimestamp(float(datestr)/1000)
        if len(datestr) >= len('1283140800'):
            return datetime.datetime.fromtimestamp(float(datestr))
    
    raise NotImplementedError