import configparser
import os
import errno

config = configparser.ConfigParser()
config.read(["conf/pitschixapi.conf", os.environ.get("PITSCHI_XAPI_CONFIG", ""), "/etc/pitschi/conf/pitschixapi.conf"])

def get(section, option, default = None, os_env=True, required=False):
    """
    Reads config optoin from the given section, returning default if not found
    """
    cp_vars = os.environ if os_env else None
    try:
        return config.get(section, option, vars=cp_vars).strip()
    except:
        if required: 
            raise Exception(f"option {option} is required in section {section}")
        else:
            return default
