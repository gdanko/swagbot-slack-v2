#!/usr/bin/env python3

from pprint import pprint
import csv
import logging
import os
import re
import sqlite3
import sys
import time

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

def parse_csv(filename):
    output = []
    with open(filename, newline='') as fh:
        reader = csv.reader(fh, delimiter=',', quotechar='"')
        for row in reader:
            output.append(row)
    return output

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

def create_schema():
    logger.info('Creating the database schema.')
    config = {
        'tables': {
            'currency_conversion': {
                'columns': {
                    'currency_code': { 'type': 'text', 'null': False, 'unique': True },
                    'currency_name': { 'type': 'text', 'null': False, 'unique': False }
                }
            },
            'crypto_conversion': {
                'columns': {
                    'currency_code': { 'type': 'text', 'null': False, 'unique': True },
                    'currency_name': { 'type': 'text', 'null': False, 'unique': False }
                }
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

def populate_currency(table_name=None, filename=None):
    filename = os.path.join(os.getcwd(), filename)
    currency_data = parse_csv(filename)

    confdir = os.path.join( os.path.expanduser('~'), '.swagbot' )
    database = os.path.join(confdir, 'bot.db')
    conn = sqlite3.connect(database, check_same_thread=False)
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    for row in currency_data:
        insert = f'INSERT INTO {table_name} (currency_code, currency_name) VALUES(?,?)'
        print(insert)
        pprint(row)
        # exit()
        cursor.execute(insert, (
            row[0],
            row[1],
        ))
        conn.commit()

def populate_physical_currency():
      populate_currency(
        table_name = 'currency_conversion',
        filename=os.path.join(os.getcwd(), 'physical_currency_list.csv'),
      )

def populate_crypto_currency():
    populate_currency(
        table_name = 'crypto_conversion',
        filename=os.path.join(os.getcwd(), 'digital_currency_list.csv'),
    )

logger = configure_logger()
confdir = os.path.join( os.path.expanduser('~'), '.swagbot' )
database = os.path.join(confdir, 'swagbot.plugins.extras.db')

result = get_input(
    text='This will completely destroy any existing swagbot.plugins.extras database in "{}". Are you sure you want to do this?'.format(confdir),
    default='no'
)

if result == 'yes':
    conn = sqlite3.connect(database, check_same_thread=False)
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    # create_schema()
    populate_physical_currency()
    populate_crypto_currency()
    logger.info('The database setup is complete.')
else:
    print('Aborting.')
