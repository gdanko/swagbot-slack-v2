from pprint import pprint
from datetime import datetime, timedelta
from swagbot.core import BasePlugin
import argparse
import logging
import os
import swagbot.database.pagerduty as db
import swagbot.globals as globals
import swagbot.request as request
import swagbot.scheduler
import swagbot.utils.core as utils
import sys

class Plugin(object):
    def __init__(self, client):
        self.__configure_parsers()
        self.methods = self.__setup_methods()
        self.client = client
        BasePlugin.__init__(self, client)

        config_file = os.path.join(globals.config_root, 'swagbot.plugins.pagerduty.yml')
        self.config = utils.parse_config(path=config_file)
        self.pagerduty_key = self.config.get('key', None)
        self.formatter = '%Y-%m-%d %H:%M:%S'
        self.extra_headers = {
            'Accept': 'application/json',
            'Authorization': f'Token token={self.pagerduty_key}',
            'Content-Type': 'application/json',
        }
        self.scheduler = swagbot.scheduler.Scheduler(
            name = self.classname
        )
    
        schema_is_valid = db.validate_schema()
        if not schema_is_valid:
            db.create_schema()

        self.__refresh_data()
        self.__add_scheduled_jobs()
        self.scheduler.start()
 
###############################################################################
#
# PagerDuty Event functions
#
###############################################################################

    def events(self, command=None):
        sys.argv = command.argv
        try:
            args = self.events_parser.parse_args()
        except:
            command.output.errors.append(self.events_parser.format_help().rstrip())
            return

        start = None
        end = None

        if args.start:
            start = utils.validate_date(date=args.start)
            if not start:
                command.output.errors.append(f'Invalid start time format: {args.start}')
                return
        
        if args.end:
            args.end = utils.validate_date(date=args.end)
            if not end:
                command.output.errors.append(f'Invalid end time format: {args.end}')
                return
        
        if args.status:
            status = args.status
        elif self.config['commands']['events']['statuses']:
            status = self.config['commands']['events']['statuses']
        else:
            status = ['triggered']

        success, data = self.__pagerduty_events(status=status, urgency=args.urgency, service=args.service, start=start, end=start, limit=args.limit)
        if success:
            if len(data) > 0:
                command.success = True
                for chunk in utils.chunker(data, 10):
                    command.output.messages.append(utils.generate_table(headers=['Created', 'Service', 'Description', 'Urgency', 'Status', 'Owner'], data=chunk))
            else:
                command.output.errors.append('No PagerDuty events found matching the specified criteria.')
        else:
            command.output.errors.append(data)

    def __events_ticker(self):
        name = 'events_ticker'
        success, data = self.__pagerduty_events(status=self.config['jobs'][name]['statuses'], limit=100)
        if success:
            if len(data) > 0:
                plural = 'event' if len(data) == 1 else 'events'
                are = 'is' if len(data) == 1 else 'are'
                for channel_id in self.config['jobs'][name]['channels']:
                    self.client.chat_postMessage(channel=channel_id, text=f'There {are} currently {len(data)} triggered {plural} in PagerDuty.')
                    text = utils.generate_table(headers=['Created', 'Service', 'Description', 'Urgency', 'Status', 'Owner'], data=data)
                    self.client.chat_postMessage(channel=channel_id, text=f'```{text}```')
            else:
                for channel_id in self.config['jobs'][name]['channels']:
                    self.client.chat_postMessage(channel=channel_id, text='There are currently no triggered incidents.')
        else:
            for channel_id in self.config['jobs'][name]['channels']:
                self.client.chat_postMessage(channel=channel_id, text='Unable to retrieve PagerDuty events at this time. I will try again in a few minutes.')
   
    def __pagerduty_events(self, status=[], urgency=[], service=[], start=None, end=None, limit=100):
        qs = {
            'team_ids[]': self.config['teams'],
            'limit': str(limit),
        }
        if len(status) > 0:  qs['statuses[]'] = status
        if len(urgency) > 0: qs['urgencies[]'] = urgency
        if len(service) > 0: qs['services_ids[]'] = service
        if start:            qs['since'] = start.strftime(self.formatter)
        if end:              qs['until'] = end.strftime(self.formatter)

        uri = f'https://api.pagerduty.com/incidents?{self.__build_qs_list(qs=qs)}'
        request.get(self, uri=uri, extra_headers=self.extra_headers)
        if self.response['success']:
            incidents = []
            for incident in self.response['incidents']:
                created = incident['created_at']
                assignees = [assignee['assignee']['summary'] for assignee in incident['assignments'] if assignee['assignee']['summary'] != 'DevOps Awareness']
                incidents.append([
                    datetime.fromisoformat(created.rstrip('Z')),
                    incident['service']['summary'][0:40],
                    incident['title'][0:40].replace('\n', ' '),
                    incident['urgency'],
                    incident['status'],
                    assignees[0] if len(assignees) > 0 else 'Unknown',
                ])
            return True, incidents
        else:
            False, 'Failed to retrieve PagerDuty events. Please try again later.'
    
