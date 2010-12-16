import re
from utils import valid_email

class ParseEventError(Exception):
    pass

def parse_time(text):
    time_regex_1 = re.compile('^(\d{1,2})(\.|:)(\d{2})(am|pm)\s', re.I)
    time_regex_2 = re.compile('^(\d{1,2})(am|pm)\s', re.I)
    time_regex_3 = re.compile('^(\d{1,2})(\.|:)(\d{2})\s', re.I)
    
    time_ = None
    
    if time_regex_1.findall(text):
        h, __, m, am_pm = time_regex_1.findall(text)[0]
        h = int(h)
        m = int(m)
        if am_pm.lower() == 'pm':
            h += 12
        time_ = (h, m)
        text = time_regex_1.sub('', text).strip()
    elif time_regex_2.findall(text):
        h, am_pm = time_regex_2.findall(text)[0]
        h = int(h)
        if am_pm.lower() == 'pm':
            h += 12
        time_ = (h, 0)
        text = time_regex_2.sub('', text).strip()
    elif time_regex_3.findall(text):
        h, __, m = time_regex_3.findall(text)[0]
        h = int(h)
        m = int(m)
        text = time_regex_3.sub('', text).strip()
        time_ = (h, m)
        
    if time_:
        # make sure it makes sense
        if time_[0] < 0 or time_[0] > 23:
            raise ParseEventError("Hour part not in range 0..24")
        if time_[1] < 0 or time_[1] > 59:
            raise ParseEventError("Minute part not in range 0..24")
            
    return text, time_


def parse_duration(text):
    duration = None
    duration_regex = re.compile('^(\d{1,2})(\.\d{1,2})*\s*(d |h |m |hour|minute|day)', re.I)
    
    return text, duration


def parse_email_line(es):
    """ find all email addresses in the string 'es'.
    For example, if the input is 'Peter <mail@peterbe.com>'
    then return ['mail@peterbe.com']
    In other words, strip out all junk that isn't valid email addresses.
    """
            
    real_emails = []
    sep = ','
    local_domain_email_regex = re.compile(r'\b\w+@\w+\b')

    for chunk in [x.strip() for x in es.replace(';',',').split(',') if x.strip()]:

        # if the chunk is something like this:
        # 'SnapExpense info@snapexpense.com <add@snapexpense.com>'
        # then we want to favor the part in <...>
        found = re.findall('<([^@]+@[^@]+)>', chunk)
        if found:
            chunk = found[0].strip()

        if valid_email(chunk) or local_domain_email_regex.findall(chunk):
            if chunk.lower() not in [x.lower() for x in real_emails]:
                real_emails.append(chunk)

    return real_emails
