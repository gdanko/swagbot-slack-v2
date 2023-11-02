from pprint import pprint

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from swagbot.core import Command, Event
import logging
import os
import psutil
import shlex
import swagbot.database.core as db
import swagbot.exception as exception
import swagbot.logger as logger
import swagbot.plugins
import swagbot.globals as globals
import swagbot.utils.core as utils
import sys

class SwagBot(object):
    def __init__(self, **kwargs):
        self.debug = kwargs.get('debug', False)
        logger.configure(debug=self.debug)

        self.classname = utils.classname(self)
        self.client = None
        globals.start_time = utils.now()
        self.version = swagbot.__VERSION__

        if not 'config_file' in kwargs:
            raise exception.MissingConstructorParameter(classname=self.classname, parameter='config_file')

        globals.config_root = os.path.join(os.path.expanduser('~'), '.swagbot')
        globals.config = utils.parse_config(path=kwargs['config_file'])
        globals.schedulers = {}

        self.app_token = globals.config.get('app_token', '')
        self.bot_token = globals.config.get('bot_token', '')
        self.command_prefix = globals.config.get('command_prefix', '!')
        self.userid = globals.config.get('userid', '')
        self.initialize_bot()

    def die_if_running(self):
        pid = os.getpid()
        myproc = [proc for proc in psutil.process_iter() if proc._pid == pid][0]
        mycmdline = ' '.join(list(myproc.cmdline()))

        bots = []
        for proc in psutil.process_iter():
            try:
                cmdline = ' '.join(proc.cmdline())
                if (cmdline == mycmdline) and proc._pid != pid:
                    bots.append(proc)
            except:
                pass

        if len(bots) > 0:
            for bot in bots:
                logging.fatal('There is a bot running with the pid {}. Cannot start.'.format(bot._pid))
            sys.exit(1)

    def initialize_bot(self):
        globals.start_time = utils.now()
        self.die_if_running()

    def run(self):
        app = App(token=self.bot_token)
        self.client = app.client
        self.load_plugins(reload=False)

        @app.event('message')
        def message_handler(event, say):
            bot_event = Event(event=event)
            bot_event.say = say
            # pprint(bot_event.__dict__)
            self.process_message(bot_event)
        
        @app.event('member_joined_channel')
        def member_joined_channel_handler(event, say):
            bot_event = Event(event=event)
            bot_event.say = say
            if bot_event.user != self.userid:
                say(f'<@{bot_event.user}>, hello!')

        @app.event('member_left_channel')
        def member_left_channel_handler(event, say):
            bot_event = Event(event=event)
            bot_event.say = say
            pass

        globals.ready_time = utils.now()
        logging.info('SwagBot ready in {} seconds.'.format('{0:.4f}'.format(globals.ready_time - globals.start_time)))
        SocketModeHandler(app, self.app_token).start()

    def load_plugins(self, reload=False):
        globals.plugins = {}
        for importer, modulename, ispkg in utils.iter_namespace(swagbot.plugins):
            if modulename in globals.plugins:
                logging.warning(f'Could not load the module "{modulename}" as a module with the same name is already loaded.')
            else:
                module = db.get_module(module=modulename)
                if module:
                    if module['enabled'] == 1:
                        if reload:
                            err = utils.reload_module(module=modulename, client=self.client)
                        else:
                            err = utils.load_module(module=modulename, client=self.client)
                        if err:
                            logging.error(f'Failed to load the module {modulename}: {err}.')
                    else:
                        logging.info(f'Not loading module {modulename} because it is disabled.')
                else:
                    if 'enable_new_modules' in globals.config and globals.config['enable_new_modules']:
                        enabled = True
                        enabled_str = 'enabling it'
                    else:
                        enabled = False
                        enabled_str = 'leaving it disabled'
                    logging.info(f'I have found a new module named "{modulename}" which is not in the database. Adding the module and {enabled_str}.')
                    db.moduleadd(module=modulename, enabled=enabled)
                    err = utils.load_module(module=modulename, client=self.client)
                    if err:
                        logging.error(f'Failed to load the module {modulename}: {err}.')
        utils.prune_commands_table()
    
    def process_seen(self, userid=None, channel=None):
        userinfo = db.get_user_by_id(id=userid)
        if userinfo:
            db.update_seen(userid=userid, username=userinfo['name'], channel=channel)
        else:
            logging.error(f'User info for {userid} not found')

    def process_message(self, event):
        can_process_message = False
        at_prefix = f'<@{self.userid}> '
        message_text = event.text
        message_type_map = {
            'im': 'private',
            'channel': 'public',
        }
        message_type = message_type_map[event.channel_type]
        if message_text:
            if message_type == 'public':
                self.process_seen(userid=event.user, channel=event.channel)
            if message_type == 'public' and (message_text.startswith(self.command_prefix) or message_text.startswith(at_prefix)):
                can_process_message = True
            elif message_type == 'private':
                can_process_message = True

            if can_process_message:
                if message_text.startswith(self.command_prefix):
                    message_text = message_text.lstrip(self.command_prefix)
                elif message_text.startswith(at_prefix):
                    message_text = message_text.lstrip(at_prefix)

                argv = shlex.split(message_text, posix=False)
                command_name = argv[0]
                command_object = db.command_lookup(command=command_name)

                command = Command()
                command.event = event
                command.client = self.client
                command.message_type = message_type
                if command_object:
                    command.__dict__.update(command_object)
                    command.argv = argv
                    command.command = getattr(globals.plugins[command.module]['instance'], command.method)
                    command.name = command_name
                    if command.validate():
                        command.execute()
                else:
                    self.send(event.channel, f'Unknown command: `{command_name}`.')

    def send(self, channel, messages):
        if type(messages) == str:
            self.client.chat_postMessage(channel=channel, text=messages)
        elif type(messages) == list:
            for message in messages:
                self.client.chat_postMessage(channel=channel, text=message)
