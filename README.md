# Yet another Dolores clone

This is a Discord Bot for Pixel Starships, targeted for hosting on Heroku.

## 1. Setup for Hosting on Heroku

1. Create a Heroku account and go to the [dashboard](https://dashboard.heroku.com)
2. Fork this repository to your own Github account
3. Under the deploy option, connect to your Github account, and select this repository.
   Select the button for automatic deploys.
4. Under settings, choose "Reveal Config Vars".
   Enter `DISCORD_BOT_TOKEN` as the variable name.
   Enter the value from the bot token retrieved from the
   [Discord developer page](https://discordapp.com/developers/applications)
5. Under overview, choose "Configure Dynos"
   Enable the option where it says `worker: python src/bot.py`.

## 2. Self-Hosted Setup

1. Log in to the server (this is optional if you are running from
   a local computer).  For example, if you
   [launched](https://aws.amazon.com/getting-started/tutorials/launch-a-virtual-machine)'
   an Amazon Web Services Virtual Machine, this would be:

```bash
ssh -i $HOME/.ssh/my_key_file.pem ec2-user@hostname
```

where your Amazon AWS instance key file is `my_key_file.pem`
and the username and address above should be changed to that
of your instance running on AWS.

2. Install Python 3.6 and Git.
   On an Amazon AMI, this would be:

```bash
sudo yum install python36 python36-pip git
```

3. Clone this Github repository
   Use pip to install Python dependencies:
   `asyncio`, `holidays`, `numpy`, `pandas`,
   `python-dateutil`, `pytz`,
   `git+https://github.com/Rapptz/discord.py@rewrite#egg=discord.py`

```bash
git clone https://github.com/jzx3/heroku-pss.git
cd heroku-pss/
python3 -m pip install --user -r requirements.txt
```

4. Create a Discord Bot.  A good guide is Sebi's bot tutorial.
   The link to the tutorial is [here](https://discord.gg/GWdhBSp).

   Get the invite link for the Discord bot and add the bot to the
   Discord chat.

   Get the Discord bot token from https://discordapp.com/developers/applications
   Add the bot token to `~/.bash_profile` as follows:

```bash
export DISCORD_BOT_TOKEN="insert_bot_token_here"
```

## 2. Running the Bot

Inside the server, create a `screen` session to run the job
in the background. Note that it is not necessary to use
`screen`--the job can be run in the background in other ways,
for example using the `nohup` command.

```bash
cd $HOME/heroku-pss/
screen -S pss    # Create a screen session named "pss"
while true; do python36 src/bot.py; sleep 5; done
```

Press Ctrl-A, Ctrl-D to exit the screen session.
To get back to the screen session (e.g. for stopping the bot),
restore the session with:

```
screen -r pss
```

To stop the bot, press Ctrl-C twice.

## 3. Bot Usage on Discord

Inside Discord chat, get the list of commands using:

```
/help
```
