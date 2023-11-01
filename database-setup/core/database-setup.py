#!/usr/bin/env python3

# from base64 import b64encode, b64decode
# from Crypto.Cipher import PKCS1_OAEP
# from Crypto.PublicKey import RSA
from pprint import pprint
import csv
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

# def rsa_encrypt(message):	
#     message = message.encode('utf-8')
#     key = RSA.importKey(open(pubkey).read())
#     cipher = PKCS1_OAEP.new(key)
#     ciphertext = cipher.encrypt(message)
#     return b64encode(ciphertext).decode('utf-8')

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
            'afk': {
                'columns': {
                    'username': { 'type': 'text', 'null': False, 'primary_key': False },
                    'message': { 'type': 'text', 'null': False, 'primary_key': False },
                    'timestamp': { 'type': 'integer', 'null': False, 'primary_key': False },
                }
            },
            'command_settings': {
                'columns': {
                    'command': { 'type': 'text', 'null': False, 'primary_key': True },
                    'module': { 'type': 'text', 'null': False, 'primary_key': False },
                    'enabled': { 'type': 'integer', 'null': False, 'primary_key': False, 'default': 1 },
                    'hidden': { 'type': 'integer', 'null': False, 'primary_key': False, 'default': 0 },
                    'channels': { 'type': 'integer', 'null': True, 'primary_key': False },
                }
            },
            'commands': {
                'columns': {
                    'command': { 'type': 'text', 'null': False, 'primary_key': True },
                    'usage': { 'type': 'text', 'null': False, 'primary_key': False },
                    'is_admin': { 'type': 'integer', 'null': False, 'primary_key': False, 'default': 0 },
                    'can_be_disabled': { 'type': 'integer', 'null': False, 'primary_key': False, 'default': 1 },
                    'module': { 'type': 'text', 'null': False, 'primary_key': False },
                    'method': { 'type': 'text', 'null': False, 'primary_key': False },
                    'type': { 'type': 'text', 'null': False, 'primary_key': False },
                    'monospace': { 'type': 'integer', 'null': False, 'primary_key': False, 'default': 0 },
                    'split_output': { 'type': 'integer', 'null': False, 'primary_key': False, 'default': 0 },
                }
            },
            'curses': {
                'columns': {
                    'username': { 'type': 'text', 'null': False, 'primary_key': False },
                    'curses_count': { 'type': 'integer', 'null': False, 'primary_key': False },
                    'last_curse_time': { 'type': 'integer', 'null': False, 'primary_key': False },
                    'last_curse_word': { 'type': 'text', 'null': False, 'primary_key': False },
                    'last_curse_channel': { 'type': 'text', 'null': False, 'primary_key': False },
                }
            },
            'curse_words': {
                'columns': {
                    'word': { 'type': 'text', 'null': False, 'unique': True },
                }
            },
            'modules': {
                'columns': {
                    'module': { 'type': 'text', 'null': False, 'primary_key': False },
                    'enabled': { 'type': 'integer', 'null': False, 'primary_key': False, 'default': 1 },
                    'can_be_disabled': { 'type': 'integer', 'null': False, 'primary_key': False, 'default': 0 },
                },
            },
            'greetings': {
                'columns': {
                    'language': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': True },
                    'greeting': { 'type': 'text', 'null': False, 'unique': False, 'primary_key': False },
                },
            },
            'seen': {
                'columns': {
                    'username': { 'type': 'text', 'null': False, 'primary_key': False },
                    'userid': { 'type': 'text', 'null': False, 'primary_key': False },
                    'time': { 'type': 'integer', 'null': False, 'primary_key': False },
                    'channel': { 'type': 'text', 'null': False, 'primary_key': False },
                },
            },
            # 'timers': {
            #     'columns': {
            #         'title': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': False },
            #         'description': { 'type': 'text', 'null': False, 'primary_key': False },
            #         'expires': { 'type': 'integer', 'null': False, 'primary_key': False },
            #         'expired': { 'type': 'integer', 'null': False, 'primary_key': False },
            #     }
            # },
            'users': {
                'columns': {
                    'id': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': True },
                    'name': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': False },
                    'real_name': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': False },
                    'email': { 'type': 'text', 'null': True, 'unique': True, 'primary_key': False },
                    'is_bot': { 'type': 'integer', 'null': True, 'unique': False, 'primary_key': False },
                    'is_app_user': { 'type': 'integer', 'null': True, 'unique': False, 'primary_key': False },
                    'deleted': { 'type': 'integer', 'null': True, 'primary_key': False, 'default': 0 },
                    'updated': { 'type': 'integer', 'null': True, 'primary_key': False, 'default': 0 },
                },
            },
            'admins': {
                'columns': {
                    'id': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': True },
                    'name': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': False },
                    'real_name': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': False },
                },
            },
            'seen': {
                'columns': {
                    'id': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': True },
                    'name': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': False },
                    'seen_time': { 'type': 'integer', 'null': True, 'primary_key': False, 'default': 0 },
                    'seen_channel': { 'type': 'text', 'null': True, 'primary_key': False },
                },
            },
            'channels': {
                'columns': {
                    'id': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': True },
                    'name': { 'type': 'text', 'null': False, 'unique': True, 'primary_key': False },
                    'is_channel': { 'type': 'integer', 'null': True, 'unique': False, 'primary_key': False, 'default': 0 },
                    'is_group': { 'type': 'integer', 'null': True, 'unique': False, 'primary_key': False, 'default': 0 },
                    'is_im': { 'type': 'integer', 'null': True, 'unique': False, 'primary_key': False, 'default': 0 },
                    'is_private': { 'type': 'integer', 'null': True, 'unique': False, 'primary_key': False, 'default': 0 },
                    'is_mpim': { 'type': 'integer', 'null': True, 'unique': False, 'primary_key': False, 'default': 0 },
                    'created': { 'type': 'integer', 'null': True, 'unique': False, 'primary_key': False, 'default': 0 },
                    'creator': { 'type': 'text', 'null': True, 'unique': False, 'primary_key': False },
                    'updated': { 'type': 'integer', 'null': True, 'unique': False, 'primary_key': False, 'default': 0 },
                    'name_normalized': { 'type': 'text', 'null': True, 'unique': False, 'primary_key': False },
                }
            },
            'slack_errors': {
                'columns': {
                    'method': { 'type': 'text', 'null': False, 'unique': False, 'primary_key': False },
                    'error': { 'type': 'text', 'null': False, 'unique': False, 'primary_key': False },
                    'bot_error': { 'type': 'text', 'null': False, 'unique': False, 'primary_key': False },
                },
            },
            # CREATE TABLE scheduler (
            # id INTEGER PRIMARY KEY AUTOINCREMENT,
            # name TEXT NOT NULL,
            # description TEXT,
            # module TEXT NOT NULL,
            # interval INTEGER NOT NULL,
            # function TEXT NOT NULL,
            # enabled INTEGER NOT NULL DEFAULT 1,
            # paused_until INTEGER DEFAULT 0,
            # UNIQUE(name, module) ON CONFLICT FAIL);
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
        'swagbot.plugins.core',
        'swagbot.plugins.maintenance',
        'swagbot.plugins.quotes',
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