###############################################################################
#
# PagerDuty Oncall functions
#
###############################################################################

    def oncall(self, command=None):
        sys.argv = command.argv
        try:
            args = self.oncall_parser.parse_args()
        except:
            command.output.errors.append(self.oncall_parser.format_help().rstrip())
            return
        
        if args.min:
            min = args.min
        elif self.config['commands']['oncall']['min']:
            min = self.config['commands']['oncall']['min']
        else:
            min = 1

        if args.max:
            max = args.max
        elif self.config['commands']['oncall']['max']:
            max = self.config['commands']['oncall']['max']
        else:
            max = 1000
        
        if args.id:
            escalation_policy_ids = args.id
        elif self.config['commands']['oncall']['escalation_policy_ids']:
            escalation_policy_ids = self.config['commands']['oncall']['escalation_policy_ids']
        else:
            escalation_policy_ids = []

        self.__oncall_search(escalation_policy_ids=escalation_policy_ids)
        oncalls = db.get_oncall_temp(min=min, max=max)
        if oncalls:
            if len(oncalls) > 0:
                command.success = True
                for chunk in utils.chunker(oncalls, 25):
                    output = []
                    for item in chunk:
                        output.append([
                            item['escalation_policy'],
                            item['level'],
                            item['name'],
                        ])
                    command.output.messages.append(utils.generate_table(headers=['Escalation Policy', 'Level', 'Name'], data=output))
            else:
                command.output.errors.append('Crikey! No oncall data found. Try again later.')
        else:
            command.output.errors.append('Failed to get oncall information. Try again later.')

    def __oncall_ticker(self):
        name = 'oncall_ticker'
        self.__oncall_search(escalation_policy_ids=self.config['jobs'][name]['escalation_policy_ids'])
        oncalls = db.get_oncall_temp(min=self.config['jobs'][name]['min'], max=self.config['jobs'][name]['max'])
        if oncalls:
            if len(oncalls) > 0:
                output = []
                for item in oncalls:
                    output.append([
                        item['escalation_policy'],
                        item['level'],
                        item['name'],
                    ])
                for channel_id in self.config['jobs'][name]['channels']:
                    self.client.chat_postMessage(channel=channel_id, text=f'Curretly oncall')
                    text = utils.generate_table(headers=['Escalation Policy', 'Level', 'Name'], data=output)
                    self.client.chat_postMessage(channel=channel_id, text=f'```{text}```')
            else:
                for channel_id in self.config['jobs'][name]['channels']:
                    self.client.chat_postMessage(channel=channel_id, text='No oncall data found. I will try again later.')
        else:
            for channel_id in self.config['jobs'][name]['channels']:
                self.client.chat_postMessage(channel=channel_id, text='No oncall data found. I will try again later.')

    def __oncall_search(self, escalation_policy_ids=[]):
        db.wipe_oncall_temp()
        qs = {
            'limit': str(100),
            'team_ids[]': self.config['teams'],
        }
        if len(escalation_policy_ids) > 0:
            qs['escalation_policy_ids[]'] = escalation_policy_ids

        uri = f'https://api.pagerduty.com/oncalls?{self.__build_qs_list(qs=qs)}'
        request.get(self, uri=uri, extra_headers=self.extra_headers)
        if self.response['success']:
            for oncall in self.response['oncalls']:
                if oncall['user']['summary'] != 'DevOps Awareness':
                    db.add_oncall_temp(
                        summary=oncall['escalation_policy']['summary'],
                        level=oncall['escalation_level'],
                        name=oncall['user']['summary']
                    )

