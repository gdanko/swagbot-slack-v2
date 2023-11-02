from pprint import pprint
import logging
import os
import sqlite3
import swagbot.utils.core as utils

def update_plugin_commands(module=None, methods=None):
    for command_name, command_settings in methods.items():
        method = command_settings['method'] if 'method' in command_settings else command_name
        monospace = command_settings['monospace'] if 'monospace' in command_settings else 0
        hidden = command_settings['hidden'] if 'hidden' in command_settings else 0
        split_output = command_settings['split_output'] if 'split_output' in command_settings else 0

        select = f'SELECT * FROM commands WHERE command="{command_name}"'
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            count = len(cursor.fetchall())

        if count <= 0:
            insert = 'INSERT OR REPLACE INTO commands (command,description,usage,is_admin,can_be_disabled,module,method,type,monospace,split_output) VALUES (?,?,?,?,?,?,?,?,?,?)'
            with conn:
                cursor = conn.cursor()
                cursor.execute(insert, (
                    command_name,
                    command_settings['description'],
                    command_settings['usage'],
                    command_settings['is_admin'],
                    command_settings['can_be_disabled'],
                    module,
                    method,
                    command_settings['type'],
                    monospace,
                    split_output,
                ))
                conn.commit()
        else:
            update = f'UPDATE commands SET description=?,usage=?,is_admin=?,can_be_disabled=?,module=?,method=?,type=?,monospace=?,split_output=? WHERE command="{command_name}"'
            with conn:
                cursor = conn.cursor()
                cursor.execute(update, (
                    command_settings['description'],
                    command_settings['usage'],
                    command_settings['is_admin'],
                    command_settings['can_be_disabled'],
                    module,
                    method,
                    command_settings['type'],
                    monospace,
                    split_output,
                ))
                conn.commit()

        select = f'SELECT * FROM command_settings WHERE command="{command_name}"'
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            count = len(cursor.fetchall())

            if count <= 0:
                insert = 'INSERT OR REPLACE INTO command_settings (command,module,enabled,hidden) VALUES (?,?,?,?)'
                cursor.execute(insert, (
                    command_name,
                    module,
                    1,
                    hidden
                ))
                conn.commit()

# Help and commands
def help(is_admin=None):
    where = ''
    if is_admin == 0:
        where = 'WHERE is_admin=0'
    commands = []
    select = f'SELECT commands.*, command_settings.* FROM commands JOIN command_settings ON commands.command=command_settings.command AND command_settings.enabled=1 AND command_settings.hidden=0 {where} ORDER BY command'
    try:
        with conn:
            cursor = conn.cursor()
            results = cursor.execute(select)
            conn.commit()
            for row in results:
                commands.append(row)
            return commands
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return None

def usage(command=None):
    select = f'SELECT usage FROM commands WHERE command="{command}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            results = cursor.fetchone()
            return results['usage'] if results else None
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return None

def all_commands():
    commands = []
    select = 'SELECT command FROM commands'
    try:
        with conn:
            cursor = conn.cursor()
            results = cursor.execute(select)
            conn.commit()
            for row in results:
                commands.append(row['command'])
            return commands
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return commands

def command_lookup(command=None):
    select = f"SELECT commands.command, commands.description, commands.usage, commands.is_admin, commands.can_be_disabled, commands.module, commands.method, commands.type, commands.monospace, commands.split_output, command_settings.enabled, command_settings.hidden FROM commands JOIN command_settings ON commands.command = command_settings.command WHERE commands.command='{command}'"
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            results = cursor.fetchone()
            if results:
                results['can_be_disabled'] = True if ('can_be_disabled' in results and results['can_be_disabled'] == 1) else False
                results['enabled'] = True if ('enabled' in results and results['enabled'] == 1) else False
                results['hidden'] = True if ('hidden' in results and results['hidden'] == 1) else False
                results['monospace'] = True if ('monospace' in results and results['monospace'] == 1) else False
                results['split_output'] = True if ('split_output' in results and results['split_output'] == 1) else False
                return results
            else:
                return False
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

def prune_commands_table(commands=None):
    delete = f'DELETE FROM commands WHERE command IN ({utils.quote_list(commands)})'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(delete)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {delete}: {e}')
        return False

def hide_command(command=None):
    update = f'UPDATE command_settings SET hidden=1 WHERE command="{command}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(update)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {update} {e}')
        return False

