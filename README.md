# SwagBot v2.0 - Now with more swagger!
SwagBot is a powerful, useful, and sometimes mischievious bot for Slack. It utilizes the Slack Events API and is easily extensible.

## Installation
In short
* Clone the repo
* `$ mkdir ~/.swagbot`
* Create `~/.swagbot/bot.yml`
* `$ pip install -r requirements.txt`
* `$ ./database-setup/database-setup.py`
* `$ ./bot-launcher.py`

## Features
SwagBot possesses a number of useful features.
* SwagBot utilizes a SQLite backend for a number of things such as:
  * User and channel data
  * Command definitions (command enabled, etc)
  * Module definitions for enabling and disabling modules
* SwagBot uses a plugin-based architecture for its commands. i.e., Commands are stored in Python modules which are subclasses of the class `Swagbot.core.BasePlugin`. Because of the modularity, commands or entire plugins can be enabled/disabled on the fly.
* SwagBot is resilient. If there is an unexpected error and the websocket disconnects, the bot will attempt to reconnect. This also applies for a code error which causes the bot or one of its modules to crash.
* New code can be added without taking the bot down. You can simply instruct the bot to reload its plugins.

## Classes
### swagbot.bot.SwagBot
This is the main bot class. It initializes the bot, loads the plugins, and launches required threads. It also processes inbound events.
### swagbot.core.BasePlugin
This is a basic plugin class. All plugins should be a subclass of this class
### swagbot.core.Command
If a user says something to the bot that is actually a bot command, its Event object is used to construct a Command object. The command object determines if the command is able to be executed based on factors like command level, user level, and command state. The command output is also stored in the command object. It allows the bot to process each command in an encapsulated object.
### swagbot.core.Event
Each eligible Slack event received is put into an instance of `swagbot.core.Event` and attached to each command instance.
### swagbot.core.Output
This class stores output/error information about each command executed. It is attached to each command instance.
### swagbot.scheduler.Scheduler
This class allows any bot plugin to schedule tasks, e.g., update PagerDuty schedule information, on a schedule. Its features include:
* Job functions are encapsulated using `dill`, based64-encoded, and stored in a the bot's `scheduler` table
* Individual jobs can be created, deleted, enabled, and disabled
* The scheduler can be started, stopped, paused, and resumed

## Core User Commands
* `about` - Display version information, system information about SwagBot's host, and information about SwagBot's process
* `dad` - Tell a dad joke
* `fortune` - Display a Unix™ fortune
* `greeting` - Greet the user in a random language or in the specified language
* `help` - Display commands available to the user as well as command-specific help
* `seen` - Display the last time \<user\> was seen by the bot
* `time` - Display the current time
* `uptime` - Display the bot's uptime

## Core Admin Commands
* `admins` - Grant admin access, revoke admin access, or list bot admins
* `commands` - Enable, disable, hide, or unhide a bot command
* `join` - Instruct the bot to join the specified channel
* `kick` - Kick \<user\> from the current channel (this may not always work)
* `leave` - Instruct the bot to leave the specified channel
* `modules` - Enable, disable, or list bot modules
* `maint` - Start or stop the bot's maintenance thread
* `purpose` - Set a channel's purpose (description)
* `reload` - Reload all of the bot's modules
* `topic` - Set a channel's topic
