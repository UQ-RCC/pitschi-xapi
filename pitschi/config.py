import configparser
import os
import errno

config = configparser.SafeConfigParser()
config.read(["conf/pitschixapi.conf", os.environ.get("PITSCHI_XAPI_CONFIG", ""), "/etc/pitschi/conf/pitschixapi.conf"])

def get(section, option, default = None, required=False):
    """
    Reads config optoin from the given section, returning default if not found
    """
    try:
        return config.get(section, option).strip()
    except:
        if required: 
            raise Exception(f"option {option} is required in section {section}")
        else:
            return default