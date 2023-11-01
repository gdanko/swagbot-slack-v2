import base64
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
        with conn:
            cursor = conn.cursor()
            cursor.execute(update, (module, name, interval, encoded_data, enabled, job['id']))
            conn.commit()
    else:
        insert = f'INSERT OR REPLACE INTO scheduler (module, name, interval, function, enabled) VALUES (?, ?, ?, ?, ?)'
        with conn:
            cursor = conn.cursor()
            cursor.execute(insert, (module, name, interval, encoded_data, enabled))
            conn.commit()

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
    with conn:
        cursor = conn.cursor()
        res = cursor.execute(select)
        for row in res:
                output.append(row)
        return output

def delete_job(module=None, name=None):
    delete = f'DELETE FROM scheduler WHERE module=? AND name=?'
    cursor.execute(delete, (module, name))
    conn.commit()

def delete_job_by_id(id=None):
    delete = f'DELETE FROM scheduler WHERE id=?'
    cursor.execute(delete, (id))
    conn.commit()

def enable_job(module=None, name=None):
    delete = f'UPDATE scheduler SET enabled=1 WHERE module=? AND name=?'
    cursor.execute(delete, (module, name))
    conn.commit()

def enable_job_by_id(id=None):
    delete = f'UPDATE scheduler SET enabled=1 WHERE id=?'
    cursor.execute(delete, (id))
    conn.commit()

def disable_job(module=None, name=None):
    update = f'UPDATE scheduler SET enabled=0 WHERE module="{module}" AND name="{name}"'
    cursor.execute(update)
    conn.commit()

def disable_job_by_id(id=None):
    update = f'UPDATE scheduler SET enabled=0 WHERE id=?'
    cursor.execute(update, (id))
    conn.commit()

def get_all_jobs():
    output = []
    select = 'SELECT * FROM scheduler'
    res = cursor.execute(select)
    for row in res:
            row['enabled'] = True if row['enabled'] else False
            output.append(row)
    return output

def get_jobs_by_module(module=None):
    output = []
    select = f'SELECT * FROM scheduler WHERE module="{module}"'
    res = cursor.execute(select)
    for row in res:
            row['enabled'] = True if row['enabled'] else False
            output.append(row)
    return output

def get_job_by_module_and_name(module=None, name=None):
    select = f'SELECT * FROM scheduler WHERE module="{module}" AND name="{name}"'
    cursor.execute(select)
    result = cursor.fetchone()
    if result:
        return result
    else:
        return False

def get_job_by_id(id=None):
    select = f'SELECT * FROM scheduler WHERE id={id}'
    cursor.execute(select)
    result = cursor.fetchone()
    if result:
        return result
    else:
        return False

def delete_jobs_for_module(module=None):
    delete = f'DELETE FROM scheduler WHERE module="{module}"'
    try:
        cursor.execute(delete)
        conn.commit()
    except Exception as e:
        return False

    delete = f'DELETE FROM scheduler_channels WHERE module="{module}"'
    try:
        cursor.execute(delete)
        conn.commit()
        return True
    except Exception as e:
        return False

config_root = os.path.join(os.path.expanduser('~'), '.swagbot')
dbfile = os.path.join(config_root, 'bot.db')
conn = sqlite3.connect(dbfile, check_same_thread=False)
conn.row_factory = utils.dict_factory
cursor = conn.cursor()