###############################################################################
#
# PagerDuty Schedule Override functions
#
###############################################################################

    def overrides(self, command=None):
        help = {}
        for action in self.overrides_parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for choice, subparser in action.choices.items():
                    help[choice] = subparser.format_help()

        sys.argv = command.argv
        try:
            args = self.overrides_parser.parse_args()
        except:
            command.output.errors.append(help[sys.argv[1]])
            return

        if hasattr(args, 'start'):
            args.start = utils.to8601(args.start)
            if not args.start:
                command.output.errors.append(f'Invalid start time format: {args.start}')
                return
        
        if hasattr(args, 'end'):
            args.end = utils.to8601(args.end)
            if not args.end:
                command.output.errors.append(f'Invalid end time format: {args.end}')
                return

        try:
            args.func(args, command)
        except Exception as e:
            print(e)
            command.output.errors.append(self.overrides_parser.format_help().rstrip())
            return

    def overrides_list(self, args, command):
        qs = {
            'since': args.start,
            'until': args.end,
        }
        uri = f'https://api.pagerduty.com/schedules/{args.id}/overrides?{self.__build_qs_list(qs=qs)}'
        request.get(self, uri=uri, extra_headers=self.extra_headers)
        if self.response['success']:
            overrides = []
            for override in self.response['overrides']:
                overrides.append([
                    override['id'],
                    args.id,
                    datetime.fromisoformat(override['start'].rstrip('Z')).strftime(self.formatter),
                    datetime.fromisoformat(override['end'].rstrip('Z')).strftime(self.formatter),
                    override['user']['summary'],
                ])
            if len(overrides) > 0:
                command.success = True
                for chunk in utils.chunker(overrides, 10):
                    command.output.messages.append(utils.generate_table(headers=['ID', 'Schedule ID', 'Start', 'End', 'Name'], data=chunk))
            else:
                command.output.errors.append('Crikey! No override data found. Try again later.')
        else:
            command.output.errors.append(self.response['error']['message'])
            return

    def overrides_add(self, args, command):
        payload = {
            'overrides' :[
                {
                    'start': args.start,
                    'end': args.end,
                    'user': {
                        'id': args.userid,
                        'type': 'user_reference', 
                    }
                }
            ]
        }
        uri = f'https://api.pagerduty.com/schedules/{args.id}/overrides'
        request.post(self, uri=uri, extra_headers=self.extra_headers, payload=payload)
        if self.response['success']:
            command.success = True
            command.output.messages.append(f'Successfully added schedule override ID {self.response["body"][0]["override"]["id"]}.')
        else:
            command.output.errors.append('Failed to add the schedule override.')

    def overrides_delete(self, args, command):
        uri = f'https://api.pagerduty.com/schedules/{args.id}/overrides/{args.override_id}'
        request.delete(self, uri=uri, extra_headers=self.extra_headers)
        if self.response['success']:
            command.success = True
            command.output.messages.append(f'Successfully deleted schedule override ID {args.override_id}.')
        else:
            command.output.errors.append(f'Failed to delete the schedule override: {self.response["error"]["message"]}')

