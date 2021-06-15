import pitschi.config as config
import datetime, pytz
import os
from chardet import detect

def localize_time(datetimeobject):
    if datetimeobject.tzinfo:
        return datetimeobject
    else:
        return pytz.timezone(config.get('ppms', 'timezone')).localize(datetimeobject, is_dst=None)

def convert_to_xapi_tz(datetimeobject):
    return pytz.timezone('utc').localize(datetimeobject, is_dst=None).astimezone(pytz.timezone(config.get('ppms', 'timezone')))


def get_encoding_type(file):
    with open(file, 'rb') as f:
        rawdata = f.read()
    return detect(rawdata)['encoding']

def read_metadata(path):
    """
    Read metadata file and returns JSON
    """
    extension = os.path.splitext(path)[-1]
    if extension == '.txt':
        contents = {}
        with open(path, encoding=get_encoding_type(path), errors='ignore') as fp:
            for count, line in enumerate(fp):
                line = line.strip()
                if '=' in line:
                    _vals = line.split('=', 1)
                else:
                    _vals = line.split(' ', 1)
                if len(_vals) > 1:
                    (field, val) = _vals
                else:
                    field = _vals[0]
                    val = None
                #field=a.replace('$', '')
                while field.startswith('$'):
                    field = field[1:]
                contents[field] = val
        return contents
    else:
        return {}
        