def unhide_command(command=None):
    update = f'UPDATE command_settings SET hidden=0 WHERE command="{command}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(update)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {update} {e}')
        return False

def enable_command(command=None):
    update = f'UPDATE command_settings SET enabled=1 WHERE command="{command}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(update)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {update} {e}')
        return False

def disable_command(command=None):
    update = f'UPDATE command_settings SET enabled=0 WHERE command="{command}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(update)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {update} {e}')
        return False

# Users
def get_user_by_id(id=None):
    select = f'SELECT * FROM users WHERE id="{id}"'
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

def get_user_by_name(name=None):
    select = f'SELECT * FROM users WHERE name="{name}"'
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

# Channels
def get_channel_by_name(name=None):
    try:
        select = f'SELECT * FROM channels WHERE name="{name}"'
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

# Errors
def get_slack_api_errors(method=None, error=None):
    select = f'SELECT * FROM slack_errors WHERE method="{method}" and error="{error}"'
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
    
# Modules
def module_list():
    output = []
    select = f'SELECT * FROM modules ORDER BY enabled, module'
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

def get_module(module=None):
    select = f'SELECT * FROM modules WHERE module="{module}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            results = cursor.fetchone()
            return results if results else False
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

def moduleadd(module=None, enabled=False):
    insert = f'INSERT INTO modules (module,enabled,can_be_disabled) VALUES ("{module}", {enabled}, 1)'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(insert)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {insert}: {e}')
        return False

def enable_module(module=None):
    update = f'UPDATE modules SET enabled=1 WHERE module="{module}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(update)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {update} {e}')
        return False

def disable_module(module=None):
    update = f'UPDATE modules SET enabled=0 WHERE module="{module}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(update)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {update} {e}')
        return False

def module_commands(module=None):
    commands = []
    select = f'SELECT command FROM commands WHERE module="{module}"'
    try:
        with conn:
            cursor = conn.cursor()
            results = cursor.execute(select)
            for row in results:
                commands.append(row['command'])
            return commands
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

def module_exists(module=None):
    select = f'SELECT * FROM modules WHERE module="{module}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            results = cursor.fetchone()
            return True if results else False
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

def module_is_enabled(module=None):
    select = f'SELECT enabled FROM modules WHERE module="{module}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(select)
            results = cursor.fetchone()
            return True if results['enabled'] == 1 else False
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

# Admin grant/revoke
def admin_list():
    output = []
    select = f'SELECT * FROM admins'
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

def get_admin_by_name(name=None):
    select = f'SELECT * FROM admins WHERE name="{name}"'
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

def get_admin_by_id(id=None):
    select = f'SELECT * FROM admins WHERE id="{id}"'
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

def admin_grant(id=None, name=None, real_name=None, email=None):
    insert = f'INSERT OR REPLACE INTO admins (id, name, real_name) VALUES ("{id}", "{name}", "{real_name}")'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(insert)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {insert}: {e}')
        return False

def admin_revoke(name=None):
    delete = f'DELETE FROM admins WHERE name="{name}"'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(delete)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {delete}: {e}')
        return False

# Miscellaneous
def update_seen(userid=None, username=None, channel=None):
    insert = f'INSERT OR REPLACE INTO seen (id, name, seen_time, seen_channel) VALUES ("{userid}", "{username}", {utils.now()}, "{channel}")'
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(insert)
            conn.commit()
    except Exception as e:
        logging.error(f'Failed to execute {insert}: {e}')
        return False

def get_seen(username=None):
    select = f'SELECT * FROM seen WHERE name="{username}"'
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

def greeting(language=None):
    table = 'greetings'
    if language == None:
        select = f'SELECT * FROM {table} ORDER BY RANDOM() LIMIT 1 COLLATE NOCASE'
    else:
        select = f'SELECT * FROM {table} WHERE language="{language}" COLLATE NOCASE'
    # fetchone!
    try:
        with conn:
            cursor = conn.cursor()
            results = cursor.execute(select)
            for row in results:
                return row
    except Exception as e:
        logging.error(f'Failed to execute {select}: {e}')
        return False

def curse_lookup(username=None):
    table = 'curses'
    select = f'SELECT * FROM {table} where username="{username}" LIMIT 1'
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
dbfile = os.path.join(config_root, 'bot.db')
conn = sqlite3.connect(dbfile, check_same_thread=False)
conn.row_factory = utils.dict_factory
cursor = conn.cursor()
