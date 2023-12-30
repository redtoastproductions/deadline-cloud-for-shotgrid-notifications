import json
import logging
import logutil
import os

# Logging to file
logutil.add_file_handler()
logger = logging.getLogger(__name__)
logger.setLevel(logutil.get_deadline_config_level())

# Logging to stdout
log_handler = logging.StreamHandler()
log_fmt = logging.Formatter(
    "%(asctime)s - [%(levelname)-7s] "
    "[%(module)s:%(funcName)s:%(lineno)d] %(message)s"
)
log_handler.setFormatter(log_fmt)
logger.addHandler(log_handler)


CREDENTIALS_PATH = "~/.deadline/notifications/config_notifications.json"


def get_credential(section, key):
    """
    Get an entry from the credentials file.
    
    Returns the matching entry or None if one is not found.
    
    Args:
        section: key name from the top level of the configuration file's data
        key: name of an entry inside the given section
    """
    
    result = None
    
    credentials_path = os.path.normpath(os.path.expanduser(CREDENTIALS_PATH))
    data = {}
    with open(credentials_path, "r") as f:
        try:
            data = json.loads(f.read())
        except:
            raise
    
    if section in data:
        if key in data[section]:
            result = data[section][key]
        else:
            logger.debug(f"Key '{key}' not found in section '{section}' in credentials: {credentials_path}")
    else:
        logger.error(f"Section '{section}' not found in credentials: {credentials_path}")
    
    return result


