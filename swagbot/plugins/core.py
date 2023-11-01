from cpuinfo import get_cpu_info
from datetime import datetime
from slack_sdk.errors import SlackApiError
from swagbot.core import BasePlugin
import argparse
import base64
import dill
import logging
import os
import platform
import psutil
import re
import swagbot.database.core as db
import swagbot.globals as globals
import swagbot.utils.core as utils
import swagbot.utils.scheduler as scheduler_utils
import sys
import time

from pprint import pprint

class Plugin(BasePlugin):
    def __init__(self, client):
        self.__configure_parsers()
        self.methods = self.__setup_methods()
        BasePlugin.__init__(self, client)

        self.formatter = '%Y-%m-%d %H:%M:%S'
        self.client = client

    # Non-admin commands
    def about(self, command=None):
        process = psutil.Process(os.getpid())
        if process:
            command.success = True
            command.output.messages.append(f'SwagBot version {globals.bot.version} -- Now with more swagger!™')
            command.output.messages.append('©2010-2023 Gary Danko')
            command.output.messages.append('Bot Information')
            messages_dict = {
                'platform': platform.platform(),
                'release': platform.version(),
                'architecture': platform.machine(),
                'cpu_type': f'{get_cpu_info()["count"]} x {get_cpu_info()["brand_raw"]}',
                'memory_total': f'{utils.to_gb(psutil.virtual_memory()[0])} GB',
                'python': sys.version.split('\n')[0].rstrip(),
                'pid': process.pid,
                'created': datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S'),
                'user': process.username(),
                'threads': process.num_threads(),
                'cpu_usage': '%.2f%%' % float(process.cpu_percent()),
                'memory_usage': '%.2f%%' % float(process.memory_percent()),
                'status': process.status(),
            }
            length = 0
            for item in messages_dict.keys():
                if len(item) > length:
                    length = len(item)
            formatter = '  {{:{}}} = {{}}'.format(length)
            for k, v in messages_dict.items():
                if v not in ['', None]:
                    k = k.lstrip() if isinstance(k, str) else k
                    v = v.lstrip() if isinstance(v, str) else v
                    command.output.messages.append(formatter.format(k, v))

    def greeting(self, command=None):
        command.argv.pop(0)
        language = command.argv[0] if len(command.argv) == 1 else None # Account for invalid input
        greeting = db.greeting(language=language)
        if greeting:
            command.success = True
            command.output.messages.append(f'{greeting["greeting"]}! This is how you greet someone in {greeting["language"]}.')
        else:
            command.output.errors.append('Oops! I was not able to find any available greetings.')

    def help(self, command=None):
        admininfo = db.get_admin_by_id(id=command.event.user)
        is_admin = 1 if admininfo else 0

        command.argv.pop(0)
        help_command = command.argv[0] if len(command.argv) == 1 else None # Account for invalid input
        if help_command:
            command_info = db.command_lookup(command=help_command)
            if command_info and command_info['enabled']:
                command.success = True
                command.output.messages.append(command_info['usage'])
            else:
                command.output.errors.append(f'No help found for "{help_command}"')
        else:
            commands = db.help2(is_admin=is_admin)
            if commands:
                longest = 0
                for bot_command in commands:
                    if len(bot_command['command']) > longest:
                        longest = len(bot_command['command'])
                formatter = '   {{:<{}}}       {{}}'.format(longest)
                command.output.messages.append('SwagBot commands available to you:')
                command.output.messages.append('')
                for bot_command in commands:
                    command.output.messages.append(
                        formatter.format(bot_command['command'], bot_command['description'])
                    )
                command.output.messages.append('')
                command.output.messages.append('Use "help <command>" for command-specific help.')
                command.success = True

    def seen(self, command=None):
        command.argv.pop(0)
        name = command.argv[0]
        if name:
            userinfo = db.get_seen(username=name)
            command.success = True
            if userinfo:
                command.output.messages.append(f'<@{name}> was last seen at {utils.ts_to_human(userinfo["seen_time"])}.')
            else:
                command.output.messages.append(f'I haven\'t seen <@{name}>.')

    def time(self, command=None):
        human_time = utils.current_time()
        command.success = True
        command.output.messages.append('It is now {}.'.format(human_time))

    def uptime(self, command=None):
        process = psutil.Process(os.getpid())
        seconds = utils.now() - int(process.create_time())
        if seconds == 0: seconds = 1

        days, hours, minutes, seconds = utils.duration(seconds)
        now = datetime.fromtimestamp(utils.now()).strftime('%H:%M')

        d = 'days' if days > 1 else 'day'

        message = [ '{} up '.format(now) ]
        if days > 0:
            message.append('{} {}'.format(days, d))
        message.append('{}:{}:{}'.format(
            str(hours).zfill(2),
            str(minutes).zfill(2),
            str(seconds).zfill(2))
        )
        command.success = True
        command.output.messages.append(' '.join(message))

