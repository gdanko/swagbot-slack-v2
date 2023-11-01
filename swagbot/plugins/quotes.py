from pprint import pprint
from swagbot.core import BasePlugin
import argparse
import os
import sqlite3
import swagbot.globals as globals
import swagbot.utils.core as utils

class Plugin(object):
    def __init__(self, client):
        self.__configure_parsers()
        self.methods = self.__setup_methods()
        BasePlugin.__init__(self, client)

        self.dbfile = os.path.join(globals.config_root, f'swagbot.plugins.quotes.db')
        self.conn = sqlite3.connect(self.dbfile, check_same_thread=False)
        self.conn.row_factory = utils.dict_factory
        self.cursor = self.conn.cursor()

    def dad(self, command=None):
        quote = self.__quotes(category='dad')
        if quote:
            command.success = True
            command.output.messages.append(quote)
        else:
            command.output.errors.append('Failed to find a dad joke. :(')

    def fortune(self, command=None):
        quote = self.__quotes(category='fortunes')
        if quote:
            command.success = True
            command.output.messages.append(quote)
        else:
            command.output.errors.append('Failed to find a fortune. :(')
        
    def yomama(self, command=None):
        quote = self.__quotes(category='yomama')
        if quote:
            command.success = True
            command.output.messages.append(quote)
        else:
            command.output.errors.append('Failed to find a yomama joke. :(')

    def __quotes(self, category=None):
        select = f'SELECT quote FROM quotes where category="{category}" ORDER BY RANDOM() LIMIT 1'

        res = self.cursor.execute(select)
        for row in res:
            return row['quote']

    def __configure_parsers(self):
        self.dad_parser = argparse.ArgumentParser(add_help=False, prog='dad', description='Tell a dad joke.')
        self.dad_parser.set_defaults(func=self.dad)

        self.fortune_parser = argparse.ArgumentParser(add_help=False, prog='fortune', description='Tell a Unix fortune.')
        self.fortune_parser.set_defaults(func=self.fortune)

        self.yomama_parser = argparse.ArgumentParser(add_help=False, prog='yomama', description='Tell a (sometimes) funny yo mama joke.')
        self.yomama_parser.set_defaults(func=self.yomama)

    def __setup_methods(self):
        return {
            'dad': {
                'description': self.dad_parser.description,
                'usage': self.dad_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 1,
                'monospace': 0,
                'split_output': 0,
            },
            'fortune': {
                'description': self.fortune_parser.description,
                'usage': self.fortune_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 1,
                'monospace': 0,
                'split_output': 0,
            },
            'yomama': {
                'description': self.yomama_parser.description,
                'usage': self.yomama_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 1,
                'monospace': 0,
                'split_output': 0,
            },
        }
