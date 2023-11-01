from pprint import pprint

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from swagbot.core import Command, Event
import importlib
import logging
import os
import pkgutil
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
        self.start_time = utils.now()
        self.version = swagbot.__VERSION__

        if not 'config_file' in kwargs:
            raise exception.MissingConstructorParameter(classname=self.classname, parameter='config_file')

        # parse_config needs to adequately parse the config file. right now it does not.
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
        self.start_time = utils.now()
        self.die_if_running()

    def run(self):
        self.start_time = utils.now()
        app = App(token=self.bot_token)
        self.client = app.client
        self.load_plugins(reload=False)

        @app.event('message')
        def message_handler(event, say):
            bot_event = Event(event=event)
            bot_event.say = say
            # pprint(bot_event.__dict__)
            self.process_message(bot_event, say)
        
        @app.event('member_joined_channel')
        def member_joined_channel_handler(event, say):
            bot_event = Event(event=event)
            bot_event.say = say
            # pprint(bot_event.__dict__)
            if bot_event.user != self.userid:
                say(f'<@{bot_event.user}>, hello!')

        self.ready_time = utils.now()
        logging.info('SwagBot ready in {} seconds.'.format('{0:.4f}'.format(self.ready_time - self.start_time)))
        SocketModeHandler(app, self.app_token).start()

    def iter_namespace(self, ns_pkg):
        # Specifying the second argument (prefix) to iter_modules makes the
        # returned name an absolute name instead of a relative one. This allows
        # import_module to work without having to do additional modification to the name.
        return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + '.')

    def load_plugins(self, reload=False):
        loading = 'Reloading' if reload else 'Loading'
        globals.plugins = {}
        for importer, modulename, ispkg in self.iter_namespace(swagbot.plugins):
            if modulename in globals.plugins:
                logging.warning(f'Could not load the module "{modulename}" as a module with the same name is already loaded.')
            else:
                module = db.get_module(module=modulename)
                if module:
                    if module['enabled'] == 1:
                        logging.info(f'{loading} module {modulename}.')
                        module_obj = importlib.import_module(modulename)
                        if reload:
                            importlib.reload(module_obj)
                        module_instance = module_obj.Plugin(client=self.client)
                        logging.info(f'Updating bot commands for the module {modulename}.')
                        db.update_plugin_commands(module=module_instance.classname, methods=module_instance.methods)
                        globals.plugins[modulename] = {
                            'module': modulename,
                            'instance': module_instance,
                        }
                    else:
                        logging.info(f'Not loading module {modulename} because it is disabled.')
                else:
                    logging.info(f'I have found a new module named "{modulename}" which is not in the database. I will insert it and leave it disabled.')
                    db.moduleadd(module=modulename)

    def sanitize_module_name(self, name):
        separator = '.'
        module_bits = name.split(separator)
        module_bits.pop()
        return separator.join(module_bits)

    def prune_commands_table(self):
        loaded_commands = []
        for _, plugin_obj in globals.plugins.items():
            plugin_instance = plugin_obj['instance']
            if hasattr(plugin_instance, 'methods'):
                loaded_commands += list(plugin_instance.methods.keys())
        loaded_commands = sorted(loaded_commands)

        command_table_commands = db.all_commands()

        to_prune = list(set(command_table_commands) - set(loaded_commands))
        if len(to_prune) > 0:
            command = 'command' if len(to_prune) == 1 else 'commands'
            logging.info('Pruning {} {} from the commands table.'.format(len(to_prune), command))
            db.prune_commands_table(commands=to_prune)
    
    def process_seen(self, userid=None, channel=None):
        userinfo = db.get_user_by_id(id=userid)
        if userinfo:
            db.update_seen(userid=userid, username=userinfo['name'], channel=channel)
        else:
            logging.error(f'User info for {userid} not found')

    def process_message(self, event, say):
        process_message = False
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
                process_message = True
            elif message_type == 'private':
                process_message = True

            if process_message:
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
                    command.validate()
                    if len(command.output.errors) > 0:
                        command.process_error()
                    else:
                        command.execute()
                        command.process_output()
                else:
                    command.output.errors.append(f'Unknown command: "{command_name}"')
                    command.process_error()
