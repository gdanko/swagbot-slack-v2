import base64
import logging
import os
import sqlite3
import swagbot.utils.core as utils
from pprint import pprint
import dill

def add_job(module=None, name=None, interval=None, function=None, enabled=None):
    encoded_data = base64.b64encode(dill.dumps(function))
    job = get_job_by_module_and_name(module=module, name=name)
    if job:
        update = f'UPDATE scheduler SET module=?, name=?, interval=?, function=?, enabled=? WHERE id=?'
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(update, (module, name, interval, encoded_data, enabled, job['id']))
                conn.commit()
        except Exception as e:
            logging.error(f'Failed to execute {update}: {e}')
            return False
    else:
        insert = f'INSERT OR REPLACE INTO scheduler (module, name, interval, function, enabled) VALUES (?, ?, ?, ?, ?)'
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(insert, (module, name, interval, encoded_data, enabled))
                conn.commit()
        except Exception as e:
            logging.error(f'Failed to execute {insert}: {e}')
            return False

def get_jobs(module=None, name=None):
    output = []
    where = []
    where_str = ''
    if module:
        where.append(
            f'module="{module}"'
        )
    if name:
        where.append(
            f'name="{name}"'
        )
    if len(where) > 0:
        where_str = 'WHERE ' + ' AND '.join(where)
    
    select = f'SELECT id, module, name, interval, enabled FROM scheduler {where_str}'
    try:
        with conn:
            cursor = conn.cursor()
            results = cursor.execute(select)
            for row in results:
                    output.append(row)
            return output
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

def delete_job(module=None, name=None):
    delete = f'DELETE FROM scheduler WHERE module="{module} AND name="{name}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(delete)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {delete}: {e}')
        return False

def delete_job_by_id(id=None):
    delete = f'DELETE FROM scheduler WHERE id={id}'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(delete)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {delete}: {e}')
        return False

def enable_job(module=None, name=None):
    delete = f'UPDATE scheduler SET enabled=1 WHERE module="{module} AND name="{name}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(delete)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {delete}: {e}')
        return False        

def enable_job_by_id(id=None):
    delete = f'UPDATE scheduler SET enabled=1 WHERE id={id}'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(delete, (id))
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {delete}: {e}')
        return False  

def disable_job(module=None, name=None):
    update = f'UPDATE scheduler SET enabled=0 WHERE module="{module}" AND name="{name}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(update)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {update}: {e}')
        return False  

def disable_job_by_id(id=None):
    update = f'UPDATE scheduler SET enabled=0 WHERE id={id}'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(update, (id))
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {update}: {e}')
        return False  

def get_all_jobs():
    output = []
    select = 'SELECT * FROM scheduler'
    try:
        with conn:
            cursor = conn.cursor()
            results = cursor.execute(select)
            for row in results:
                    row['enabled'] = True if row['enabled'] else False
                    output.append(row)
            return output
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return output 

def get_jobs_by_module(module=None):
    output = []
    select = f'SELECT * FROM scheduler WHERE module="{module}"'
    try:
        with conn:
            cursor = conn.cursor()
            results = cursor.execute(select)
            for row in results:
                row['enabled'] = True if row['enabled'] else False
                output.append(row)
            return output
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return output 

def get_job_by_module_and_name(module=None, name=None):
    select = f'SELECT * FROM scheduler WHERE module="{module}" AND name="{name}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            results = cursor.fetchone()
            return results if results else False
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False 

def get_job_by_id(id=None):
    select = f'SELECT * FROM scheduler WHERE id={id}'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            results = cursor.fetchone()
            return results if results else False
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False 

def delete_jobs_for_module(module=None):
    delete = f'DELETE FROM scheduler WHERE module="{module}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(delete)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {delete}: {e}')
        return False 

config_root = os.path.join(os.path.expanduser('~'), '.swagbot')
dbfile = os.path.join(config_root, 'bot.db')
conn = sqlite3.connect(dbfile, check_same_thread=False)
conn.row_factory = utils.dict_factory
cursor = conn.cursor()