###############################################################################
#
# PagerDuty Escalation Policy functions
#
###############################################################################

    def policies(self, command=None):
        results = db.list(table_name='escalation_policies')
        if results != None:
            if len(results) > 0:
                for chunk in utils.chunker(results, 25):
                    output = []
                    for policy in chunk:
                        output.append([policy['id'], policy['name']])
                    command.success = True
                    command.output.messages.append(utils.generate_table(headers=['Escalation Policy ID', 'Escalation Policy Name'], data=output))
            else:
                command.output.errors.append(f'You haven\'t added any escalation policies.')
        else:
            command.output.errors.append(f'Failed to get the list of escalation policies.')
    
###############################################################################
#
# PagerDuty Schedule functions
#
###############################################################################

    def schedules(self, command=None):
        sys.argv = command.argv
        try:
            args = self.schedules_parser.parse_args()
        except:
            command.output.errors.append(self.schedules_parser.format_help().rstrip())
            return
        
        if not args.view:
            results = db.list(table_name='schedules')
            if results != None:
                if len(results) > 0:
                    for chunk in utils.chunker(results, 25):
                        schedules = []
                        for schedule in chunk:
                            schedules.append([schedule['id'], schedule['name']])
                        command.success = True
                        command.output.messages.append(utils.generate_table(headers=['Schedule ID', 'Schedule Name'], data=schedules))
                else:
                    command.output.errors.append(f'You haven\'t added any schedules.')
            else:
                command.output.errors.append(f'Failed to get the list of schedules.')

        elif args.view:
            since = datetime.now()
            until = since + timedelta(days = args.days)
            qs = {
                'overflow': 'true',
                'include_oncall': 'true',
                'since': since.strftime(self.formatter),
                'until': until.strftime(self.formatter),
            }
            qs_str = self.__generate_query_string(qs, args)
            uri = f'https://api.pagerduty.com/schedules/{args.view}?{qs_str}'
            request.get(self, uri=uri, extra_headers=self.extra_headers)
            if self.response['success']:
                schedules = []
                name = self.response['schedule']['name']
                for person in self.response['schedule']['final_schedule']['rendered_schedule_entries']:
                    start = datetime.fromisoformat(person['start'].rstrip('Z'))
                    end = datetime.fromisoformat(person['end'].rstrip('Z'))
                    schedules.append([name, start.strftime(self.formatter), end.strftime(self.formatter), person['user']['summary']])
                if len(schedules) > 0:
                    command.success = True
                    for chunk in utils.chunker(schedules, 20):
                        command.output.messages.append(utils.generate_table(headers=['Schedule', 'Start', 'End', 'Name'], data=chunk))
                else:
                    command.output.errors.append(f'No schedule information found.')
            else:
                if 'error' in self.response and 'message' in self.response['error']:
                    command.output.errors.append(self.response['error']['message'])
                else:
                    command.output.errors.append(f'Schedule ID {args.view} not found.')
        else:
            command.output.errors.append(self.schedules_parser.format_help().rstrip())

###############################################################################
#
# PagerDuty Services functions
#
###############################################################################

    def services(self, command=None):
        # Need a function to better handle verification
        sys.argv = command.argv[0:2]
        sys.argv.append(' '.join(command.argv[2:]))
        try:
            args = self.services_parser.parse_args()
        except:
            command.output.errors.append(self.services_parser.format_help().rstrip())
            return
        if args.pattern:
            args.pattern = args.pattern.replace('*', '%')

        results = self.__services_search(pattern=args.pattern)
        if results != None:
            if len(results) > 0:
                command.success = True
                for chunk in utils.chunker(results, 25):
                    output = []
                    for service in chunk:
                        output.append([service['id'], service['name']]) 
                    command.output.messages.append(utils.generate_table(headers=['Service ID', 'Service Name'], data=output))
            else:
                command.output.errors.append(f'You haven\'t added any PagerDuty services.')
        else:
            command.output.errors.append(f'Failed to get the list of PagerDuty services.')

    def __services_search(self, pattern=None):
        results = db.list(table_name='services', pattern=pattern)
        return results