def parse_csv(filename):
    output = []
    with open(filename, newline='') as fh:
        reader = csv.reader(fh, delimiter=',', quotechar='"')
        for row in reader:
            output.append(row)
    return output

def populate_slack_errors_table():
    filename = os.path.join(os.getcwd(), 'slack_errors.csv')
    slack_error_data = parse_csv(filename)

    confdir = os.path.join( os.path.expanduser('~'), '.swagbot' )
    database = os.path.join(confdir, 'bot.db')
    conn = sqlite3.connect(database, check_same_thread=False)
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    for row in slack_error_data:
        print(row[0])
        insert = 'INSERT INTO slack_errors (method, error, bot_error) VALUES(?,?,?)'
        cursor.execute(insert, (
            row[0],
            row[1],
            row[2],
        ))
        conn.commit()

logger = configure_logger()
confdir = os.path.join( os.path.expanduser('~'), '.swagbot' )
database = os.path.join(confdir, 'bot.db')

result = get_input(
    text='This will completely destroy any existing swagbot database in "{}". Are you sure you want to do this?'.format(confdir),
    default='no'
)
if result == 'yes':
    #make_confdir()
    conn = sqlite3.connect(database, check_same_thread=False)
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    create_schema()
    enable_core_plugin()
    populate_greetings_table()
    populate_slack_errors_table()
    logger.info('The database setup is complete.')
else:
    print('Aborting.')
