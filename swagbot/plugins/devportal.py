from swagbot.core import BasePlugin
import argparse

class Plugin(BasePlugin):
    def __init__(self, client):
        self.__configure_parsers()
        self.methods = self.__setup_methods()
        BasePlugin.__init__(self, client)

        self.client = client

###############################################################################
#
# Argument Parsers
#
###############################################################################

    def __configure_parsers(self):
        pass

    def __setup_methods(self):
        return {}