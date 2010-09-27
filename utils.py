import datetime


def parse_datetime(datestr):
    if datestr.isdigit() and len(datestr) >= len('1285041600000'):
        return datetime.datetime.fromtimestamp(float(datestr)/1000)
    
    
    raise NotImplementedError