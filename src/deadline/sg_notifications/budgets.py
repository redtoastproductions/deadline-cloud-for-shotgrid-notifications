import datetime
import locale
import logging
import logutil
import sys
import traceback

import alerts
import credentials
import storage

from deadline.client import api

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


class DeadlineCloudHelper(object):
    """
    Deadline Cloud utility functions to get normalized output from the API
    and handle notifications for a given studio hostname.
    
    """
    
    def __init__(self, studio_hostname=None):
        """
        Create a DeadlineCloudHelper for the given studio hostname.
        
        Args:
            studio_hostname: Deadline Cloud studio web host name
        """
        
        self.studio_hostname = studio_hostname
        self.initialize()
    
    
    def initialize(self):
        """
        Checks configuration and alerts the user to misconfiguration.
        
        """
        
        if not self.studio_hostname:
            logger.error("No studio_hostname was provided.")
    
    
    def get_farms(self):
        """
        Returns a list of Deadline Cloud farms for this studio.
        
        """
        
        farms = None
        
        try:
            result = api.list_farms()
            
            if "farms" not in result:
                raise RuntimeError(f"No farms in result: {result.keys()}")
            
            farms = result["farms"]
            
        except:
            raise
        
        return farms
    
    
    def get_queues(self, farm_id):
        """
        Returns a list of Deadline Cloud queues for the given farm.
        
        Args:
            farm_id: Deadline Cloud farm ID
        """
        
        queues = None
        
        try:
            result = api.list_queues(farmId=farm_id)
            
            if "queues" not in result:
                raise RuntimeError(f"No queues in result: {result.keys()}")
            
            queues = result["queues"]
        
        except Exception as e:
            raise e
        
        return queues
    
    
    def get_budgets_for_farm(self, farm_id):
        """
        Returns a list of Deadline Cloud budgets for the given farm.
        
        Args:
            farm_id: Deadline Cloud farm ID
        """
        
        budgets = None
        
        try:
            result = _list_budgets(farmId=farm_id)
            logger.debug(f"_list_budgets: {result}")
            
            if "budgets" not in result:
                raise RuntimeError(f"No budgets in result: {result.keys()}")
            
            budgets = result["budgets"]
            
        except:
            raise
        
        return budgets
    
    
    def get_farm_from_queue_id(self, queue_id):
        """
        Returns the Deadline Cloud farm that contains a queue with the given queue_id.
        
        Args:
            queue_id: Deadline Cloud queue ID
        """
        
        farm_result = None
        
        farm_id = None
        try:
            farms = self.get_farms()
        except Exception as e:
            if e.__class__.__name__ == "AccessDeniedException":
                logger.error(f"Access denied for ListQueues on farm: {farm['farmId']}")
                logger.error(sys.exc_info())
            else:
                raise
        
        logger.debug(f"farms: {farms}")
        for farm in farms:
            try:
                for queue in self.get_queues(farm["farmId"]):
                    if queue["queueId"] == queue_id:
                        farm_result = farm
                        break
            except Exception as e:
                if e.__class__.__name__ == "AccessDeniedException":
                    logger.error(f"Access denied for ListQueues on farm: {farm['farmId']}")
                    logger.error(sys.exc_info())
                else:
                    raise
        
        return farm_result
    
    
    def notify_queue_over_limit(self, budgets_to_notify):
        """
        Send budget alert notifications to users monitoring the budgeted queues.
        
        Returns a list of Deadline Cloud budgets which had alert notifications sent.
        
        Args:
            budgets_to_notify: Deadline Cloud budgets for which notifications will be sent.
        """
        
        notified_over_limit = []
        
        for budget in budgets_to_notify:
            budget_id = budget["budgetId"]
            budget_limit = budget["approximateDollarLimit"]
            
            queue_id = budget["usageTrackingResource"]["queueId"]
            try:
                farm = self.get_farm_from_queue_id(queue_id)
                farm_name = farm["displayName"]
                logger.debug(f"Farm: {farm_name}  Budget: {budget_id}")
            except:
                logger.error(sys.exc_info())
                continue
            
            queue_name = [queue["displayName"] for queue in self.get_queues(farm["farmId"]) if queue["queueId"] == queue_id][0]
            
            # Check if an alert for this budget limit has already been sent
            try:
                if get_alert_sent(budget_id, budget_limit):
                    logger.debug(f"Skipping notification for budget: {budget_id}  limit: {budget_limit}")
                    continue
            except:
                logger.error(traceback.format_exc())
                # continue
            
            # Apply currency symbol to budget limit using the current OS locale
            locale.setlocale(locale.LC_ALL, "")
            budget_limit_formatted = locale.currency(budget["approximateDollarLimit"], grouping=True)
            
            # Send an alert to the users monitoring this queue
            try:
                note = alerts.send_budget_alert_note(
                    farm_id=farm["farmId"],
                    farm_name=farm_name,
                    farm_hostname=self.studio_hostname,
                    queue_name=queue_name,
                    budget_id=budget_id,
                    budget_limit=budget_limit_formatted
                )
                logger.debug(f"Sent note: {note}")
                
                alert_sent = set_alert_sent(budget_id, budget_limit)
                logger.debug(f"alert_sent: {alert_sent}")
                
                notified_over_limit.append(budget)
            except:
                logger.error(sys.exc_info())
                continue
        
        return notified_over_limit
    
    
