from slack_sdk.errors import SlackApiError
from swagbot.core import BasePlugin
import argparse
import logging
import os
import swagbot.scheduler
import sys
import time

class Plugin(BasePlugin):
    def __init__(self, client):
        self.__configure_parsers()
        self.methods = self.__setup_methods()
        BasePlugin.__init__(self, client)

        self.scheduler = swagbot.scheduler.Scheduler(
            name = self.classname
        )
        self.stale_threshold = 3660
        self.client = client
        self.users = []
        self.channels = []

        self.__add_scheduled_jobs()
        self.scheduler.start()

    def update_users(self, cursor=None):
        if cursor:
            try:
                response = self.client.users_list(limit=1000, cursor=cursor)
            except SlackApiError as e:
                logging.error(f'Failed to update the user list: {e.response.data["error"]}')
                return
            except Exception as e:
                logging.error(f'Failed to update the user list: Unknown error.')
                return
        else:
            try:
                response = self.client.users_list(limit=1000)
            except SlackApiError as e:
                logging.error(f'Failed to update the user list: {e.response.data["error"]}')
                return
            except Exception as e:
                logging.error(f'Failed to update the user list: Unknown error.')
                return

        for user in response['members']:
            self.users.append(user)
        if 'response_metadata' in response and 'next_cursor' in response['response_metadata']:
            if response['response_metadata']['next_cursor'] != '':
                time.sleep(1)
                self.update_users(cursor=response['response_metadata']['next_cursor'])

    def update_channels(self, cursor=None):
        if cursor:
            try:
                response = self.client.conversations_list(limit=1000, types='public_channel', exclude_archived=True, cursor=cursor)
            except SlackApiError as e:
                logging.error(f'Failed to update the channel list: {e.response.data["error"]}')
                return
            except Exception as e:
                logging.error(f'Failed to update the channel list: Unknown error.')
                return
        else:
            try:
                response = self.client.conversations_list(limit=1000, types='public_channel', exclude_archived=True)
            except SlackApiError as e:
                logging.error(f'Failed to update the channel list: {e.response.data["error"]}')
                return
            except Exception as e:
                logging.error(f'Failed to update the channel list: Unknown error.')
                return

        for conversation in response['channels']:
            self.channels.append(conversation)
        if 'response_metadata' in response and 'next_cursor' in response['response_metadata']:
            if response['response_metadata']['next_cursor'] != '':
                time.sleep(1)
                self.update_channels(cursor=response['response_metadata']['next_cursor'])

###############################################################################
#
# PagerDuty Scheduled Job functions
#
###############################################################################

    def __add_scheduled_jobs(self):
    #     success, message = self.scheduler.delete_jobs_for_module(module=self.classname)
    #     if success:
        self.scheduler.add_job(module=self.classname, name='update_slack_users', interval=60, function=(self.update_users, ()), enabled=1)
        self.scheduler.add_job(module=self.classname, name='update_slack_channels', interval=60, function=(self.update_channels, ()), enabled=1)
        # else:
        #     logging.error(f'Failed to add the scheduled jobs for "{self.classname}": {message}')

    def maint(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.maint_parser.parse_args()
        except:
            self.send_monospace(command.event.channel, self.maint_parser.format_help().rstrip())
            return
        
        if args.pause and args.resume:
            self.send_plain(command.event.channel, '--pause and --resume are mutually exclusive.')
            return

        elif args.pause:
            if self.paused:
                self.send_plain(command.event.channel, 'The bot\'s maintenance thread is already paused.')
            else:
                self.paused = True
                self.send_plain(command.event.channel, 'The bot\'s maintenance thread has been paused.')
        
        elif args.resume:
            if not self.paused:
                self.send_plain(command.event.channel, 'The bot\'s maintenance thread is already running.')
            else:
                self.paused = False
                self.send_plain(command.event.channel, 'The bot\'s maintenance thread has been resumed.')

    def __configure_parsers(self):
        self.maint_parser = argparse.ArgumentParser(add_help=False, prog='maint', description='Pause or resume the bot\'s maintenance thread.')
        self.maint_parser.add_argument('--pause', help='Pause the bot\'s maintenance thread.', action='store_true')
        self.maint_parser.add_argument('--resume', help='Resume the bot\'s maintenance thread.', action='store_true')

    def __setup_methods(self):
        return {
            'maint': {
                'description': self.maint_parser.description,
                'usage': self.maint_parser.format_help().rstrip(),
                'is_admin': 1,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
        }
