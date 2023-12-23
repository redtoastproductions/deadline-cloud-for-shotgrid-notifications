import shotgun_api3


def get_shotgun(url, login=None, password=None):
    """
    Get a connection to ShotGrid using the specified credentials.
    
    Returns a Shotgun Client connection.
    
    Args:
        url: Full URL to the ShotGrid instance
        login: Username of a ShotGrid account
        password: Password for the account
    """
    
    sg = None
    try:
        sg = shotgun_api3.Shotgun(url, login=login, password=password)
    except:
        raise
    
    return sg


def create_budget_alert_note(sg=None, project_id=None, users=None, farm_id=None, farm_name=None, farm_hostname=None, queue_name=None, budget_id=None, budget_limit=None):
    """
    Create a budget notification addressed to a list of users on a project.
    
    Returns the created Note entity.
    
    Args:
        sg: Shotgun client
        project_id: sg_id of the Project
        users: A list of HumanUsers to receive the note
        farm_id: Deadline Cloud farm ID
        farm_name: Deadline Cloud farm name
        farm_hostname: Deadline Cloud Monitor web hostname, e.g. "<farmname>.<region>.deadlinecloud.amazonaws.com"
        queue_name: Deadline Cloud queue name
        budget_id: Deadline Cloud budget ID
        budget_limit: Deadline Cloud budget approximateDollarLimit
    """
    
    note_text = "Deadline Budget Alert:\n"
    note_text += f"The queue {queue_name} on farm {farm_name} has stopped because it reached its budget limit of {budget_limit}.\n"
    note_text += "\n"
    note_text += f"Please update the budget limit to enable renders on this queue: https://{farm_hostname}/farms/{farm_id}/budget/{budget_id}/edit"
    
    note_subject = f"Deadline Cloud Budget Alert: {queue_name} stopped"
    
    note = None
    try:
        note = sg.create(
                   "Note",
                   {
                       "addressings_to": users,
                       "sg_status_list": "opn",
                       "content": note_text,
                       "subject": note_subject,
                       "project": {"type": "Project", "id": project_id}
                       
                   })
    except:
        raise
    
    return note