def get_budgets_to_notify(budgets):
    """
    Find budgets which are marked ACTIVE and have usage that has met or exceeded the limit.
    
    Returns a list of Deadline Cloud budgets matching those criteria.
    
    Args:
        budgets: a list of Deadline Cloud budgets
    """
    
    budgets_to_notify = []
    
    for budget in budgets:
        # logger.debug(f"budget: {budget}")
        budget_id = budget['budgetId']
        # logger.debug(f"budgetId: {budget_id}")
        
        queue_id = budget["usageTrackingResource"]["queueId"]
        # logger.debug(f"queue_id: {queue_id}")
        
        # Budgets are ACTIVE or INACTIVE
        status = budget["status"]
        if status != "ACTIVE":
            logger.debug(f"Skipping budget with status: {status}")
            continue
        
        usage_over_limit = budget["usages"]["approximateDollarUsage"] >= budget["approximateDollarLimit"]
        if usage_over_limit:
            budgets_to_notify.append(budget)
    
    return budgets_to_notify


def check_budgets_and_notify(studio_hostname):
    """
    Check all budgets in this Deadline Cloud studio and send notifications
    for any that are over their usage limit.
    
    Returns a dict with a list of Deadline Cloud budgets which need notifications sent.
    
    Args:
        studio_hostname: Deadline Cloud studio web host name
    """
    
    result = {}
    
    logger.debug(f"studio_hostname: {studio_hostname}")
    
    # Get a DeadlineCloudHelper for this studio
    try:
        dch = DeadlineCloudHelper(studio_hostname=studio_hostname)
    except:
        raise
    
    # Check every farm in the studio
    for farm in dch.get_farms():
        logger.debug(f"farm: {farm['farmId']}")
        try:
            budgets = dch.get_budgets_for_farm(farm_id=farm["farmId"])
        except:
            raise
        # logger.debug(f"Received {len(budgets)}: {budgets}")
        
        # Check if any budgets are over limit
        budgets_to_notify = get_budgets_to_notify(budgets)
        logger.debug(f"budgets_to_notify: {budgets_to_notify}")
        
        # Check if any ShotGrid groups need creation
        groups_created = alerts.create_notification_groups(dch.get_queues(farm["farmId"]))
        if groups_created:
            logger.info(f"groups_created: {groups_created}")
        
        # If any notifications are needed
        if budgets_to_notify:
            try:
                # Send budget notifications to the groups corresponding to queues who are over budget
                result["notified_over_limit"] = dch.notify_queue_over_limit(budgets_to_notify)
            except:
                raise
        
    return result


def get_studio_hostnames():
    """
    Get a list of studio hostnames from the credentials store.
    
    Returns a list of Deadline Cloud studio web host names.
    
    """
    
    studio_hostnames = None
    
    try:
        studio_hostnames = credentials.get_credential("deadline_cloud", "studio_hostnames")
        logger.debug(f"studio_hostnames: {studio_hostnames}")
    except:
        raise
    
    return studio_hostnames


def get_alert_sent(budget_id, budget_limit):
    """
    Get if a budget alert notification was sent the given budgeted queue.
    
    Returns None if no data is available, or boolean if a matching budget alert was already sent.
    
    Args:
        budget_id: Deadline Cloud budget ID
        budget_limit: (float) Deadline Cloud budget approximateDollarLimit
    """
    
    alert_sent = None
    
    alert_data = {}
    try:
        alert_data = storage.get_stored_data()
    except Exception as e:
        logger.error("Couldn't read stored data")
        logger.error(traceback.format_exc())
    
    if not alert_data:
        return None
    
    if budget_id in alert_data:
        if alert_data[budget_id]["approximateDollarLimit"] == budget_limit:
            # An alert was previously sent for this budget's budget_limit
            alert_sent = True
    
    return alert_sent


def set_alert_sent(budget_id, budget_limit):
    """
    Stores a budget_limit for a budget_id.
    
    Args:
        budget_id: Deadline Cloud budget ID
        budget_limit: (float) Deadline Cloud budget approximateDollarLimit
    """
    
    alert_stored = None
    
    alert_data = {}
    try:
        alert_data = storage.get_stored_data()
    except Exception as e:
        logger.error("Couldn't read stored data")
        logger.error(traceback.format_exc())
    
    alert_to_store = {budget_id: {"approximateDollarLimit": budget_limit}}
    # logger.debug(alert_to_store)
    
    try:
        data_written = storage.update_stored_data(alert_to_store)
    except:
        logger.error("Couldn't write stored data")
        logger.error(traceback.format_exc())
    
    return alert_to_store


def _list_budgets(*args, **kwargs):
    """
    Calls the deadline:ListBudgets API call. If the response is paginated,
    it repeatedly calls the API to get all the budgets.
    
    kwargs:
        farmId: Deadline Cloud farm ID
    """
    
    deadline_client = api._session.get_boto3_client("deadline")
    return api._list_apis._call_paginated_deadline_list_api(deadline_client.list_budgets, "budgets", **kwargs)


def run():
    results = []
    
    studio_hostnames = get_studio_hostnames()
    for studio_hostname in studio_hostnames:
        result = check_budgets_and_notify(studio_hostname)
        results.append(result)
        logger.debug(f"result: {result}")
    
    return results

