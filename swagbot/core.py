from contextlib import contextmanager
from pprint import pprint
import inspect
import swagbot.database.core as db
import swagbot.globals as globals
import sys

class Event(object):
    def __init__(self, **kwargs):
        self.channel = None
        self.channel_type = None
        self.client_msg_id = None
        self.debug = False
        self.event_ts = None
        self.say = None
        self.source_team = None
        self.success = True
        self.team = None
        self.text = None
        self.ts = None
        self.type = None
        self.user = None
        self.user_team = None
        # self.__dict__.update(kwargs) # This will populate self from whatever is in kwargs

        event = kwargs.get('event')
        for key, value in event.items():
            setattr(self, key, value)
        
class Command(object):
    def __init__(self, **kwargs):
        self.argv = None
        self.client = None
        self.command = None
        self.command_object = None
        self.debug = False
        self.enabled = None
        self.event = None
        self.is_admin = None
        self.message_type = None
        self.method = None
        self.module = None
        self.monospace = False
        self.name = None
        self.output = CommandOutput()
        self.split_output = False
        self.success = False
        self.type = None
        self.usage = None
        self.__dict__.update(kwargs)

    def validate(self):
        admininfo = db.get_admin_by_id(id=self.event.user)
        is_admin = 1 if admininfo else 0
        if self.name:
            if self.enabled == True:
                if (self.is_admin and not is_admin) and not self.event.user in globals.config['owners']:
                    self.output.errors.append(f'You are not permitted to use the command "{self.name}".')

                if self.type != 'all' and self.type != self.message_type:
                    self.output.errors.append(f'The command "{self.name}" cannot be used in {self.type}.')
            else:
                self.output.errors.append(f'The command "{self.name}" is not currently enabled.')
        else:
            self.output.errors.append(f'The command "{self.name}" was not found. This is a fatal error.')

    def execute(self):
        self.command(self)

    def process_private(self):
        if self.split_output:
            for message in self.output.messages:
                if self.monospace:
                    message = f'```{message}```'
                self.send(self.event.channel, message)
        else:
            message = '\n'.join(self.output.messages)
            if self.monospace:
                message = f'```{message}```'
            self.send(self.event.channel, message)

    def process_public(self):
        at = f'<@{self.event.user}>'
        self.send(self.event.channel, at)
        if self.split_output:
            for message in self.output.messages:
                if self.monospace:
                    message = f'```{message}```'
                self.send(self.event.channel, message)
        else:
            message = '\n'.join(self.output.messages)
            if self.monospace:
                message = f'```{message}```'
            self.send(self.event.channel, message)
    
    def process_error(self):
        errors = []
        if self.message_type == 'private':
            errors = '\n'.join(self.output.errors)
            errors = f'```{errors}```'
            # for error in self.output.errors:
            #     errors.append(f'```{error}```')
            self.send(self.event.channel, errors)
        elif self.message_type == 'public':
            at = f'<@{self.event.user}>'
            for error in self.output.errors:
                errors.append(f'```{at} {error}```')
            self.send(self.event.channel, errors)
    
    def process_output(self):
        if self.success:
            if self.message_type == 'private':
                self.process_private()
            elif self.message_type == 'public':
                self.process_public()
        else:
            self.process_error()

    def send(self, channel, messages):
        if type(messages) == str:
            self.client.chat_postMessage(channel=channel, text=messages)
        elif type(messages) == list:
            for message in messages:
                self.client.chat_postMessage(channel=channel, text=message)

class BasePlugin(object):
    def __init__(self, client):
        self.classname = self.__class__.__module__

    @contextmanager
    def redirect_stdout_stderr(self, stream):
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stream
        sys.stderr = stream
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

class CommandOutput(object):
    def __init__(self, **kwargs):
        self.classname = self.__class__
        self.messages = []
        self.errors = []

def current_class():
    return inspect.stack()[1][3]

def parent_class():
    return inspect.stack()[2][3]
