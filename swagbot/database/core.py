from pprint import pprint
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
        cursor.execute(select)
        count = len(cursor.fetchall())

        if count <= 0:
            insert = 'INSERT OR REPLACE INTO commands (command,description,usage,is_admin,can_be_disabled,module,method,type,monospace,split_output) VALUES (?,?,?,?,?,?,?,?,?,?)'
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
    res = cursor.execute(select)
    conn.commit()
    for row in res:
        commands.append(row['command'])
    return commands

def help2(is_admin=None):
    where = ''
    if is_admin == 0:
        where = 'WHERE is_admin=0'
    commands = []
    select = f'SELECT commands.*, command_settings.* FROM commands JOIN command_settings ON commands.command=command_settings.command AND command_settings.enabled=1 AND command_settings.hidden=0 {where} ORDER BY command'
    res = cursor.execute(select)
    conn.commit()
    for row in res:
        commands.append(row)
    return commands

def usage(command=None):
    select = f'SELECT usage FROM commands WHERE command="{command}"'
    cursor.execute(select)
    result = cursor.fetchone()
    return result['usage'] if result else None

def all_commands():
    commands = []
    select = 'SELECT command FROM commands'
    res = cursor.execute(select)
    conn.commit()
    for row in res:
        commands.append(row['command'])
    return commands

def command_lookup(command=None):
    select = f"SELECT commands.command, commands.description, commands.usage, commands.is_admin, commands.can_be_disabled, commands.module, commands.method, commands.type, commands.monospace, commands.split_output, command_settings.enabled, command_settings.hidden FROM commands JOIN command_settings ON commands.command = command_settings.command WHERE commands.command='{command}'"
    cursor.execute(select)
    result = cursor.fetchone()
    if result:
        result['can_be_disabled'] = True if ('can_be_disabled' in result and result['can_be_disabled'] == 1) else False
        result['enabled'] = True if ('enabled' in result and result['enabled'] == 1) else False
        result['hidden'] = True if ('hidden' in result and result['hidden'] == 1) else False
        result['monospace'] = True if ('monospace' in result and result['monospace'] == 1) else False
        result['split_output'] = True if ('split_output' in result and result['split_output'] == 1) else False
        return result
    else:
        return False

def prune_commands_table(commands=None):
    delete = f'DELETE FROM commands WHERE command IN ({utils.quote_list(commands)})'
    cursor.execute(delete)
    conn.commit()

def hide_command(command=None):
    update = f'UPDATE command_settings SET hidden=1 WHERE command="{command}"'
    cursor.execute(update)
    conn.commit()

def unhide_command(command=None):
    update = f'UPDATE command_settings SET hidden=0 WHERE command="{command}"'
    cursor.execute(update)
    conn.commit()

def enable_command(command=None):
    update = f'UPDATE command_settings SET enabled=1 WHERE command="{command}"'
    cursor.execute(update)
    conn.commit()

def disable_command(command=None):
    update = f'UPDATE command_settings SET enabled=0 WHERE command="{command}"'
    cursor.execute(update)
    conn.commit()

# Users
def get_user_by_id(id=None):
    select = f'SELECT * FROM users WHERE id="{id}"'
    cursor.execute(select)
    result = cursor.fetchone()
    if result:
        return result
    else:
        return False

def get_user_by_name(name=None):
    select = f'SELECT * FROM users WHERE name="{name}"'
    cursor.execute(select)
    result = cursor.fetchone()
    if result:
        return result
    else:
        return False

# Channels
def get_channel_by_name(name=None):
    select = f'SELECT * FROM channels WHERE name="{name}"'
    cursor.execute(select)
    result = cursor.fetchone()
    if result:
        return result
    else:
        return False

# Errors
def get_slack_api_errors(method=None, error=None):
    select = f'SELECT * FROM slack_errors WHERE method="{method}" and error="{error}"'
    cursor.execute(select)
    result = cursor.fetchone()
    if result:
        return result
    else:
        return False

# Modules
def module_list():
    output = []
    select = f'SELECT * FROM modules ORDER BY enabled, module'
    res = cursor.execute(select)
    for row in res:
            output.append(row)
    return output

def get_module(module=None):
    select = f'SELECT * FROM modules WHERE module="{module}"'
    cursor.execute(select)
    result = cursor.fetchone()
    return result if result else False

def moduleadd(module=None):
    insert = 'INSERT INTO modules (module,enabled,can_be_disabled) VALUES (?,?,?)'
    cursor.execute(insert, (module, 0, 1))
    conn.commit()

def enable_module(module=None):
    update = f'UPDATE modules SET enabled=1 WHERE module="{module}"'
    cursor.execute(update)
    conn.commit()

def disable_module(module=None):
    update = f'UPDATE modules SET enabled=0 WHERE module="{module}"'
    cursor.execute(update)
    conn.commit()

def module_commands(module=None):
    commands = []
    select = f'SELECT command FROM commands WHERE module="{module}"'
    res = cursor.execute(select)
    for row in res:
        commands.append(row['command'])
    return commands

# Admin grant/revoke
def admin_list():
    output = []
    select = f'SELECT * FROM admins'
    res = cursor.execute(select)
    for row in res:
            output.append(row)
    return output

def get_admin_by_name(name=None):
    select = f'SELECT * FROM admins WHERE name="{name}"'
    cursor.execute(select)
    result = cursor.fetchone()
    if result:
        return result
    else:
        return False

def get_admin_by_id(id=None):
    select = f'SELECT * FROM admins WHERE id="{id}"'
    cursor.execute(select)
    result = cursor.fetchone()
    if result:
        return result
    else:
        return False

def admin_grant(id=None, name=None, real_name=None, email=None):
    insert = 'INSERT OR REPLACE INTO admins (id, name, real_name) VALUES (?, ?, ?)'
    cursor.execute(insert, (
        id,
        name,
        real_name,
    ))
    conn.commit()

def admin_revoke(name=None):
    delete = f'DELETE FROM admins WHERE name="{name}"'
    cursor.execute(delete)
    conn.commit()

# Miscellaneous
def update_seen(userid=None, username=None, channel=None):
    insert = 'INSERT OR REPLACE INTO seen (id, name, seen_time, seen_channel) VALUES (?, ?, ?, ?)'
    cursor.execute(insert, (
        userid,
        username,
        utils.now(),
        channel,
    ))
    conn.commit()

def get_seen(username=None):
    select = f'SELECT * FROM seen WHERE name="{username}"'
    cursor.execute(select)
    result = cursor.fetchone()
    if result:
        return result
    else:
        return False

def greeting(language=None):
    table = 'greetings'
    if language == None:
        select = f'SELECT * FROM {table} ORDER BY RANDOM() LIMIT 1 COLLATE NOCASE'
    else:
        select = f'SELECT * FROM {table} WHERE language="{language}" COLLATE NOCASE'

    res = cursor.execute(select)
    for row in res:
        return row

def curse_lookup(username=None):
    table = 'curses'
    select = f'SELECT * FROM {table} where username="{username}" LIMIT 1'

    res = cursor.execute(select)
    for row in res:
        return row

config_root = os.path.join(os.path.expanduser('~'), '.swagbot')
dbfile = os.path.join(config_root, 'bot.db')
conn = sqlite3.connect(dbfile, check_same_thread=False)
conn.row_factory = utils.dict_factory
cursor = conn.cursor()
