from pprint import pprint
import logging
import os
import sqlite3
import swagbot.globals as globals
import swagbot.utils.core as utils

def update_channels(channels=None):
    logging.info('Populating the channels table.')
    now = utils.now()
    for c in channels:
        is_channel = 1 if c['is_channel'] == True else 0
        is_group = 1 if c['is_group'] == True else 0
        is_im = 1 if c['is_im'] == True else 0
        is_private = 1 if c['is_private'] == True else 0
        is_mpim = 1 if c['is_mpim'] == True else 0
        insert = f'INSERT OR REPLACE INTO channels (id, name, is_channel, is_group, is_im, is_private, is_mpim, created, creator, name_normalized, updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(insert, (c['id'], c['name'], is_channel, is_group, is_im, is_private, is_mpim, c['created'], c['creator'], c['name_normalized'], now))
                conn.commit()
        except Exception as e:
            logging.error(f'Failed to execute {insert}: {e}')
            return False

def get_channel_by_name(name=None):
    select = f'SELECT * FROM channels WHERE name="{name}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            results = cursor.fetchone()
            if results:
                return results
            else:
                return False
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

def update_users(users=None):
    logging.info('Populating the users table.')
    now = utils.now()
    for u in users:
        real_name = u['real_name'] if 'real_name' in u else 'Unknown'
        is_bot = 1 if u['is_bot'] == True else 0
        is_app_user = 1 if u['is_app_user'] == True else 0
        email = u['profile']['email'] if ('profile' in u and 'email' in u['profile']) else 'unknown'
        insert = f'INSERT OR REPLACE INTO users (id, name, real_name, email, is_bot, is_app_user, updated) VALUES (?, ?, ?, ?, ?, ?, ?)'
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(insert, (u['id'], u['name'], real_name, email.lower(), is_bot, is_app_user, now))
                conn.commit()
        except Exception as e:
            logging.error(f'Failed to execute {insert}: {e}')
            return False

def row_count(table=None):
    select = f'SELECT * FROM "{table}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            return len(cursor.fetchall())
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

def check_freshness(table=None):
    select = f'SELECT MIN(updated) AS updated FROM "{table}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            results = cursor.fetchone()
            if results:
                return results['updated'] if results['updated'] else 0
            else:
                return 0
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return 0

config_root = os.path.join(os.path.expanduser('~'), '.swagbot')
dbfile = os.path.join(config_root, 'bot.db')
conn = sqlite3.connect(dbfile, check_same_thread=False)
conn.row_factory = utils.dict_factory
cursor = conn.cursor()
