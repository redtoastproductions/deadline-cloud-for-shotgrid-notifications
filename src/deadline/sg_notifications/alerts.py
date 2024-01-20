import logging
import logutil

import shotgun_api3

import credentials

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


DC_NOTIFICATIONS_PREFIX = "DeadlineCloud"
DC_BUDGET_ACTION_NONE = "NONE"
DC_BUDGET_ACTION_STOP_SCHEDULING_AND_CANCEL_TASKS = "STOP_SCHEDULING_AND_CANCEL_TASKS"
DC_BUDGET_ACTION_STOP_SCHEDULING_AND_COMPLETE_TASKS = "STOP_SCHEDULING_AND_COMPLETE_TASKS"


def get_shotgun(url=None, login=None, password=None, script_name=None, api_key=None):
    """
    Get a connection to ShotGrid using the specified credentials.
    
    Returns a Shotgun Client connection.
    
    Args:
        url: Full URL to the ShotGrid instance
        login: Username of a ShotGrid account
        password: Password for the account
    """
    
    sg = None
    
    url = url or credentials.get_credential("shotgrid", "url")
    
    script_name = script_name or credentials.get_credential("shotgrid", "script_name")
    
    if script_name:
        api_key = api_key or credentials.get_credential("shotgrid", "api_key")
        
    # Prefer ScriptUser authentication
    if script_name and api_key:
        try:
            sg = shotgun_api3.Shotgun(url, script_name=script_name, api_key=api_key)
            return sg
        except:
            raise
    
    login = login or credentials.get_credential("shotgrid", "login")
    
    password = password or credentials.get_credential("shotgrid", "password")
    
    if login and password:
        try:
            sg = shotgun_api3.Shotgun(url, login=login, password=password)
            return sg
        except:
            raise
    else:
        logger.error("Insufficient credentials provided for authentication.")
    
    return None


def send_budget_alert_note(farm_id=None, farm_name=None, farm_hostname=None, queue_name=None, budget_id=None, budget_limit=None, default_budget_action=None):
    """
    Create a budget notification addressed to a list of users on a ShotGrid project.
    
    Returns the created Note entity.
    
    Args:
        farm_id: Deadline Cloud farm ID
        farm_name: Deadline Cloud farm name
        farm_hostname: Deadline Cloud Monitor web hostname for the studio, e.g. "<farmname>.<region>.deadlinecloud.amazonaws.com"
        queue_name: Deadline Cloud queue name
        budget_id: Deadline Cloud budget ID
        budget_limit: Deadline Cloud budget approximateDollarLimit
        default_budget_action: Deadline Cloud budget defaultBudgetAction
    """
    
    note_text = ""
    note_subject = f"Deadline Cloud Budget Alert: {queue_name} reached its limit"
    if default_budget_action in [
        DC_BUDGET_ACTION_STOP_SCHEDULING_AND_CANCEL_TASKS,
        DC_BUDGET_ACTION_STOP_SCHEDULING_AND_COMPLETE_TASKS
    ]:
        note_subject = f"Deadline Cloud Budget Alert: {queue_name} reached its limit and stopped"
        note_text = "Deadline Budget Alert:\n"
        note_text += f"The queue {queue_name} on farm {farm_name} has stopped because it reached its budget limit of {budget_limit}.\n"
        note_text += "\n"
        note_text += f"Please update the budget limit to enable renders on this queue: https://{farm_hostname}/farms/{farm_id}/budget/{budget_id}/edit"
        
    elif default_budget_action == DC_BUDGET_ACTION_NONE:
        note_text = "Deadline Budget Alert:\n"
        note_text += f"The queue {queue_name} on farm {farm_name} has reached its budget limit of {budget_limit}. The queue will continue processing jobs.\n"
        note_text += "\n"
        note_text += f"To update the budget limit on this queue: https://{farm_hostname}/farms/{farm_id}/budget/{budget_id}/edit"
        
    else:
        logger.warning(f"Unknown default_budget_action: {default_budget_action}")
        note_text = "Deadline Budget Alert:\n"
        note_text += f"The queue {queue_name} on farm {farm_name} has reached its budget limit of {budget_limit}.\n"
        note_text += "\n"
        note_text += f"To update the budget limit on this queue: https://{farm_hostname}/farms/{farm_id}/budget/{budget_id}/edit"
    
    try:
        group = get_queue_group(queue_name)
        logger.debug(f"group: {group}")
    except:
        raise
    
    note = None
    try:
        sg = get_shotgun()
        note = sg.create(
                   "Note",
                   {
                       "addressings_to": [group],
                       "sg_status_list": "opn",
                       "content": note_text,
                       "subject": note_subject,
                       "project": {"type": "Project", "id": group["sg_group_project"]["id"]}
                       
                   })
    except:
        raise
    
    return note


