import json
import logging
import logutil
import os
import traceback

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


DATA_PATH = "~/.deadline/notifications/notification_data.json"


def get_stored_data():
    """Returns a dictionary containing the notifier's stored data.
    Data is stored as JSON.
    
    """
    
    data = {}
    
    data_path = os.path.normpath(os.path.expanduser(DATA_PATH))
    
    with open(data_path, "r") as f:
        try:
            data = json.loads(f.read())
        except Exception as e:
            logger.exception(e)
    
    if not data:
        data = {}
    
    # logger.debug(data)
    
    return data


def update_stored_data(data):
    """Updates the notifier's stored data with the given dictionary contents.
    
    Args:
        data: A dictionary of data to insert or update into the notifier stored data.
    """
    
    # logger.debug(f"data: {data}")
    data_path = os.path.normpath(os.path.expanduser(DATA_PATH))
    
    data_stored = {}
    try:
        data_stored = get_stored_data()
    except:
        logger.error("Couldn't read stored data")
        logger.error(traceback.format_exc())
    
    data_stored.update(data)
    
    try:
        if not os.path.exists(os.path.dirname(data_path)):
            os.makedirs(os.path.dirname(data_path))
    except Exception as e:
        logger.exception(e)
    
    with open(data_path, "w") as f:
        try:
            result = f.write(json.dumps(data_stored, indent=4))
        except Exception as e:
            logger.exception(e)
    
    return result

