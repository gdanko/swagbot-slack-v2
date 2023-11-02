from pprint import pprint
import logging
import os
import sqlite3
import swagbot.utils.core as utils

def currency_lookup(currency_code=None):
    select = f'SELECT currency_name,currency_code FROM currency_conversion where currency_code="{currency_code}" LIMIT 1'
    try:
        with conn:
            cursor = conn.cursor()
            results = cursor.execute(select)
            for row in results:
                return row
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

def crypto_lookup(currency_code=None):
    select = f'SELECT currency_name,currency_code FROM crypto_conversion where currency_code="{currency_code}" LIMIT 1'
    try:
        with conn:
            cursor = conn.cursor()
            results = cursor.execute(select)
            for row in results:
                return row
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

config_root = os.path.join(os.path.expanduser('~'), '.swagbot')
dbfile = os.path.join(config_root, 'swagbot.plugins.extras.db')
conn = sqlite3.connect(dbfile, check_same_thread=False)
conn.row_factory = utils.dict_factory
cursor = conn.cursor()
