#!/usr/bin/env python3

# from base64 import b64encode, b64decode
# from Crypto.Cipher import PKCS1_OAEP
# from Crypto.PublicKey import RSA
from pprint import pprint
import logging
import os
import re
import sqlite3
import sys

def dict_factory(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def configure_logger():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

def get_input(text=None, default=None):
    if default:
        if (default.lower() == 'yes'):
            prompt = '(Y/n)'
        elif (default.lower() == 'no'):
            prompt = '(y/N)'
    else:
        prompt = None

    if prompt:
        message = '{} {} '.format(text, prompt)
        result = input(message)
        if (result == ''):
            result = default
        elif (result.lower() == 'yes') or (result.lower() == 'y'):
            result = 'yes'
        else:
            result = 'no'
    else:
        message = '{}'.format(text)
        result = input(message)

    return result

def is_file(path):
    try:
        if os.path.isfile(path):
            return True
        else:
            return False
    except:
        return False
    return False

def make_confdir():
    logger.info('Creating the bot configuration directory.')
    try:
        os.mkdir(confdir)
    except OSError as e:
        if e.errno == 17:
            pass
        else:
            logger.fatal('Failed: {}.'.format(e))
            sys.exit(1)

def create_schema():
    logger.info('Creating the database schema.')
    config = {
        'tables': {
            'quotes': {
                'columns': {
                    'quote': { 'type': 'text', 'null': False, 'primary_key': False },
                    'category': { 'type': 'text', 'null': False, 'primary_key': False }
                },
            },
        }	
    }

    for table_name, table_obj in config['tables'].items():
        drop = 'DROP TABLE IF EXISTS {}'.format(table_name)
        res = cursor.execute(drop)
        conn.commit()

        create_arr = []
        for col_name, col_obj in table_obj['columns'].items():
            arr = []
            arr.append('{} {}'.format(col_name, col_obj['type'].upper()))
            if 'null' in col_obj and col_obj['null'] == False:
                arr.append('NOT NULL')
            if 'primary_key' in col_obj and col_obj['primary_key'] == True:
                arr.append('PRIMARY KEY')
            if 'autoincrement' in col_obj and col_obj['autoincrement'] == True:
                arr.append('AUTOINCREMENT')
            if 'unique' in col_obj and col_obj['unique'] == True:
                arr.append('UNIQUE')
            if 'default' in col_obj:
                arr.append('DEFAULT {}'.format(col_obj['default']))
            create_arr.append(' '.join(arr))
        create = 'CREATE TABLE {} ({})'.format(table_name, ', '.join(create_arr))
        cursor.execute(create)
        conn.commit()

def enable_core_plugin():
    core_plugins = [
        'swagbot.plugins.quotes'
    ]
    for plugin in core_plugins:
        logger.info('Enabling the plugin {}.'.format(plugin))
        try:
            insert = 'INSERT INTO modules (module,enabled,can_be_disabled) VALUES("{}",1,0)'.format(plugin)
            cursor.execute(insert)
            conn.commit()
        except sqlite3.IntegrityError as e:
            logger.fatal('Failed to enable the core plugin: {}'.format(e))
            sys.exit(1)

def populate_greetings_table():
    filename = os.path.join(os.getcwd(), 'greetings.txt')
    if is_file(filename):
        logger.info('Populating the greeting table.')
        cursor.execute('DELETE FROM greetings')
        with open(filename) as lines:
            for line in lines:
                line = line.rstrip()
                language,greeting = re.split('\s*,\s*', line)
                insert = 'INSERT INTO greetings (language,greeting) VALUES(?,?)'
                cursor.execute(insert, (
                    language,
                    greeting
                ))
                conn.commit()
    else:
        logger.warning('Could not populate the greetings table because the file "{}" was not found.'.format(filename))

def populate_quotes(filename=None, category=None):
    if is_file(filename):
        logger.info('Populating the {} table.'.format(category))
        cursor.execute('DELETE FROM quotes WHERE category="{}"'.format(category))
        with open(filename) as lines:
            for quote in lines:
                insert = 'INSERT INTO quotes (category, quote) VALUES(?,?)'
                cursor.execute(insert, (
                    category,
                    quote.strip()
                ))
                conn.commit()
    else:
        logger.warning('Could not populate the greetings table because the file "{}" was not found.'.format(filename))

def populate_yomama():
      populate_quotes(
        filename=os.path.join(os.getcwd(), 'yomama.txt'),
        category='yomama'
      )

def populate_fortune():
    populate_quotes(
        filename=os.path.join(os.getcwd(), 'fortunes.txt'),
        category='fortunes'
    )

def populate_dad():
    populate_quotes(
        filename=os.path.join(os.getcwd(), 'dad.txt'),
        category='dad'
    )

logger = configure_logger()
confdir = os.path.join( os.path.expanduser('~'), '.swagbot' )
database = os.path.join(confdir, 'swagbot.plugins.quotes.db')

result = get_input(
    text='This will completely destroy any existing swagbot quote database in "{}". Are you sure you want to do this?'.format(confdir),
    default='no'
)
if result == 'yes':
    #make_confdir()
    conn = sqlite3.connect(database, check_same_thread=False)
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    create_schema()
    populate_yomama()
    populate_fortune()
    populate_dad()
    logger.info('The database setup is complete.')
else:
    print('Aborting.')