###############################################################################
#
# PagerDuty Users functions
#
###############################################################################

    def users(self, command=None):
        results = db.list(table_name='users')
        if results != None:
            if len(results) > 0:
                for chunk in utils.chunker(results, 25):
                    output = []
                    for policy in chunk:
                        output.append([policy['id'], policy['name']])
                    command.success = True
                    command.output.messages.append(utils.generate_table(headers=['User ID', 'User Name'], data=output))
            else:
                command.output.errors.append(f'Failed to get the list of users.')
        else:
            command.output.errors.append(f'Failed to get the list of users.')

###############################################################################
#
# PagerDuty Maintenance functions
#
###############################################################################

    def windows(self, command=None):
        help = {}
        for action in self.windows_parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for choice, subparser in action.choices.items():
                    help[choice] = subparser.format_help()

        sys.argv = command.argv
        try:
            args = self.windows_parser.parse_args()
        except:
            command.output.errors.append(help[sys.argv[1]])
            return

        if hasattr(args, 'start'):
            args.start = utils.to8601(args.start)
            if not args.start:
                command.output.errors.append(f'Invalid start time format: {args.start}')
                return
 
        if hasattr(args, 'end'):
            args.end = utils.to8601(args.end)
            if not args.end:
                command.output.errors.append(f'Invalid end time format: {args.end}')
                return

        try:
            args.func(args, command)
        except Exception as e:
            print(e)
            command.output.errors.append(self.windows_parser.format_help().rstrip())
            return

    def windows_list(self, args, command):
        pass
        # qs = {
        #     'since': args.start,
        #     'until': args.end,
        # }
        # uri = f'https://api.pagerduty.com/schedules/{args.id}/overrides?{self.__build_qs_list(qs=qs)}'
        # request.get(self, uri=uri, extra_headers=self.extra_headers)
        # if self.response['success']:
        #     overrides = []
        #     for override in self.response['overrides']:
        #         overrides.append([
        #             override['id'],
        #             args.id,
        #             datetime.fromisoformat(override['start'].rstrip('Z')).strftime(self.formatter),
        #             datetime.fromisoformat(override['end'].rstrip('Z')).strftime(self.formatter),
        #             override['user']['summary'],
        #         ])
        #     if len(overrides) > 0:
        #         command.success = True
        #         for chunk in utils.chunker(overrides, 10):
        #             command.output.messages.append(utils.generate_table(headers=['ID', 'Schedule ID', 'Start', 'End', 'Name'], data=chunk))
        #     else:
        #         command.output.errors.append('Crikey! No override data found. Try again later.')
        # else:
        #     command.output.errors.append(self.response['error']['message'])
        #     return

    def windows_add(self, args, command):
        pass
        # payload = {
        #     'overrides' :[
        #         {
        #             'start': args.start,
        #             'end': args.end,
        #             'user': {
        #                 'id': args.userid,
        #                 'type': 'user_reference',
        #             }
        #         }
        #     ]
        # }
        # uri = f'https://api.pagerduty.com/schedules/{args.id}/overrides'
        # request.post(self, uri=uri, extra_headers=self.extra_headers, payload=payload)
        # if self.response['success']:
        #     command.success = True
        #     command.output.messages.append(f'Successfully added schedule override ID {self.response["body"][0]["override"]["id"]}.')
        # else:
        #     command.output.errors.append('Failed to add the schedule override.')

    def windows_delete(self, args, command):
        pass
        # uri = f'https://api.pagerduty.com/schedules/{args.id}/overrides/{args.override_id}'
        # request.delete(self, uri=uri, extra_headers=self.extra_headers)
        # if self.response['success']:
        #     command.success = True
        #     command.output.messages.append(f'Successfully deleted schedule override ID {args.override_id}.')
        # else:
        #     command.output.errors.append(f'Failed to delete the schedule override: {self.response["error"]["message"]}')

