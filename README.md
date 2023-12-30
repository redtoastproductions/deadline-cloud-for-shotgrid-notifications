# Deadline Cloud ShotGrid Notifications

## Deadline Cloud ShotGrid Budget Alerts

### Installation
Ensure you have Deadline Cloud Monitor set up with a default Monitor profile configured.

A server environment with continuous availability requires an access key on the profile's account.

Starting from the root directory of this repository:

**1. Create a virtual environment for the notifier**

  `python -m venv notifier_env`

**2. Activate the environment**

  `notifier_env/Scripts/activate`

**3. Install libraries into the environment**

  * Log in to codeartifact:
  * `aws --region us-west-2 codeartifact login --tool pip --domain amazon-deadline-cloud --domain-owner 938076848303 --repository amazon-deadline-cloud-client-software`
  * Install the Deadline Cloud client library:
  * `pip install deadline`
  
  * Install the shotgun_api3 library:
  `pip install git+https://github.com/shotgunsoftware/python-api.git`


### ShotGrid and notifier setup
**1. Create a Script in ShotGrid**
  
  * In your ShotGrid instance, go to the Scripts page for the instance from the Admin menu in the top right corner.
  * Click "Add Script".
  * Give the script a name, such as "DeadlineCloudNotifications".
  * Click the "More fields" dropdown.
  * Make sure Generate Events is checked in the "More fields" dropdown.
  * Enable the Generate Events checkbox on the "Create a new Script" form.
  * Copy the script name and application key to a text editor. They will be used to configure the notifier.
  * Click "Create Script". It may be "Create Script and Keep Form Values" if you changed the default.
  * Close the "Create a new Script" form if necessary after creating the script.
  
**2. Configure the notifier**

  A sample configuration template in JSON format is supplied: `examples/config_notifications.json`
  * Copy this template to the configuration file's location: `~/.deadline/notifications/config_notifications.json`
  * Edit the configuration file's `studio_hostnames` section to include all studio hostnames you would like to monitor.
  * Edit the template's `shotgrid` section to fill in your ShotGrid URL, script name, and application key.
  
**3. Start the notifier**
  
  You can start the notifier with a job scheduler or run it from the shell with:
  
  `python src/deadline/sg_notifications/notifier.py`
  
  If starting with a scheduler, be sure to activate the Python environment first.
  
**4. Populate ShotGrid groups**
  
  The notifier creates one Group in ShotGrid for each queue in each farm in your studio.
  
  The groups are named as: _DeadlineCloud queue:Queue Name queue-id:queue-example1234567890_
  
  The groups must to be associated with a ShotGrid project and have users added to receive notifications.
  
  * In your ShotGrid instance, go to the Groups page for the instance from the Admin menu in the top right corner.
  * Add the "Group Project" column to the page if it's not already visible.
  * For each DeadlineCloud group, click the Group Project field to assign a ShotGrid Project to the group. Notifications for a queue are visible to project members as Notes on the linked project.
  * For each DeadlineCloud group, add users to be notified by clicking in the Users field to assign users to the group.

**5. Enable ShotGrid email notifications (_optional_)**
  
  Deadline Cloud notifications will appear in your ShotGrid Inbox as Notes.
  If you would like to receive email notifications as well:
  * In your ShotGrid instance, go to your Account Settings page from the Profile menu in the top right corner.
  * Click "Email Notifications" in the left navigation pane.
  * Enable "Email me about Notes that I'm involved in"


### Usage
Without any command line options, the notifier will run continuously and check for updates every 15 seconds.

You can specify a refresh delay in seconds with the `-d` (`--delay`) option.

Specify a refresh delay of 0 to have the notifier perform one update and exit without running continuously. This is useful if launching from a script or job scheduler.


### Development notes
The notifier uses the Deadline Cloud log level. You can change it with:
`deadline config set settings.log_level LOG_LEVEL`


## License

Redtoast