###############################################################################
#
# Scheduled Jobs functions
#
###############################################################################

    def jobs(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.jobs_parser.parse_args()
        except:
            if sys.argv[1] in help:
                command.output.errors.append(help[sys.argv[1]])
            else:
                command.output.errors.append(self.jobs_parser.format_help().rstrip())
            return

        if args.enable:
            success, message = scheduler_utils.enable(id=args.enable)
            if success:
                command.success = True
                command.output.messages.append(message)
            else:
                command.output.errorrs.append(message)
        elif args.disable:
            success, message = scheduler_utils.disable(id=args.disable)
            if success:
                command.success = True
                command.output.messages.append(message)
            else:
                command.output.errorrs.append(message)
        elif args.run:
            job = scheduler_utils.get_job_by_id(id=args.run)
            if job:
                logging.info(f'Executing the job {job["module"]}.{job["name"]}.')
                try:
                    decoded = dill.loads(base64.b64decode(job['function']))
                    fn, args = decoded
                    fn(*args)
                    command.success = True
                    command.output.messages.append(f'Successfully executed the job {job["module"]}.{job["name"]}.')
                except Exception as e:
                    logging.error(f'Failed to execute the job {job["module"]}.{job["name"]}: {e}')
            else:
                command.output.errors.append(f'Job ID {args.run} not found.')
        else:
            job_list = scheduler_utils.list()
            if job_list:
                if len(job_list) > 0:
                    command.success = True
                    for chunk in job_list:
                        command.output.messages.append(chunk)
                else:
                    command.error.messages.append('No scheduled jobs found.')
            else:
                command.error.messages.append('An error occurred when trying to fetch the scheduled job list.')            

    def reload(self, command=None):
        sleep_period = 60
        command.success = True
        command.output.messages.append('before:')
        for plugin_name, plugin in globals.plugins.items():
            command.output.messages.append(str(plugin))
        
        for name, scheduler in globals.schedulers.items():
            scheduler.stop()
        logging.info(f'Restarting in {sleep_period} seconds...')
        time.sleep(sleep_period)

        globals.bot.load_plugins(reload=True)

        command.output.messages.append('after:')
        for _, plugin in globals.plugins.items():
            command.output.messages.append(str(plugin))
        command.success = True

    def admins(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.admins_parser.parse_args()
        except:
            command.output.errors.append(self.admins_parser.format_help().rstrip())
            return

        if args.grant:
            admininfo = db.get_admin_by_name(name=args.grant)
            if admininfo:
                command.output.errors.append(f'User "{args.grant}" is already an admin.')
            else:
                userinfo = db.get_user_by_name(name=args.grant)
                if userinfo:
                    db.admin_grant(id=userinfo['id'], name=userinfo['name'], real_name=userinfo['real_name'])
                    admininfo = db.get_admin_by_name(name=args.grant)
                    if admininfo:
                        command.success = True
                        command.output.messages.append(f'User "{args.grant}" was successfully granted admin access.')
                    else:
                        command.output.errors.append(f'Failed to grant admin access to "{args.grant}".')
                else:
                    command.output.errors.append(f'Username "{args.grant} not found. Please try again later or contact a bot administrator.')
        elif args.revoke:
            admininfo = db.get_admin_by_name(name=args.revoke)
            if not admininfo:
                command.output.errors.append(f'User "{args.revoke}" is not an admin.')
            else:
                db.admin_revoke(name=args.revoke)
                admininfo = db.get_admin_by_name(name=args.revoke)
                if not admininfo:
                    command.success = True
                    command.output.messages.append(f'Admin access for "{args.revoke}" was successfully revoked.')
                else:
                    command.output.errors.append(f'Failed to revoke admin access for "{args.revoke}".')
        else:
            results = db.admin_list()
            if results and len(results) > 0:
                admins = [[item['real_name'], item['name']] for item in results]
                command.output.messages.append(utils.generate_table(headers=['Name', 'Username'], data=admins))
                command.success = True
            else:
                command.output.errors.append('Oh crap! No admins found.')

    def commands(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.commands_parser.parse_args()
        except:
            command.output.errors.append( self.commands_parser.format_help().rstrip())
            return
        if args.enable:
            to_enable = db.command_lookup(command=args.enable)
            if to_enable:
                if to_enable['enabled'] == 0:
                    db.enable_command(command=args.enable)
                    command.success = True
                    command.output.messages.append(f'The command "{args.enable}" was enabled.')
                else:
                    command.output.errors.append(f'The command "{args.enable}" is already enabled.')
            else:
                command.output.errors.append(f'The command "{args.enable}" was not found.')
        elif args.disable:
            to_disable = db.command_lookup(command=args.disable)
            if to_disable:
                if to_disable['enabled'] == 1:
                    if to_disable['can_be_disabled'] == 0:
                        command.output.success = False
                        command.output.errors.append(f'The command "{args.disable}" cannot be disabled.')
                    else:
                        db.disable_command(command=args.disable)
                        command.success = True
                        command.output.messages.append(f'The command "{args.disable}" was disabled.')
                else:
                    command.output.errors.append(f'The command "{args.disable}" is already disabled.')
            else:
                command.output.errors.append(f'The command "{args.disable}" was not found.')
        elif args.hide:
            to_hide = db.command_lookup(command=args.hide)
            if to_hide:
                if not to_hide['hidden'] == 1:
                    db.hide_command(command=args.hide)
                    command.success = True
                    command.output.messages.append(f'The command "{args.hide}" was hidden.')
                else:
                    command.output.errors.append(f'The command "{args.hide}" is already hidden.')
            else:
                command.output.errors.append(f'The command "{args.hide}" was not found.')
        elif args.unhide:
            to_unhide = db.command_lookup(command=args.unhide)
            if to_unhide:
                if to_unhide['hidden'] == 1:
                    db.unhide_command(command=args.unhide)
                    command.success = True
                    command.output.messages.append(f'The command "{args.unhide}" was unhidden.')
                else:
                    command.output.errors.append(f'The command "{args.unhide}" is already unhidden.')
            else:
                command.output.errors.append(f'The command "{args.unhide}" was not found.')

###############################################################################
#
# Module functions
#
###############################################################################

    def modules(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.modules_parser.parse_args()
        except:
                command.output.errors.append(self.modules_parser.format_help().rstrip())
                return

        if args.enable:
            to_enable = db.get_module(module=args.enable)
            if to_enable:
                if to_enable['enabled'] == 0:
                    db.enable_module(module=args.enable)
                    command.success = True
                    command.output.messages.append(f'The module "{args.enable}" was enabled.')
                    globals.bot.reload_plugins()
                    
                    commands = db.module_commands(module=args.enable)
                    if len(commands) > 0:
                        command.output.messages.append(f'The following commands are now available: {", ".join(sorted(commands))}')
                else:
                    command.output.errors.append(f'The module "{args.enable}" is already enabled.')
            else:
                command.output.errors.append(f'The module "{args.enable}" was not found.')
        elif args.disable:
            to_disable = db.get_module(module=args.disable)
            if to_disable:
                if to_disable['enabled'] == 1:
                    if to_disable['can_be_disabled'] == 0:
                        command.output.errors.append(f'The module "{args.disable}" cannot be disabled.')
                    else:
                        db.disable_module(module=args.disable)
                        command.success = True
                        command.output.messages.append(f'The module "{args.disable}" was disabled.')

                        commands = db.module_commands(module=args.disable)
                        if len(commands) > 0:
                            command.output.messages.append(f'The following commands will no longer be available: {", ".join(sorted(commands))}')
                        globals.bot.reload_plugins()
                else:
                    command.output.errors.append(f'The module "{args.disable}" is already disabled.')
            else:
                command.output.errors.append(f'The module "{args.disable}" was not found.')
        else:
            results = db.module_list()
            if results and len(results) > 0:
                modules = [[item['module'], 'Enabled' if item['enabled'] == 1 else 'Disabled'] for item in results]
                command.output.messages.append(utils.generate_table(headers=['Module', 'Status'], data=modules))
                command.success = True
            else:
                command.output.errors.append('Oh crap! No modules found.')            

###############################################################################
#
# Channel functions
#
###############################################################################

    def channels(self, command=None):
        help = {}
        for action in self.channels_parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for choice, subparser in action.choices.items():
                    help[choice] = subparser.format_help()

        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.channels_parser.parse_args()
        except:
            if sys.argv[1] in help:
                command.output.errors.append(help[sys.argv[1]])
            else:
                command.output.errors.append(self.channels_parser.format_help().rstrip())
            return

        try:
            args.func(args, command)
        except Exception as e:
            command.output.errors.append(self.channels_parser.format_help().rstrip())
            return
    
    def channels_invite(self, args, command):
        userinfo = db.get_user_by_name(name=args.name)
        if not userinfo:
            command.output.errors.append(f'Failed to get user info for "{args.name}".')
            return

        channel_info = db.get_channel_by_name(name=args.channel)
        if not channel_info:
            command.output.errors.append(f'Failed to get channel info for "{args.channel}".')
            return
        try:
            self.client.conversations_invite(
                channel=channel_info['id'],
                users=userinfo['id'],
            )
            command.success = True
        except SlackApiError as e:
            logging.error(f'Failed to invite {args.name} to {args.channel}: {e.response.data["error"]}')
            bot_error = utils.error_ineterpolator(
                method='conversations_invite',
                error=e.response.data['error'],
                replacements={'user': args.name, 'channel': args.channel},
                quote_replacements=True,
            )
            if bot_error:
                command.output.errors.append(bot_error)
            else:
                command.output.errors.append(f'Failed to invite {args.name} to {args.channel}.')
        except Exception as e:
            logging.error(f'Failed to invite {args.name} to "{args.channel}": Unknown error')
            command.output.errors.append(f'Failed to invite {args.name} to {args.channel}.')

    def channels_join(self, args, command):
        if args.channel.startswith('<#'):
            result = re.search(self.channel_pattern, args.channel)
            if result:
                channel_id = result.group(0)
        else:
            channel_name_stripped = args.channel.lstrip('#')
            channel_info = db.get_channel_by_name(name=channel_name_stripped)
            if channel_info:
                channel_id = channel_info['id']
        if channel_id:
            try:
                self.client.conversations_join(
                    channel=channel_id
                )
                command.output.messages.append(f'Successfully joined "{args.channel}"')
                command.success = True
            except SlackApiError as e:
                logging.error(f'Failed to join "{args.channel}": {e.response.data["error"]}')
                command.output.errors.append(f'Failed to join "{args.channel}"')
            except Exception as e:
                logging.error(f'Failed to join "{args.channel}": Unknown error.')
                command.output.errors.append(f'Failed to join "{args.channel}"')
        else:
            command.output.errors.append(f'Failed to join "{args.channel}"')

    def channels_kick(self, args, command):
        if args.name:
            userinfo = db.get_user_by_name(name=args.name)
            if not userinfo:
                command.output.errors.append(f'Failed to get user info for "{args.name}".')
                return

        if args.channel:
            channel_info = db.get_channel_by_name(name=args.channel)
            if not channel_info:
                command.output.errors.append(f'Failed to get channel info for "{args.channel}".')
                return
        try:
            self.client.conversations_kick(
                channel=channel_info['id'],
                user=userinfo['id'],
            )
            command.success = True
        except SlackApiError as e:
            logging.error(f'Failed to kick "{args.name}" from "{args.channel}": {e.response.data["error"]}')
            command.output.errors.append(f'Failed to kick "{args.name}" from "{args.channel}"')
        except Exception as e:
            logging.error(f'Failed to kick "{args.name}" from "{args.channel}": Unknown error')
            command.output.errors.append(f'Failed to kick "{args.name}" from "{args.channel}"')

    def channels_leave(self, args, command):
        if args.channel.startswith('<#'):
            result = re.search(self.channel_pattern, args.channel)
            if result:
                channel_id = result.group(0)
        else:
            channel_name_stripped = args.channel.lstrip('#')
            channel_info = db.get_channel_by_name(name=channel_name_stripped)
            if channel_info:
                channel_id = channel_info['id']
        if channel_id:
            try:
                self.client.conversations_leave(
                    channel=channel_id
                )
                command.output.messages.append(f'Successfully left "{args.channel}"')
                command.success = True
            except SlackApiError as e:
                logging.error(f'Failed to leave "{args.channel}": {e.response.data["error"]}')
                command.output.errors.append(f'Failed to leave "{args.channel}"')
            except Exception as e:
                logging.error(f'Failed to leave "{args.channel}": Unknown error.')
                command.output.errors.append(f'Failed to join "{args.channel}"')
        else:
            command.output.errors.append(f'Failed to leave "{args.channel}"')

    def channels_purpose(self, args, command):
        pass
        # Need a function to better handle verification
        sys.argv = command.argv[0:4]
        sys.argv.append(' '.join(command.argv[4:]))
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.purpose_parser.parse_args()
        except:
            command.output.errors.append(self.kick_parser.format_help().rstrip())
            return

        channel = db.get_channel_by_name(name=args.channel)
        if channel:
            try:
                self.client.conversations_setPurpose(
                    channel=args.channel,
                    purpose=args.purpose,
                )
                command.success = True
                command.output.messages.append('The channel\'s purpose was successfully set.')
            except SlackApiError as e:
                command.output.errors.append('Failed to set the channel\'s purpose.')
                logging.error(f'Failed to set the channel description: {e.response.data["error"]}')
                return
            except Exception as e:
                command.output.errors.append('Failed to set the channel\'s purpose.')
                logging.error(f'Failed to set the channel\'s purpose: Unknown error.')
                return
        else:
            command.output.errors.append(f'Channel "{args.channel}" not found. If this is a valid channel, please contact a bot administrator.')

    def channels_topic(self, args, command):
        pprint(args)
        pprint(sys.argv)
        pass
        # Need a function to better handle verification
        sys.argv = command.argv[0:4]
        sys.argv.append(' '.join(command.argv[4:]))
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.topic_parser.parse_args()
        except:
            command.output.errors.append(self.topic_parser.format_help().rstrip())
            return

        channel = db.get_channel_by_name(name=args.channel)
        if channel:
            try:
                self.client.conversations_setTopic(
                    channel=channel['id'],
                    topic=args.topic
                )
                command.success = True
                command.output.messages.append('The channel\'s topic was successfully set.')
            except SlackApiError as e:
                command.output.errors.append('Failed to set the channel\'s topic.')
                logging.error(f'Failed to set the channel\'s topic: {e.response.data["error"]}')
                return
            except Exception as e:
                command.output.errors.append('Failed to set the channel\'s topic.')
                logging.error(f'Failed to set the channel\'x topic: Unknown error.')
                return
        else:
            command.output.errors.append(f'Channel "{args.channel}" not found. If this is a valid channel, please contact a bot administrator.')

    def whisper(self, command=None):
        sys.argv = command.argv
        pprint(sys.argv)
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.whisper_parser.parse_args()
        except:
            command.output.errors.append(self.whisper_parser.format_help().rstrip())
            return
        
        userinfo = db.get_user_by_name(name=args.username)
        if not userinfo:
            command.output.errors.append(f'Failed to get user info for "{args.username}".')
            return
        
        
        try:
            self.client.chat_postMessage(
                channel=userinfo['id'],
                text=args.message,
            )
            command.output.messages.append(f'Successfully whispered to <@{args.username}>')
            command.success = True
        except SlackApiError as e:
            command.output.errors.append(f'Failed to whisper to <@{args.username}>')
            logging.error(f'Failed to whisper to {args.username}: {e.response.data["error"]}')
        
    def __configure_parsers(self):
        self.about_parser = argparse.ArgumentParser(add_help=False, prog='about', description='Display information about this bot.')
        self.about_parser.set_defaults(func=self.about)

        # Admins
        self.admins_parser = argparse.ArgumentParser(add_help=False, prog='admins', description='List bot admins, grant or revoke admin access.')
        self.admins_parser.add_argument('-g', '--grant', help='Grant admin access to a user.', metavar='<username>', action='store')
        self.admins_parser.add_argument('-r', '--revoke', help='Revoke admin access from a user.', metavar='<username>', action='store')

        # Channels
        self.channels_parser = argparse.ArgumentParser(add_help=False, prog='channels', description='Join a channel, leave a channel, invite a user to a channel, set a channel\'s topic or purpose.', epilog='Use "channels <subcommand> --help" for help with subcommands.')
        self.channels_parser.set_defaults(func=self.channels)
        subparsers = self.channels_parser.add_subparsers(help='Sub-command help')

        parser_channels_invite = subparsers.add_parser('invite', add_help=False, help='Invite a user to a channel.')
        parser_channels_invite.add_argument('-n', '--name', help='The username to invite.', metavar='<username>', required=True, action='store')
        parser_channels_invite.add_argument('-c', '--channel', help='The channel to invite them to.', metavar='<channel>', required=True, action='store')
        parser_channels_invite.set_defaults(func=self.channels_invite)

        parser_channels_join = subparsers.add_parser('join', add_help=False, help='Ask the bot to join a channel.')
        parser_channels_join.add_argument('-c', '--channel', help='The channel to join.', metavar='<channel>', required=True, action='store')
        parser_channels_join.set_defaults(func=self.channels_join)

        parser_channels_leave = subparsers.add_parser('leave', add_help=False, help='Ask the bot to leave a channel.')
        parser_channels_leave.add_argument('-c', '--channel', help='The channel to leave.', metavar='<channel>', required=True, action='store')
        parser_channels_leave.set_defaults(func=self.channels_leave)

        # parser_channels_kick = subparsers.add_parser('kick', add_help=False, help='Ask the bot to kick a user from a channel.')
        # parser_channels_kick.add_argument('-n', '--name', help='The username to kick.', metavar='<username>', required=True, action='store')
        # parser_channels_kick.add_argument('-c', '--channel', help='The channel to kick them from.', metavar='<channel>', required=True, action='store')
        # parser_channels_kick.set_defaults(func=self.channels_kick)

        parser_channels_purpose = subparsers.add_parser('purpose', add_help=False, help='Set a channel\'s purpose (description).')
        parser_channels_purpose.add_argument('-c', '--channel', help='The channel to kick them from.', metavar='<channel>', required=True, action='store')
        parser_channels_purpose.add_argument('-p', '--purpose', help='The purpose.', metavar='<purpose>', required=True, action='store')
        parser_channels_purpose.set_defaults(func=self.channels_purpose)

        parser_channels_topic = subparsers.add_parser('topic', add_help=False, help='Set a channel\'s topic.')
        parser_channels_topic.add_argument('-c', '--channel', help='The channel to kick them from.', metavar='<channel>', required=True, action='store')
        parser_channels_topic.add_argument('-t', '--topic', help='The topic.', metavar='<topic>', required=True, action='store')
        parser_channels_topic.set_defaults(func=self.channels_purpose)

        # Commands
        self.commands_parser = argparse.ArgumentParser(add_help=False, prog='commands', description='Enable, disable, hide, or unhide a bot command.')
        self.commands_parser.add_argument('-e', '--enable', help='Enable a bot command.', metavar='<command>', action='store')
        self.commands_parser.add_argument('-d', '--disable', help='Disable a bot command.', metavar='<command>', action='store')
        self.commands_parser.add_argument('-h', '--hide', help='Hide a bot command.', metavar='<command>', action='store')
        self.commands_parser.add_argument('-u', '--unhide', help='Unhide a bot command.', metavar='<command>', action='store')

        self.greeting_parser = argparse.ArgumentParser(add_help=False, prog='greeting', description='Learn how to greet someone in a random language or specify a language to see how to greet someone.')
        self.greeting_parser.set_defaults(func=self.greeting)

        self.help_parser = argparse.ArgumentParser(add_help=False, prog='help', description='Display a list of commands or usage for a specific command.')
        self.help_parser.set_defaults(func=self.help)

        # Jobs
        self.jobs_parser = argparse.ArgumentParser(add_help=False, prog='jobs', description='Manage the SwagBot job scheduler. Use "jobs" without arguments to list scheduled jobs.')
        self.jobs_parser.add_argument('-e', '--enable', help='The ID of the job to enable.', metavar='<id>', action='store')
        self.jobs_parser.add_argument('-d', '--disable', help='The ID of the job to disable.', metavar='<id>', action='store')
        self.jobs_parser.add_argument('-r', '--run', help='The ID of the job to run.', metavar='<id>', action='store')
        self.jobs_parser.set_defaults(func=self.jobs)

        # Modules
        self.modules_parser = argparse.ArgumentParser(add_help=False, prog='modules', description='List, enable, or disable bot modules. Use "modules" without arguments to list modules.')
        self.modules_parser.add_argument('-e', '--enable', help='Enable a module and all of its commands.', metavar='<module>', action='store')
        self.modules_parser.add_argument('-d', '--disable', help='Disablea module and all of its commands.', metavar='<modules>', action='store')

        self.reload_parser = argparse.ArgumentParser(add_help=False, prog='reload', description='Reload all confiugred modules.')
        self.reload_parser.set_defaults(func=self.reload)

        self.seen_parser = argparse.ArgumentParser(add_help=False, prog='seen', description='Show when <username> was last seen.')
        self.seen_parser.set_defaults(func=self.seen)

        self.time_parser = argparse.ArgumentParser(add_help=False, prog='time', description='Display the current local time.')
        self.time_parser.set_defaults(func=self.time)

        self.uptime_parser = argparse.ArgumentParser(add_help=False, prog='uptime', description='Display the bot\'s uptime.')
        self.uptime_parser.set_defaults(func=self.uptime)

        self.whisper_parser = argparse.ArgumentParser(add_help=False, prog='whisper', description='Ask the bot to whisper something to another user.')
        self.whisper_parser.add_argument('-u', '--username', help='The username to whisper to.', metavar='<username>', required=True, action='store') 
        self.whisper_parser.add_argument('-m', '--message', help='The message to whisper to <user>.', metavar='<message>', required=True, action='store')

    def __setup_methods(self):
        return {
            'about': {
                'description': self.about_parser.description,
                'usage': self.about_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 0,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'greeting': {
                'description': self.greeting_parser.description,
                'usage': self.greeting_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 0,
                'hidden': 0,
                'monospace': 0,
                'split_output': 0,
            },
            'help': {
                'description': self.help_parser.description,
                'usage': self.help_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 0,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'seen': {
                'description': self.seen_parser.description,
                'usage': self.seen_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 0,
                'split_output': 0,
            },
            'time': {
                'description': self.time_parser.description,
                'usage': self.time_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 0
            },
            'uptime': {
                'description': self.uptime_parser.description,
                'usage': self.uptime_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            # Command-specific stuff
            'commands': {
                'description': self.commands_parser.description,
                'usage': self.commands_parser.format_help().rstrip(),
                'is_admin': 1,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            # Module-specific commands
            'modules': {
                'description': self.modules_parser.description,
                'usage': self.modules_parser.format_help().rstrip(),
                'is_admin': 1,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            # Channel-specific commands
            'channels': {
                'description': self.channels_parser.description,
                'usage': self.channels_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 0,
                'hidden': 0,
                'monospace': 0,
                'split_output': 0,
            },
            # Miscellany
            'admins': {
                'description': self.admins_parser.description,
                'usage': self.admins_parser.format_help().rstrip(),
                'is_admin': 1,
                'type': 'all',
                'can_be_disabled': 0,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'jobs': {
                'description': self.jobs_parser.description,
                'usage': self.jobs_parser.format_help().rstrip(),
                'is_admin': 1,
                'type': 'private',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'reload': {
                'description': self.reload_parser.description,
                'usage': self.reload_parser.format_help().rstrip(),
                'is_admin': 1,
                'type': 'all',
                'can_be_disabled': 0,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'whisper': {
                'description': self.whisper_parser.description,
                'usage': self.whisper_parser.format_help().rstrip(),
                'is_admin': 1,
                'type': 'private',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 0,
                'split_output': 0,
            },
        }