###############################################################################
#
# PagerDuty Scheduled Job functions
#
###############################################################################

    def __add_scheduled_jobs(self):
        # success, message = self.scheduler.delete_jobs_for_module(module=self.classname)
        # if success:
        self.scheduler.add_job(module=self.classname, name='refresh_data', interval=60, function=(self.__refresh_data, ()), enabled=1)
        self.scheduler.add_job(module=self.classname, name='events_ticker', interval=10, function=(self.__events_ticker, ()), enabled=1)
        self.scheduler.add_job(module=self.classname, name='oncall_ticker', interval=10, function=(self.__oncall_ticker, ()), enabled=1)
        # else:
        #     logging.error(f'Failed to add the scheduled jobs for "{self.classname}": {message}')

###############################################################################
#
# PagerDuty Table Population functions
#
###############################################################################

    # Table population
    def __refresh_data(self):
        self.__populate(item_type='escalation_policies')
        self.__populate(item_type='schedules')
        self.__populate(item_type='services')
        self.__populate(item_type='users')

    def __populate(self, item_type=None, total=0, offset=0):
        if offset == 0:
            logging.info(f'Populating the PagerDuty {item_type} database table.')
        qs = {
            'limit': str(100),
            'offset': str(offset),
            'team_ids[]': self.config['teams'],
        }
        uri = f'https://api.pagerduty.com/{item_type}?{self.__build_qs_list(qs=qs)}'
        request.get(self, uri=uri, extra_headers=self.extra_headers)

        for item in self.response[item_type]:
            db.add(table_name=item_type, name=item['name'], id=item['id'])

        if self.response['more'] == True:
            total = total + len(self.response[item_type])
            self.__populate(item_type=item_type, total=total, offset=total+1)
        else:
            logging.info('Done!')
    
###############################################################################
#
# Query String functions
#
###############################################################################

    def __build_qs_list(self, qs={}):
        qs_list = []
        for key, value in qs.items():
            if type(value) == str:
                qs_list.append(f'{key}={value}')
            elif type(value) == list:
                for item in value:
                    qs_list.append(f'{key}={item}')
        return '&'.join(qs_list)

    def __generate_query_string(self, qs, args):
        if not qs:
            qs = {'team_ids[]': self.config['teams']}
        for key in vars(args):
            value = getattr(args, key)

            if key == 'limit':
                qs['limit'] = str(value) if value else str(100)
            elif key == 'status' and value:
                qs['statuses[]'] = value
            elif key == 'urgency' and value:
                qs['urgencies[]'] = value
            elif key == 'service' and value:
                qs['service_ids[]'] = value
            elif key == 'id' and value:
                qs['escalation_policy_ids[]'] = value
            elif key == 'pattern' and value:
                pattern = value.lstrip('"').rstrip('"').lstrip("'").rstrip("'")
                results = self.__services_search(pattern=pattern)
                if results:
                    qs['service_ids[]'] = [item['id'] for item in results]
        
        if not 'limit' in qs:
            qs['limit'] = str(100)

        return self.__build_qs_list(qs=qs)

