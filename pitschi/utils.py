import pitschi.config as config
import datetime, pytz
import os
from chardet import detect
from random import randrange

def localize_time(datetimeobject):
    if datetimeobject.tzinfo:
        return datetimeobject
    else:
        return pytz.timezone(config.get('ppms', 'timezone')).localize(datetimeobject, is_dst=None)

#converts navive datetime object to UTC and then convert it to ppms timezone
def convert_to_xapi_tz(datetimeobject):
    return pytz.timezone('utc').localize(datetimeobject, is_dst=None).astimezone(pytz.timezone(config.get('ppms', 'timezone')))

def convert_utc_to_ppms(datetimeobject):
    return datetimeobject.astimezone(pytz.timezone(config.get('ppms', 'timezone')))

def convert_to_utc(datetimeobject):
    if datetimeobject.tzinfo:
        return datetimeobject.astimezone(pytz.utc)
    else:
        return pytz.timezone(config.get('ppms', 'timezone')).localize(datetimeobject, is_dst=None).astimezone(pytz.utc)


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
        


def ok_for_ingest():
    """
    This function gets a random folder from config[prefix]
    Then checks whether the folder is accessible
    This is due to the fact that NFS mounts might not be accessible
    Ingestion service needs to check this before hand
    """
    try:
        _collections = os.listdir(config.get('rdm', 'prefix'))
        if not _collections:
            return False
        else:
            _random_collection = _collections[randrange(len(_collections))]
            os.listdir(os.path.join(config.get('rdm', 'prefix'), _random_collection))
            return True
    except:
        return False
