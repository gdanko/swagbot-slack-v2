from datetime import datetime, timedelta, timezone
from dateutil import parser
from shutil import which
from tabulate import tabulate
import importlib
import json
import logging
import pkgutil
import re
import swagbot.database.core as db
import swagbot.exception as exception
import swagbot.globals as globals
import sys
import time
import yaml

from pprint import pprint

def parse_config(path=None):
    contents = open(path, 'r').read()

    if len(contents) <= 0:
        raise exception.InvalidConfigFile(path=path, message='Zero-length file')

    config = validate_yaml(contents)
    if config:
        return config

def validate_json(string):
    if string:
        try:
            hash = json.loads(string)
            return hash
        except:
            return None
    else:
        return None
def validate_yaml(string):
    hash = yaml.safe_load(string)
    if string:
        try:
            hash = yaml.safe_load(string)
            return hash
        except:
            return None
    else:
        return None

def validate_url(url):
    regex = "^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$"
    if re.match(regex, url):
        return True
    return False

def classname(c):
    try:
        module = c.__class__.__module__
        name = c.__class__.__name__
        return '{}.{}'.format(module, name)
    except:
        print('need a "not a class" exception')
        sys.exit(1)

def now():
    return int(time.time())

def duration(seconds):
    seconds = int(seconds)
    days = int(seconds / 86400)
    hours = int(((seconds - (days * 86400)) / 3600))
    minutes = int(((seconds - days * 86400 - hours * 3600) / 60))
    secs = int((seconds - (days * 86400) - (hours * 3600) - (minutes * 60)))

    return days, hours, minutes, secs

def duration_string(timestamp):
    try:
        datetime_oject = parser.parse(timestamp)
    except Exception as e:
        logging.error(f'Failed to convert {timestamp} to a datetime object: {e}')
        return 'Unknown'
    
    try:
        unix_time = time.mktime(datetime_oject.timetuple())
    except Exception as e:
        logging.error(f'Failed to convert {datetime_oject} to a Unix timestamp: {e}')
        return 'Unknown'
    
    try:
        days, hours, minutes, seconds = duration(now() - unix_time)
    except Exception as e:
        logging.error(f'Failed to pass {unix_time} through utils.duration(): {e}')
        return 'Unknown'
    
    output = []

    d = 'days' if days > 1 else 'day'
    if days > 0:
        output.append(f'{days} {d}'.format(days, d))
    output.append('{}:{}:{}'.format(
        str(hours).zfill(2),
        str(minutes).zfill(2),
        str(seconds).zfill(2))
    )
    return ' '.join(output)

def farenheit_to_celsius(temp):
    temp = int(temp)
    c = (((temp - 32) * 5) / 9)
    return int(c)

def celsius_to_farenheit(temp):
    temp = int(temp)
    c = (((temp * 9) / 5) + 32)
    return int(c)

def array_to_chunks(arr, chunk_size):
	for i in range(0, len(arr), chunk_size):
		yield arr[i:i + chunk_size]

def binary_exists(binary):
    return which(binary) is not None

def current_time():
    human_time = datetime.fromtimestamp(now()).strftime('%Y-%m-%d %H:%M:%S')
    return human_time

def ts_to_human(timestamp):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def to_gb(num):
    return int(num / 1024 / 1024 / 1024)

def to_mb(num):
    return int(num / 1024 / 1024 / 1024 / 1024)

def dict_factory(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def quote_list(l):
    return ','.join(['\'{}\''.format(x) for x in l])

def error_ineterpolator(method=None, error=None, replacements={}, quote_replacements=False):
    slack_error = db.get_slack_api_errors(method=method, error=error)
    if slack_error:
        error_template = slack_error['bot_error']
        for key, value in replacements.items():
            placeholder = '{' + key + '}'
            if placeholder in slack_error['bot_error']:
                if quote_replacements:
                    value = '"' + value + '"'
                error_template = error_template.replace(placeholder, value)
        return error_template
    else:
        return False

def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def validate_date(date=None):
    match = re.search('^(\d{4})-(\d{2})-(\d{2})$', date)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        date = int(match.group(3))
        return datetime(year, month, date, 0, 0, 0)
    return False

def to8601(datestamp=None):
    datestamp = datestamp.replace('"', '')
    formatter = '%Y-%m-%d %H:%M:%S'
    delimiter = 'T'
    try:
        current_date_time = datetime.strptime(datestamp, formatter)
    except Exception as e:
        logging.error(f'Failed to generate a datetime object for the datestamp {datestamp}: {e}')
        return False

    try:
        utc_offset = time.localtime().tm_gmtoff / 3600
    except Exception as e:
        logging.error(f'Failed to determine my UTC offset: {e}')
        return False

    try:
        time_delta = timedelta(hours=utc_offset)
    except Exception as e:
        logging.error(f'Failed to generate a time delta: {e}')
        return False

    try:
        tz_object = timezone(time_delta, name='Pacific')
    except Exception as e:
        logging.error(f'Failed to generate a tz object: {e}')
        return False

    try:
        time_now = current_date_time.replace(tzinfo=tz_object)
    except Exception as e:
        logging.error(f'Failed to generate a time_now object: {e}')
        return False

    try:
        return time_now.isoformat(delimiter, 'seconds')
    except Exception as e:
        logging.error(f'Failed to generate an iso8601 timestamp for the datestamp {datestamp}: {e}')
        return False

def generate_table(headers, data):
    return tabulate(
        data,
        headers=headers,
        tablefmt='psql',
        numalign='left',
        disable_numparse=True
    )

def iter_namespace(ns_pkg):
    # Specifying the second argument (prefix) to iter_modules makes the
    # returned name an absolute name instead of a relative one. This allows
    # import_module to work without having to do additional modification to the name.
    return pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + '.')

def prune_commands_table():
    loaded_commands = []
    for _, plugin_obj in globals.plugins.items():
        plugin_instance = plugin_obj['instance']
        if hasattr(plugin_instance, 'methods'):
            loaded_commands += list(plugin_instance.methods.keys())
    loaded_commands = sorted(loaded_commands)

    command_table_commands = db.all_commands()

    to_prune = list(set(command_table_commands) - set(loaded_commands))
    if len(to_prune) > 0:
        command = 'command' if len(to_prune) == 1 else 'commands'
        logging.info(f'Pruning {len(to_prune)} {command} from the commands table.')
        db.prune_commands_table(commands=to_prune)

def load_module(module=None, client=None):
    logging.info(f'Loading module {module}.')
    try:
        module_obj = importlib.import_module(module)
        module_instance = module_obj.Plugin(client=client)
        logging.info(f'Updating bot commands for the module {module}.')
        db.update_plugin_commands(module=module_instance.classname, methods=module_instance.methods)
        globals.plugins[module] = {'module': module, 'instance': module_instance}
        return None
    except Exception as e:
        return e

def reload_module(module=None, client=None):
    logging.info(f'Reloading module {module}.')
    try:
        module_obj = importlib.import_module(module)
        importlib.reload(module_obj)
        module_instance = module_obj.Plugin(client=client)
        logging.info(f'Updating bot commands for the module {module}.')
        db.update_plugin_commands(module=module_instance.classname, methods=module_instance.methods)
        globals.plugins[module] = {'module': module, 'instance': module_instance}
        return None
    except Exception as e:
        return e
