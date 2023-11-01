import logging
import os
import sqlite3
import swagbot.utils.core as utils

def validate_schema():
    tables = ['escalation_policies', 'schedules', 'services', 'oncall_temp', 'users']
    for table_name in tables:
        select = f'SELECT name FROM sqlite_master WHERE type="table" AND name="{table_name}"'
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            result = cursor.fetchone()
            if not result:
                return False
    return True

def create_schema():
    logging.info('Creating the PagerDuty database.')
    for table_name in ['escalation_policies', 'schedules', 'services', 'users']:
        create = f'CREATE TABLE {table_name} (id TEXT NOT NULL PRIMARY KEY, name TEXT NOT NULL)'
        with conn:
            try:
                cursor = conn.cursor()
                cursor.execute(create)
            except:
                return False

    create = f'CREATE TABLE oncall_temp(escalation_policy TEXT NOT NULL, name TEXT NOT NULL, level INTEGER NOT NULL)'
    with conn:
        try:
            cursor = conn.cursor()
            cursor.execute(create)
        except:
            return False

def add(table_name=None, id=None, name=None):
    try:
        insert = f'INSERT INTO {table_name} (id, name) VALUES (?, ?)'
        with conn:
            cursor = conn.cursor()
            cursor.execute(insert, (id, name))
            conn.commit()
            return True
    except Exception as e:
        # logging.error(f'Failed to add the item {id} to the table {table_name}: {e}')
        return False

def add_user(id=None, name=None, email=None, role=None):
    try:
        insert = f'INSERT INTO users (id, name, email, role) VALUES (?, ?, ?, ?)'
        with conn:
            cursor = conn.cursor()
            cursor.execute(insert, (id, name, email, role))
            conn.commit()
            return True
    except Exception as e:
        # logging.error(f'Failed to add the user {id}: {e}')
        return False

def list(table_name=None, pattern=None):
    where = ''
    if pattern:
        where = f'WHERE name LIKE("{pattern}")'
    output = []
    try:
        select = f'SELECT * FROM {table_name} {where}'
        with conn:
            cursor = conn.cursor()
            res = cursor.execute(select)
            for row in res:
                output.append(row)
            return output
    except:
        return

def wipe_oncall_temp():
    try:
        delete = 'DELETE FROM oncall_temp'
        cursor.execute(delete)
        conn.commit()
        return True
    except Exception as e:
        return False

def add_oncall_temp(summary=None, level=None, name=None):
    try:
        insert = f'INSERT INTO oncall_temp (escalation_policy, level, name) VALUES (?, ?, ?)'
        with conn:
            cursor = conn.cursor()
            cursor.execute(insert, (summary, level, name))
            conn.commit()
            return True
    except Exception as e:
        logging.error(e)
        return False

def get_oncall_temp(min=1, max=1000):
    try:
        output = []
        select = f'SELECT * FROM oncall_temp WHERE level>={min} AND level<={max} ORDER BY escalation_policy, level'
        with conn:
            cursor = conn.cursor()
            res = cursor.execute(select)
            for row in res:
                    output.append(row)
            return output
    except Exception as e:
        logging.error(e)
        return False

config_root = os.path.join(os.path.expanduser('~'), '.swagbot')
dbfile = os.path.join(config_root, 'swagbot.plugins.pagerduty.db')
conn = sqlite3.connect(dbfile, check_same_thread=False)
conn.row_factory = utils.dict_factory
cursor = conn.cursor()
