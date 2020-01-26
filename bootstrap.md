# Bootstrapping

This document contains the information you need to bootstrap the project and run your own instance of the Discord bot. It assumes that you know your way around Git, and that you have a fair bit of knowledge of Python.

## Summary

Preconditions before you can start with the bootstrapping process:

* You need accounts on the following platforms:
  * GitHub
  * Discord
  * Google
  * Heroku
* You need a system that you can use for development work with Python 3.7. This can be either a personal laptop or desktop machine, or a remote development machine (e.g. Amazon AWS instance).

And here's the checklist of the actual bootstrapping steps, with each step linking to its own dedicated details sections further down in this document.

* [Prepare dev system to work on](#prepare-dev-system-to-work-on)
* [Create a Google application](#create-a-google-application)
* [Add a stub file to Google Drive](#add-a-stub-file-to-google-drive)
* [Create a Discord application](#create-a-discord-application)
* [Fork and clone the GitHub repository](#fork-and-clone-the-github-repository)
* [Create and configure a Heroku Application](#create-and-configure-a-Heroku-Application)
* [Deploy the code into the Heroku Application container](#deploy-the-code-into-the-heroku-application-container)
* [Start/stop the bot](#startstop-the-bot)
* [Configure the fleet's Discord server](#configure-the-fleets-discord-server)


## References

### Discord resources

* Guide how to set up a Discord bot: <https://dcacademy.gitlab.io/tutorials/starting/making-the-bot.html>


### Heroku resources

* Heroku guide "Getting Started on Heroku with Python" : <https://devcenter.heroku.com/articles/getting-started-with-python>
* Collection of Heroku resources surrounding Python : <https://devcenter.heroku.com/categories/python-support>
* Snap package manager (required to install the Heroku CLI): <https://snapcraft.io/>


### Google Drive resources

* Guide how to set up a Google application that provides access to Google Drive documents : <https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html>
* PyDrive docs : <https://pythonhosted.org/PyDrive/index.html>. PyDrive is a library that provides an abstraction of the Google Drive API that is much simpler to use than the underlying API.


## Prepare dev system to work on

### Introduction

The command line examples in this document are from a vanilla Debian system which points to the `stable` branch (Debian 10 as of writing this).

If you're working with a different flavour of Linux you'll have to find your way around your particular package manager. On macOS the package manager [Homebrew](https://brew.sh/) is strongly recommended. On Windows you are on your own.


### Python 3.7 or newer

Upgrade to a version of your operating system / package manager where Python 3.7 or newer is available. On Debian that is Debian 10 or newer.

Also make sure that Python 3.7 or newer is the default Python version on your system, i.e. executing the command `python` starts the Python 3.7 or newer interpreter. This is necessary so that later on the Heroku command line runs Python commands with the correct Python version. On Debian systems you use the command `update-alternatives` to change the default Python version. Read the man page for details.


### Packages

On Debian install these packages if they are not yet installed:

* `python3-pip`. This installs the Python package installer `pip`. This is required so that the project's Python dependencies can be installed.

* `postgresql-server-dev-11`. This package is required for building certain Python dependencies with `pip`. The indicator that you are missing this package is the following error message when installing the dependencies via `pip`: `Error: b'You need to install postgresql-server-dev-NN for building a server-side extension or libpq-dev for building a client-side application.\n'`

* `snapd`. This is required for installing the Heroku CLI.


### Heroku CLI

Install the Heroku CLI if it is not yet installed:

    snap install heroku --classic


## Create a Google application

### Why Google?

The bot reads and writes data from/to a Google Drive folder. You need to create a Google Application that represents the bot instance you are going to run. The Google Application must be configured to use the Google Drive API, and it must have the privileges to access the Google Drive folder.

In addition to going through the next few sections you can follow the guide listed in the references section - it has pictures and a few more details.


### Project creation

The starting point for creating the application is this URL: <https://console.cloud.google.com/iam-admin/projects>.

* Click `Create Project`
* Project name = PSS Dolores clone (or invent a more unique name)


### Add the Google Drive API

* Select the project once it has been created. You may need to navigate to the Google Cloud Platform dashboard and select the project from the drop-down menu.
* Search for "google drive api" in the search field at the top of the screen
* Select the entry, then click the button `Enable`


### Create service account and credentials

The next step is to create a service account and to get credentials for accessing the service account. There are several ways how to do this, and if you don't know your way around in the Google Cloud Platform console things might be a bit confusing. 

**Alternative 1:** After you add and enable the Google Drive API, the web interface shows the message "*To use this API, you may need credentials. Click 'Create credentials' to get started.*" Clicking the `Create credentials` button starts a Wizard-like UI that guides you until you get to the point where you can create the service account. These are the answers to the wizard questions:

* Which API are you using? = Google Drive API
* Where will you be calling the API from? = Web Server (e.g. node.js, Tomcat)
* What data will you be accessing? = Application Data
* Are you planning to use this API with App Engine or Compute Engine? = No
* At the end of the wizard, click the button `What credentials do I need?` This starts the procedure to create a service account.

**Alternative 2:** After you add and enable the Google Drive API, select `Credentials` from the menu on the left.

* This shows a screen with the message "*To view all credentials or create new credentials visit Credentials in APIs & Services*". Click the `Credentials in APIs & Services` link.
* A new screen opens with a button `Create credentials` in the center.
* Clicking the button opens a drop-down menu. Select the `Service account key` menu entry.
* In the next screen you can select a service account from a drop-down menu. Select the `New service account` menu entry. This starts the procedure to create a service account.

Enter the following details to create the service account:

* Service account name = PSS Dolores clone (or invent a more unique name)
* Role = Project > Editor
* Key type = JSON
* Click the button `Create` to create the service account.

Creating the service account immediately downloads a JSON file to your computer. **Important: Store this JSON file securely and keep the information in the file secret!** Later you will populate a number of environment variables with values from this file.

### Create and configure consent screen

Select `OAuth consent screen` from the menu on the left.

* Select user type = External
* Click the button `Create`. This opens a new screen where you can configure the consent screen.
* You only need to set the application name = PSS Dolores clone (or invent a more unique name)
* Click the button `Save`.


### Create OAuth client ID and credentials

Select `Credentials` from the menu on the left.

* A new screen opens with a button `Create credentials` at the top.
* Clicking the button opens a drop-down menu. Select the `OAuth client ID` menu entry. **Note:** This entry exists only because you previously created and configured the consent screen.
* Application type = Web application
* Name = PSS Dolores clone (or invent a more unique name)
* Authorized JavaScript origins = http://localhost:8080. **Note:** Press Enter after typing the origin, otherwise the data will be silently discarded when you click the `Create` button.
* Authorized redirect URIs = http://localhost:8080/. **Note:** Press Enter after typing the URL, otherwise the data will be silently discarded when you click the `Create` button.
* Click the button `Create`.

After creating the OAuth client ID, it shows up together with the service account in the credentials screen. The OAuth client ID line has a download link that lets you download a JSON file to your computer. **Important: Store this JSON file securely and keep the information in the file secret!** You need this file for the next step.


### Authorize the application

In this step you authorize the application to access your Google account's Google Drive files. In addition to this section you may wish to read through the PyDrive quickstart guide (see link in the "References" section).


**Important, but only if you work on a remote system:** You can't run the authorization on a remote system, you must do it locally, because the settings you used to configure the OAuth client ID refer to `localhost` (e.g. http://localhost:8080/) for the redirect URI.


These are the steps:

* Install PyDrive if you haven't installed it yet: `python -m pip install --user pydrive`
* Create a temporary folder
* Create a file named `quickstart.py` inside the temporary folder. Edit the file so that it has this content:

```
from pydrive.auth import GoogleAuth

gauth = GoogleAuth()
gauth.LocalWebserverAuth() # Creates local webserver and auto handles authentication.
```

* Place a copy of the OAuth client ID JSON file (the one that you downloaded in the previous section) inside the temporary folder. Name the file `client_secrets.json`.
* Run this command: `python quickstart.py`
* This opens a browser window where you can perform the authorization.
* First select the Google account that should authorize the application.
* The next screen is a big fat warning. This is displayed because the Google application you are about to authorize has not been verified by Google. Ignore the warning and proceed by clicking "Advanced", then click the link that is displayed at the bottom of the screen.
* The next screen finally requests that you grant permission to the application for "See, edit, create, and delete all of your Google Drive files".
* Click the button `Allow`, then confirm your decision.


**Note:** You can revoke access at any time in your Google account's security settings.


## Add a stub file to Google Drive

### Create and share folder

* Manually create a folder in your Google account's Google Drive. The folder name does not matter.
* Right-click on the folder name and select "Share" from the context menu.
* Click "Advanced"
* At the top of the dialog you see a "Link to share". Extract from this URL the folder's globally unique folder ID. Example sharing URL `https://drive.google.com/drive/folders/foobar?usp=sharing`. In this example the folder ID is `foobar`. **Important: Keep this information secret!** Later you will populate the environment variable `GDRIVE_FOLDER_ID` with this value.
* Give read/write access to the folder to the Google application. You do this in the area where you can invite people, by entering the client email address of the service account you created earlier. Example email address: `pss-dolores-clone@pss-dolores-clone.iam.gserviceaccount.com`.
* Uncheck "Notify people" - the email address is not valid anyway, so there's no point in sending an invite email.
* Click the button `OK`.

### Create and add stub file

Create a JSON file with this content:

    {
      "fleets" : [ ],
      "users" : [ ],
      "data" : [ ]
    }

This is merely a stub file that contains an empty data set. A file with actual content must be created by another web service. Details are currently unknown.

Add the stub file the Google Drive folder you created in the previous section. **Note:** The bot fails to start up if the folder does not contain this file. The file name must conform to the pattern `pss-top-100_<timestamp>.json`. Example: `pss-top-100_20191130-235900.json`.


The timestamp part must have this format `pss-top-100_yyyymmdd-HHMMSS.json`, where:

* yyyy - year as 4 digits
* mm = month of year as 2 digits, beginning with "01" for January
* dd = day of month as 2 digits
* HH = hours as 2 digits, in 24 hour format
* MM = minutes as 2 digits
* SS = seconds as 2 digits


The actual timestamp is based on the **current date/time** in UTC when the bot runs.

* Midnight of the first of the month of the current date
* Minus 1 minute

**Note:** The code that determines the timestamp part is the function `__fix_filename_datetime` in `gdrive.py`.


## Create a Discord application

You need to create a new Discord application. When your bot instance runs it will act as that application in order to join Discord servers and listen for commands sent by users of that server.

This section contains the important points in the application creation process where you have to fill in some information, or where you have to write down some information for later use. In addition to going through the check list you can follow the guide listed in the references section - it has pictures and a few more details.

The starting point for creating the application is this URL: <https://discordapp.com/developers/applications>.

* Click `New Application`
* App name = PSS Dolores clone (or invent a more unique name)
* App icon = Select an appropriate avatar
* Client ID = secret
  * The client ID is generated for you.
  * **Important: Keep this information secret!**
  * Later you will use this to craft the URL to invite the bot to your fleet Discord server.
* Select the tab `Bot`
* Create the bot & confirm
* Username = PSS Dolores clone (or invent a more unique name)
  * This will be the name under which the bot will be visible to Discord users.
* Set "Public Bot" = Disabled. Public bots can be added by anyone. By making the bot non-public, only you can join this bot to servers.
* Bot Token = secret
  * The bot token is generated for you
  * **Important: Keep this information secret!**
  * Later you will populate the environment variable `DISCORD_BOT_TOKEN` with this value.
* Bot Permissions = 0
  * The default permissions value 0 means the bot will have whatever permissions the `everyone` role has on any Discord server that it joins.
  * Later you will use this value to craft the URL to invite the bot to your fleet Discord server.


## Fork and clone the GitHub repository

Use the GitHub web UI to fork the original GitHub repository listed in the references section.

Next, create a clone of your forked repo on your working machine. Use SSH to clone if you intend to commit and push changes back to GitHub directly from the working machine.

No more details here, you are expected to know how this stuff works. If in doubt consult the GitHub documentation.


## Create and configure a Heroku Application

### Connect Heroku account

Before you can do any Heroku-related operations on your working machine, you need to connect the working machine to your Heroku account. Run this command:

    heroku login

If your working machine is a local system, it pops up a browser where you can log into Heroku's web interface.

If your working machine is a remote machine, the command prints an URL to the console that you can copy & paste into the browser on your local system to perform the login.


### Create the Heroku application

Run these commands:

    cd YaDc
    heroku apps:create --region eu pss-dolores-clone

Notes:

* Select a different region if you don't want to run the bot in the EU region. Omitting the `--region` parameter runs the bot in the US region.
* You should probably use the same name for the Heroku application as for the Discord application.
* If you already have a Heroku application that is set up, then you can reconnect a freshly cloned Git repo to the app with the following command: `heroku git:remote -a pss-dolores-bot`. Obviously you then can skip the rest of the app configuration.


### Provision a database

This command provisions the Heroku application with a PostgreSQL database:

    heroku addons:create heroku-postgresql

The database scheme is created when the bot runs for the first time. This happens in `pss_core.py`, in the function `init_db()`.


### Configure the Heroku application

To configure the Heroku application you need to set a number of so-called *config variables*. 

**Important: The values you set here are very sensitive information! Treat them as you would treat one of your important passwords.**

You can set a config variable either in Heroku's web interface, or via command line like this:

    heroku config:set foo=bar

It is recommended that you set the config variables in Heroku's web interface so that the secret values don't leak. If you do choose the command line, then it is recommended that you set the config variables with the help of a temporary shell script that you delete after use. Do **not** type each `heroku config:set ...` command interactively because the commands you type will get into your shell's history file where they might be visible to someone else on the system.

You need to set the following config variables:

* `DISCORD_BOT_TOKEN`: Set this with the "Bot token" value that you received when you created your Discord application.
* Extract the values for the following variables from the JSON file that you downloaded when you created the Google application's service account:
  * `GDRIVE_SERVICE_CLIENT_EMAIL`
  * `GDRIVE_SERVICE_CLIENT_ID`
  * `GDRIVE_SERVICE_PRIVATE_KEY_ID`
  * `GDRIVE_SERVICE_PRIVATE_KEY`. **Important: The config variable must contain the actual newline characters.** This means that when you get the "private_key" value from the JSON file, you must replace all occurrences of `\n` with real newlines.
  * `GDRIVE_SERVICE_PROJECT_ID`
* `GDRIVE_FOLDER_ID`: Set this with the folder ID you determined when you created and shared the Google Drive folder.
* `GPAT`: Set this with the "General purpose access token" value that you received from the PSS developer community. Note that the bot will start up without this token, so you don't need it in order to take your first steps. Read the last section in this guide for more information about the GPAT.


## Deploy the code into the Heroku Application container

This command deploys the current code:

    git push heroku master

Repeat this command whenever you have committed changes to your Git repository.


## Start/stop the bot

Deploying the current code is fine and dandy, but the bot will not run unless the Heroku application is configured with at least one so-called *worker*.

The following command configures such a worker. If the code has already been deployed, this command starts the bot.

    heroku ps:scale worker=1

The following command removes the worker. If the bot is currently running this command will stop it.

    heroku ps:scale worker=0


## Configure the fleet's Discord server

Create a new channel, then add the bot to the server by visiting this URL:

    https://discordapp.com/oauth2/authorize?client_id=secret&scope=bot&permissions=0

Notes:

* Replace "secret" with the actual client ID of your Discord application
* If you assigned your bot special permissions, then you also have to replace "0" at the end of the URL with the actual permissions value.

After you added the bot it is best practice that you restrict the bot to only the channel it should operate in. If in doubt consult the Discord documentation.


## Run the bot on your working machine

### Preconditions

Install the bot's Python dependencies:

    python3 -m pip install --user -r requirements.txt

In addition you have to make sure that your shell environment is set up with environment variables that match the config variables discussed further up in this document (e.g. `DISCORD_BOT_TOKEN`).

### Run the bot with the help of the Heroku CLI

This should work:

    cd /path/to/bot-folder
    heroku local


### Run the bot completely without Heroku

Inside the server, create a `screen` session to run the job in the background. Note that it is not necessary to use `screen` - the job can be run in the background in other ways, for example using the `nohup` command.

    cd /path/to/bot-folder
    screen -S pss    # Create a screen session named "pss"
    while true; do python src/bot.py; sleep 5; done

Press Ctrl-A, Ctrl-D to exit the screen session. To get back to the screen session (e.g. for stopping the bot), restore the session with:

    screen -r pss

To stop the bot, press Ctrl-C twice.


## Obtaining the GPAT

A final word on the GPAT...

For certain calls to the PSS web API the bot needs the so-called "general purpose access token", or GPAT for short. This token is not available to the general public because SavySoda do not support general access to their PSS web API. They do tolerate access to their API by an informal community of developers that are PSS enthusiasts, and for that purpose they have handed out the GPAT to the PSS developer community at some point in the past, under the implied condition of responsible use.

The PSS developer community in turn has adopted the following policy how to deal with the GPAT:

> The community wants to limit who has the GPAT and to make sure that it is used responsibly. This is because of several concerns, starting with: If SavySoda thinks that the GPAT usage has become a problem then they could just turn it off.  That would not necessarily affect their own code, but it would stop a ton of the community stuff, like [Pixyship](http://pixyship.com/), the Dolores/Dolores 2.0 bots, etc.
> 
> So first the community wants to make sure that the request for the GPAT is not spurious, i.e., the person already knows how to program and can write a program using the API. The community does not want to give the key to someone who has only an idle interest. And secondly, the community wants to prevent secondary distribution of the GPAT, to keep it from getting into the hands of unknown people with unknown interests.

That being said, you can obtain the GPAT from the PSS developer community by joining them and answering some questions. They might impose additional conditions such as asking that you write some code working with the API first. There is a number of API calls that don't require the GPAT, so that shouldn't be too hard.

**Note:** The bot will start up without the GPAT, so you don't need it in order to take your first steps.

