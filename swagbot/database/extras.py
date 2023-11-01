from pprint import pprint
import os
import sqlite3
import swagbot.utils.core as utils

def currency_lookup(currency_code=None):
    table = 'currency_conversion'
    select = f'SELECT currency_name,currency_code FROM {table} where currency_code="{currency_code}" LIMIT 1'

    res = cursor.execute(select)
    for row in res:
        return row

def crypto_lookup(currency_code=None):
    table = 'crypto_conversion'
    select = f'SELECT currency_name,currency_code FROM {table} where currency_code="{currency_code}" LIMIT 1'

    res = cursor.execute(select)
    for row in res:
        return row   

config_root = os.path.join(os.path.expanduser('~'), '.swagbot')
dbfile = os.path.join(config_root, 'swagbot.plugins.extras.db')
conn = sqlite3.connect(dbfile, check_same_thread=False)
conn.row_factory = utils.dict_factory
cursor = conn.cursor()
