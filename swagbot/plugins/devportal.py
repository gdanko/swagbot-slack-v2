from swagbot.core import BasePlugin
import argparse

class Plugin(BasePlugin):
    def __init__(self, client):
        self.__configure_parsers()
        self.methods = self.__setup_methods()
        BasePlugin.__init__(self, client)

        self.client = client
    
    def newcommand(self, command=None):
        self.send_plain(command.event.channel, 'I am a new command')

###############################################################################
#
# Argument Parsers
#
###############################################################################

    def __configure_parsers(self):
        pass

    def __setup_methods(self):
        return {
            'newcommand': {
                'description': 'I am a new command.',
                'usage': 'newcommand -- Test',
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 1,
                'monospace': 0,
                'split_output': 0,
            },
        }