def get_queue_group(queue_name):
    """
    Find a notification Group corresponding to a Deadline Cloud queue.
    
    Returns the matching Group entity or None if one is not found.
    
    Args:
        queue_name: Deadline Cloud queue name
    """
    group = None
    
    logger.debug(f"queue_name: {queue_name}")
    
    groups = get_notification_groups()
    try:
        group = [g for g in groups if queue_name in g["code"]][0]
    except ValueError:
        logger.error(f"No group found for queue_name: {queue_name}")
    except:
        raise
    
    return group


def create_notification_groups(queues):
    """
    Create ShotGrid Groups for each specified queue.
    
    Returns a list of the Group entities created.
    
    Args:
        queues: a list of Deadline Cloud queues
    """
    
    groups_created = []
    
    groups = get_notification_groups()
    
    queues_known = []
    try:
        for group in groups:
            if f"{DC_NOTIFICATIONS_PREFIX}" in group["code"] and "queue-id:" in group["code"]:
                queues_known.append(group["code"].split("queue-id:")[-1].split(" ")[0])
        logger.debug(f"queues_known: {queues_known}")
    except:
        group_names = [group["code"] for group in groups]
        logger.error(f"One or more bad group names: {group_names}")
    
    queues_needing_groups = [queue for queue in queues if queue["queueId"] not in queues_known]
    for queue in queues_needing_groups:
        group_created = create_notification_group(queue)
        groups_created.append(group_created)
        logger.debug(f"Created group: {group_created['code']}")
    
    return groups_created


def create_notification_group(queue):
    """
    Create a notification Group corresponding to a Deadline Cloud queue.
    
    The group has the naming convention:
    "DeadlineCloud queue:Queue Name queue-id:queue-example1234567890"
    
    Returns the created Group entity or None if one was not created.
    
    Args:
        queue: Deadline Cloud queue
    """
    
    group_created = None
    
    try:
        sg = get_shotgun()
        
        group_name = "{} queue:{} queue-id:{}".format(DC_NOTIFICATIONS_PREFIX, queue["displayName"], queue["queueId"])
        
        existing_group = sg.find_one("Group", filters=[["code", "contains", group_name]], fields=["code"])
        if existing_group:
            logger.error(f"Group already exists: {group_name}")
            return None
    except:
        raise
    
    try:
        group_created = sg.create("Group", {"code": group_name})
        logger.info(f"Group created: {group_created['code']}")
    except:
        raise
    
    return group_created   


def get_notification_groups():
    """
    Find all notification Groups corresponding to Deadline Cloud queues.
    
    Returns a list of matching Group entities or raises an exception if one occurs.
    
    Args:
        queue_name: Deadline Cloud queue name
    """
    
    result = None
    
    try:
        sg = get_shotgun()
        result = sg.find("Group", filters=[["code", "contains", DC_NOTIFICATIONS_PREFIX]], fields=["code", "sg_group_project"])
    except:
        raise
    
    return result