###############################################################################
#
# Argument Parsers
#
###############################################################################

    def __configure_parsers(self):
        # Event
        self.events_parser = argparse.ArgumentParser(add_help=False, prog='incidents', description='List incidents for your configured PagerDuty teams.')
        self.events_parser.add_argument('--status', help='Specify a status (triggered, acknowledged, resolved). Can be used more than once.', metavar='<str>', choices=['triggered', 'acknowledged', 'resolved'], default=[], required=False, action='append')
        self.events_parser.add_argument('-u', '--urgency', help='Specify an urgency (high, low). Can be used more than once.', metavar='<urgency>', choices=['high', 'low'], default=[], required=False, action='append')
        self.events_parser.add_argument('-s', '--service', help='Specify an service ID. Can be used more than once. Cannot be used with --pattern.', metavar='<service>', default=[], required=False, action='append')
        self.events_parser.add_argument('--start', help='Optional start date in the format YYYY-MM-DD.', metavar='<date>', required=False, action='store')
        self.events_parser.add_argument('--end', help='Optional end date in the format YYYY-MM-DD.', metavar='<date>', required=False, action='store')
        self.events_parser.add_argument('-l', '--limit', help='Limit the results to <int>.', metavar='<int>', required=False, action='store', default=100, type=int)

        # Services
        self.services_parser = argparse.ArgumentParser(add_help=False, prog='schedules', description='List services for your configured PagerDuty teams.')
        self.services_parser.add_argument('-p', '--pattern', help='Specify a search pattern, e.g., *VKM*.', metavar='<pattern>.', required=False, action='store')
        self.services_parser.set_defaults(func=self.services)

        # Schedules
        self.schedules_parser = argparse.ArgumentParser(add_help=False, prog='schedules', description='List and view schedules for your configured PagerDuty teams.')
        self.schedules_parser.add_argument('-v', '--view', help='View an escalation policy for your configured PagerDuty teams.', metavar='<id>', required=False, action='store')
        self.schedules_parser.add_argument('-s', '--start', help='Optional start time for --view in the format YYYY-MM-DD.', metavar='<date>', required=False, action='store')
        self.schedules_parser.add_argument('-d', '--days', help='How many days to view.', metavar='<days>', required=False, action='store', type=int, default=7)

        # Oncall
        self.oncall_parser = argparse.ArgumentParser(add_help=False, prog='oncall', description='View oncall rotations for your configured PagerDuty teams.')
        self.oncall_parser.add_argument('-i', '--id', help='Specify an escalation policy ID. Can be used more than once.', required=False, action='append')
        self.oncall_parser.add_argument('--min', help='Specify the minimum oncall level to display.', required=False, action='store')
        self.oncall_parser.add_argument('--max', help='Specify the maximum oncall level to display.', required=False, action='store')

        # Overrides
        self.overrides_parser = argparse.ArgumentParser(add_help=False, prog='overrides', description='Manage PagerDuty schedule overrides.')
        self.overrides_parser.set_defaults(func=self.overrides)
        subparsers = self.overrides_parser.add_subparsers(help='Sub-command help')

        parser_list = subparsers.add_parser('list', add_help=False, help='List PagerDuty schedule overrides.')
        parser_list.add_argument('-i', '--id', help='The schedule ID.', metavar='<id>', required=True, action='store')
        parser_list.add_argument('-s', '--start', help='The start time in the format YYYY-MM-DD HH:MM:SS.', metavar='<timestamp>', required=True, action='store')
        parser_list.add_argument('-e', '--end', help='The end time in the format YYYY-MM-DD HH:MM:SS.', metavar='<timestamp>', required=True, action='store')
        parser_list.set_defaults(func=self.overrides_list)

        parser_add = subparsers.add_parser('add', add_help=False, help='Add a PagerDuty schedule override.')
        parser_add.add_argument('-i', '--id', help='The schedule ID.', metavar='<id>', required=True, action='store')
        parser_add.add_argument('-s', '--start', help='The start time in the format YYYY-MM-DD HH:MM:SS.', metavar='<timestamp>', required=True, action='store')
        parser_add.add_argument('-e', '--end', help='The end time in the format YYYY-MM-DD HH:MM:SS.', metavar='<timestamp>', required=True, action='store')
        parser_add.add_argument('-u', '--userid', help='The ID of the user.', metavar='<userid>', required=True, action='store')
        parser_add.set_defaults(func=self.overrides_add)

        parser_delete = subparsers.add_parser('delete', add_help=False, help='Delete a PagerDuty schedule override.')
        parser_delete.add_argument('-i', '--id', help='The schedule ID.', metavar='<id>', required=True, action='store')
        parser_delete.add_argument('-o', '--override-id', help='The override ID.', metavar='<id>', required=True, action='store')
        parser_delete.set_defaults(func=self.overrides_delete)

        # Maintenance Windows
        self.windows_parser = argparse.ArgumentParser(add_help=False, prog='windows', description='Manage PagerDuty maintenance windows.')
        self.windows_parser.set_defaults(func=self.windows)
        subparsers = self.windows_parser.add_subparsers(help='Sub-command help')

        parser_windows_list = subparsers.add_parser('list', add_help=False, help='List PagerDuty maintenance windows.')
        parser_windows_list.add_argument('-i', '--id', help='The schedule ID.', metavar='<id>', required=True, action='store')
        parser_windows_list.add_argument('-s', '--start', help='The start time in the format YYYY-MM-DD HH:MM:SS.', metavar='<timestamp>', required=True, action='store')
        parser_windows_list.add_argument('-e', '--end', help='The end time in the format YYYY-MM-DD HH:MM:SS.', metavar='<timestamp>', required=True, action='store')
        parser_windows_list.set_defaults(func=self.windows_list)

        parser_windows_add = subparsers.add_parser('add', add_help=False, help='Add a PagerDuty maintenance window.')
        parser_windows_add.add_argument('-i', '--id', help='The schedule ID.', metavar='<id>', required=True, action='store')
        parser_windows_add.add_argument('-s', '--start', help='The start time in the format YYYY-MM-DD HH:MM:SS.', metavar='<timestamp>', required=True, action='store')
        parser_windows_add.add_argument('-e', '--end', help='The end time in the format YYYY-MM-DD HH:MM:SS.', metavar='<timestamp>', required=True, action='store')
        parser_windows_add.add_argument('-u', '--userid', help='The ID of the user.', metavar='<userid>', required=True, action='store')
        parser_windows_add.set_defaults(func=self.windows_add)

        parser_windows_delete = subparsers.add_parser('delete', add_help=False, help='Delete a PagerDuty maintenance window.')
        parser_windows_delete.add_argument('-i', '--id', help='The schedule ID.', metavar='<id>', required=True, action='store')
        parser_windows_delete.add_argument('-o', '--override-id', help='The override ID.', metavar='<id>', required=True, action='store')
        parser_windows_delete.set_defaults(func=self.windows_delete)

        self.policies_parser = argparse.ArgumentParser(add_help=False, prog='policies', description='List escalation policies for your configured PagerDuty teams.')
        self.policies_parser.set_defaults(func=self.policies)

        self.users_parser = argparse.ArgumentParser(add_help=False, prog='users', description='List users for your configured PagerDuty teams.')
        self.users_parser.set_defaults(func=self.users)

    def __setup_methods(self):
        return {
            'events': {
                'description': self.events_parser.description,
                'usage': self.events_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 1,
            },
            'oncall': {
                'description': self.oncall_parser.description,
                'usage': self.oncall_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 1,
            },
            'overrides': {
                'description': self.overrides_parser.description,
                'usage': self.overrides_parser.format_help().rstrip(),
                'is_admin': 1,
                'type': 'private',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 1,             
            },
            'policies': {
                'description': self.policies_parser.description,
                'usage': self.policies_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 1,           
            },
            'schedules': {
                'description': self.schedules_parser.description,
                'usage': self.schedules_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 1,
            },
            'services': {
                'description': self.services_parser.description,
                'usage': self.services_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'private',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 1,             
            },
            'users': {
                'description': self.users_parser.description,
                'usage': self.users_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'private',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 1,             
            },
            # 'windows': {
            #     'usage': self.windows_parser.format_help().rstrip(),
            #     'is_admin': 1,
            #     'type': 'private',
            #     'can_be_disabled': 1,
            #     'hidden': 0,
            #     'monospace': 1,
            #     'split_output': 1,
            # },
        }
