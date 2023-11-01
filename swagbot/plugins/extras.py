from swagbot.core import BasePlugin
import argparse
import datetime
import logging
import os
import pint
import random
import re
import swagbot.database.extras as db
import swagbot.globals as globals
import swagbot.request as request
import swagbot.utils.core as utils
import sys
import time

class Plugin(object):
    def __init__(self, client):
        self.__configure_parsers()
        self.methods = self.__setup_methods()
        BasePlugin.__init__(self, client)

        config_file = os.path.join(globals.config_root, 'swagbot.plugins.extras.yml')
        self.config = utils.parse_config(path=config_file)
        self.alphavantage_key = self.config['keys'].get('alphavantage', None)
        self.tinyurl_key = self.config['keys'].get('tinyurl', None)
        self.openweathermap_key = self.config['keys'].get('openweathermap', None)
        self.wordnik_key = self.config['keys'].get('wordnik', None)

    def apg(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.apg_parser.parse_args()
        except:
            command.output.errors.append(self.apg_parser.format_help().rstrip())
            return

        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        numbers = '0123456789'
        symbols = '!@#$%^&*()_+-={}|[]\:\';\'<>?,./'
        characters = []

        if args.uppercase:
            characters += list(letters.upper())
        if args.lowercase:
            characters += list(letters.lower())
        if args.numbers:
            characters += list(numbers)
        if args.special:
            characters += list(symbols)
        
        if len(characters) == 0:
            characters += list(letters.upper())
            characters += list(letters.lower())
            characters += list(numbers)
            characters += list(symbols)

        length = int(args.length)
        quantity = int(args.quantity)

        if (quantity <= 0) or (quantity > 10):
            quantity = 10

        for x in range(0, quantity):
            command.output.messages.append(''.join(random.choice(characters) for x in range(length)))
        command.success = True

    def ball(self, command=None):
        if len(command.argv) > 1:
            answers = [
                'As I see it, yes.',
                'Ask again later.',
                'Better not tell you now.',
                'Cannot predict now.',
                'Concentrate and ask again.',
                'Don\'t count on it.',
                'It is certain.',
                'It is decidedly so.',
                'Most likely.',
                'My reply is no.',
                'My sources say no.',
                'Outlook good.',
                'Outlook not so good.',
                'Reply hazy, try again.',
                'Signs point to yes.',
                'Very doubtful.',
                'Without a doubt.',
                'Yes, definitely.',
                'Yes.',
                'You may rely on it.'
            ]
            command.success = True
            command.output.messages.append(random.choice(answers))
        else:
            command.output.errors.append('No question specified.')
            command.output.errors.append(f'Usage: {command.usage}')

    def bytes(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.bytes_parser.parse_args()
        except:
            command.output.errors.append(self.bytes_parser.format_help().rstrip())
            return

        conversion_table = {
            'bytes': {'mult': 0, 'display': 'bytes'},
            'k': {'mult': 1, 'display': 'KiB'},
            'm': {'mult': 2, 'display': 'MiB'},
            'g': {'mult': 3, 'display': 'GiB'},
            't': {'mult': 4, 'display': 'TiB'},
            'p': {'mult': 5, 'display': 'PiB'},
            'e': {'mult': 6, 'display': 'EiB'},
        }
        amount = int(args.amount)
        unit = args.unit.lower()
        units = ['bytes', 'k', 'm', 'g', 't', 'p', 'e']
        all_units = ['bytes', 'k', 'm', 'g', 't', 'p', 'e', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb'] 
        base = 1024
        if unit in all_units:
            if unit != 'bytes':
                unit = unit[0][0]
        out = []
        bit = None
        byte = None
        bit = int((amount * (base ** conversion_table[unit]['mult']) * 8))
        byte = int(bit / 8)
        out.append('{:.1f} bits'.format(bit))

        output = [
            [args.amount, args.unit]
        ]
        for key in units:
            if key != unit:
                multiplier = conversion_table[key]['mult']
                converted = '{:.15f}'.format(byte / (base ** multiplier))
                i, d = re.split(r'\.\s*', str(converted))
                if int(i) > 0:
                    converted = '{:.1f}'.format(float(i))
                elif int(d) == 0:
                    converted = int(converted)
            
                if float(converted) > 0:
                    output.append([
                        converted,
                        conversion_table[key]['display']
                    ])

        if len(output) > 0:
            command.success = True
            command.output.messages.append(utils.generate_table(headers=['Amount', 'Unit'], data=output))
        else:
            command.output.errors.append('Hmmm something went wrong.')

    def calc(self, command=None):
        command.argv.pop(0)
        equation = ' '.join(command.argv)
        if equation:
            binary = 'bc'
            if utils.binary_exists(binary):
                answer = None
                try:
                    answer = os.popen('echo "{}" | {}'.format(equation, binary)).read().rstrip()
                    if answer == '':
                        command.output.errors.append(f'Calculation failed for: {equation}')
                    else:
                        command.success = True
                        command.output.messages.append(f'{equation} = {answer}')
                except Exception as e:
                    command.output.errors.append(f'Calculation failed for: {equation}: {e}')
            else:
                command.output.errors.append(f'The "{binary}" command was not found in my PATH.')
        else:
            command.output.errors.append(f'No input specified.')
            command.output.errors.append(f'Usage: {command.usage}')

    def crypto(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.crypto_parser.parse_args()
        except:
            command.output.errors.append(self.crypto_parser.format_help().rstrip())
        
        from_code = getattr(args, 'from').upper()
        to_code = getattr(args, 'to').upper()

        to_lookup = db.crypto_lookup(currency_code=to_code)
        if not to_lookup:
            command.output.errors.append(f'Cryptocurrency code {to_lookup} not found.')

        from_lookup = db.crypto_lookup(currency_code=from_code)
        if not from_lookup:
            command.output.errors.append(f'Cryptocurrency code {from_lookup} not found.')

        uri = 'https://www.alphavantage.co/query'
        qs = {
            'function': 'CURRENCY_EXCHANGE_RATE',
            'from_currency': from_code,
            'to_currency': to_code,
            'apikey': self.alphavantage_key,
        }
        request.get(self, uri=uri, qs=qs)
        if 'Realtime Currency Exchange Rate' in self.response:
            to_amount = round(float(args.amount) * float(self.response['Realtime Currency Exchange Rate']['5. Exchange Rate']), 2)
            command.success = True
            command.output.messages.append(f'{args.amount} {from_code} = {to_amount} {to_code}')
        else:
            command.output.errors.append('Incomplete data received.')

    def currency(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.currency_parser.parse_args()
        except:
            command.output.errors.append(self.currency_parser.format_help().rstrip())
            return

        if hasattr(args, 'from'):
            from_code = getattr(args, 'from').upper()
        if hasattr(args, 'to'):
            to_code = getattr(args, 'to').upper()

        if from_code and to_code:
            to_lookup = db.currency_lookup(currency_code=to_code)
            if not to_lookup:
                command.output.errors.append(f'Currency code {to_lookup} not found.')

            from_lookup = db.currency_lookup(currency_code=from_code)
            if not from_lookup:
                command.output.errors.append(f'Currency code {from_lookup} not found.')

            uri = 'https://www.alphavantage.co/query'
            qs = {
                'function': 'CURRENCY_EXCHANGE_RATE',
                'from_currency': from_code,
                'to_currency': to_code,
                'apikey': self.alphavantage_key,
            }
            request.get(self, uri=uri, qs=qs)
            if 'Realtime Currency Exchange Rate' in self.response:
                to_amount = round(float(args.amount) * float(self.response['Realtime Currency Exchange Rate']['5. Exchange Rate']), 2)
                command.success = True
                command.output.messages.append(f'{args.amount} {from_code} = {to_amount} {to_code}')
            else:
                command.output.errors.append('Incomplete data received.')

    def dict(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.dict_parser.parse_args()
        except:
            command.output.errors.append(self.dict_parser.format_help().rstrip())
            return command.output

        if self.wordnik_key:
            limit = 4
            uri = f'http://api.wordnik.com/v4/word.json/{args.word}/definitions'
            qs = {
                'api_key': self.wordnik_key,
                'includeRelated': 'false',
                'includeTags': 'false',
                'limit': limit,
                'sourceDictionaries': 'all',
                'useCanonical': 'false',
            }
            request.get(self, uri=uri, qs=qs)
            if self.success: # Is the JSON validated in the request module? If not, do so here.
                command.success = True
                response = self.response['body'] if 'body' in self.response else self.response

                if len(response) > 0:
                    for d in response:
                        if 'text' in d:
                            definition = d["text"].replace('<xref>', '').replace('</xref>', '')
                            command.output.messages.append(f'{args.word.title()}: {d["partOfSpeech"].title()}: {definition}')
                else:
                    command.output.errors.append(f'No definition found for {args.word}.')
            else:
                if 'error' in response:
                    command.output.errors.append(f'Dictionary lookup failed: {response["error"]}.')
                else:
                    command.output.errors.append('Dictionary lookup failed.')
        else:
            command.output.errors.append('Unable to fetch the definition due to missing API key.')

    def quakes(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.quakes_parser.parse_args()
        except:
            command.output.errors.append(self.quakes_parser.format_help().rstrip())
            return command.output
        
        now = int(time.time())
        local_8601_start_time = datetime.datetime.fromtimestamp(now - 86400).isoformat('T', 'seconds')
        local_8601_end_time = datetime.datetime.fromtimestamp(now).isoformat('T', 'seconds')

        uri = 'https://earthquake.usgs.gov/fdsnws/event/1/query'
        qs = {
            'format': 'geojson',
            'starttime': local_8601_start_time,
            'endtime': local_8601_end_time,
            'limit': args.limit, # Max limit via argparse????
            'minmagnitude': args.min,
            'offset': 1,
        }
        request.get(self, uri=uri, qs=qs)

        if self.success:
            output = []
            chunk_size = 20
            if len(self.response['features']) > 0:
                command.success = True
                for event in self.response['features']:
                    location = 'Unknown' if event['properties']['place'] is None else event['properties']['place']
                    output.append([
                        datetime.datetime.fromtimestamp(event['properties']['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.datetime.fromtimestamp(event['properties']['updated'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                        location,
                        event['properties']['type'].title(),
                        '{:.2f}'.format(event['properties']['mag'])
                    ])

                chunks = utils.array_to_chunks(output, chunk_size)
                for chunk in list(chunks):
                    command.output.messages.append(utils.generate_table(headers=['Time', 'Updated', 'Location', 'Description', 'Mag'], data=chunk))
            else:
                command.output.errors.append('No results found for the given criteria')

    def stocks(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.stocks_parser.parse_args()
        except:
            command.output.errors.append(self.stocks_parser.format_help().rstrip())
            return command.output

        stock_data = []
        for symbol in args.symbol:
            uri = 'https://www.alphavantage.co/query'
            qs = {
                'function': 'TIME_SERIES_INTRADAY',
                'symbol': symbol.upper(),
                'interval': '60min',
                'apikey': self.alphavantage_key,
            }
            request.get(self, uri=uri, qs=qs)
            # Trap this
            # {'Error Message': 'Invalid API call. Please retry or visit the documentation '
            #                   '(https://www.alphavantage.co/documentation/) for '
            #                   'TIME_SERIES_INTRADAY.',
            #  'status_code': 200,
            #  'success': True}
            if self.success:
                response = self.response['body'] if 'body' in self.response else self.response
                if 'Time Series (60min)' in response:
                    latest = list(response['Time Series (60min)'].keys())[0]
                    stock_data.append([
                        symbol.upper(),
                        latest,
                        response['Time Series (60min)'][latest]['1. open'],
                        response['Time Series (60min)'][latest]['2. high'],
                        response['Time Series (60min)'][latest]['3. low'],
                        response['Time Series (60min)'][latest]['4. close'],
                        response['Time Series (60min)'][latest]['5. volume'],
                    ])
            else:
                command.output.errors.append('Crikey! No stock data found. Try again later.')

        if len(stock_data) > 0:
            command.success = True
            command.output.messages.append(utils.generate_table(headers=['Symbol', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'], data=stock_data))
        else:
            command.output.errors.append('Crikey! No stock data found. Try again later.')

    def tiny(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.tiny_parser.parse_args()
        except:
            command.output.errors.append(self.tiny_parser.format_help().rstrip())
            return
        
        if self.tinyurl_key:
            args.url = args.url.lstrip('<').rstrip('>')
            if utils.validate_url(args.url):
                extra_headers = {
                    'Authorization': f'Bearer {self.tinyurl_key}'
                }
                payload = {
                    'url': args.url,
                    'domain': 'tinyurl.com',
                }
                uri = 'https://api.tinyurl.com/create'
                request.post(self, uri=uri, payload=payload, extra_headers=extra_headers)
                if self.response['success']:
                    if 'status_code' in self.response:
                        if self.response['status_code'] == 200:
                            if 'data' in self.response and 'tiny_url' in self.response['data']:
                                command.success = True
                                command.output.messages.append(self.response['data']['tiny_url'])
                            else:
                                command.output.errors.append('The URL shortener was unable to shorten the URL.')
                        else:
                            command.output.errors.append('The URL shortener returned a non-200 status code. Please try again later.')
                    else:
                        command.output.errors.append('The URL shortener returned an unknown error.')
                else:
                    command.output.errors.append('The URL shortener returned an unknown error.')
            else:
                logging.error(f'Failed to shorten the URL {args.url}')
                command.output.errors.append('You specified an invalid URL. This has been logged. If you feel this was an error, please contact a bot administrator.')
        else:
            logging.error('Missing tinyurl API key.')
            command.output.errors.append('I am currently unable to create tiny URLs. This error has been logged. Please try again later.')            

    def units(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.units_parser.parse_args()
        except:
            command.output.errors.append(self.units_parser.format_help().rstrip())
            return

        try:
            u = args.amount
            f = getattr(args, 'from')
            t = args.to
            ureg = pint.UnitRegistry()
            converted = ureg.Quantity(float(u), ureg.parse_expression(f)).to(t)._magnitude
            command.success = True
            command.output.messages.append('{:.2f} {} = {:.2f} {}'.format(float(u), f, float(converted), t))
        except Exception as e:
            logging.error(f'Conversion failed: {e}')
            command.output.errors.append(f'Conversion failed: {e}')

    def weather(self, command=None):
        sys.argv = command.argv
        try:
            with self.redirect_stdout_stderr(os.devnull):
                args = self.weather_parser.parse_args()
        except:
            command.output.errors.append(self.weather_parser.format_help().rstrip())
            return

        longitude = None
        latitude = None
        city = None
        state = None
        country = None
        if self.openweathermap_key:
            # Get the longitude and latitude for the given city
            # https://openweathermap.org/api/geocoding-api
            # https://api.openweathermap.org/geo/1.0/direct?q=San%20Diego,CA,US&limit=4&appid=xxxxxx
            # https://api.openweathermap.org/geo/1.0/direct?q=San+Diego,US&limit=5&appid=xxxxx
            # https://api.openweathermap.org/geo/1.0/zip?zip=92103&appid=xxxxx
            # https://api.openweathermap.org/geo/1.0/reverse?lat=32.74&long=-117.24&appid=xxxxx
            uri = 'https://api.openweathermap.org/geo/1.0/zip'
            qs = {
                'zip': args.loc,
                'limit': 1,
                'appid': self.openweathermap_key,
            }

            request.get(self, uri=uri, qs=qs)
            if self.success:
                response = self.response['body'] if 'body' in self.response else self.response
                longitude = response['lon']
                latitude = response['lat']
                country = response['country']

                # Get the state
                uri = 'https://api.openweathermap.org/geo/1.0/reverse'
                qs = {
                    'lat': latitude,
                    'lon': longitude,
                    'appid': self.openweathermap_key,
                }
                request.get(self, uri=uri, qs=qs)
                if self.success:
                    response = self.response['body'] if 'body' in self.response else self.response
                    state = response[0]['state']

                uri = 'https://api.openweathermap.org/data/2.5/weather'
                qs = {
                    'lat': latitude,
                    'lon': longitude,
                    'units': 'imperial',
                    'appid': self.openweathermap_key,
                }
                request.get(self, uri=uri, qs=qs)
                if self.success:
                    response = self.response['body'] if 'body' in self.response else self.response
                    # Put error checking in all of this!!!!!
                    command.success = True
                    city = response['name']
                    current_f = response['main']['temp']
                    current_c = utils.farenheit_to_celsius(current_f)
                    feels_like_f = response['main']['feels_like']
                    feels_like_c = utils.farenheit_to_celsius(feels_like_f)
                    humidity = response['main']['humidity']
                    current_condition = response['weather'][0]['description'].title()
                    min_f = response['main']['temp_min']
                    min_c = utils.farenheit_to_celsius(min_f)
                    max_f = response['main']['temp_max']
                    max_c = utils.farenheit_to_celsius(max_f)
                    wind_speed = response['wind']['speed']
                    wind_degrees = response['wind']['deg']

                    header = []
                    if city:
                        header.append(city)
                    if state:
                        header.append(state)
                    if country:
                        header.append(country)
                    
                    if len(header) == 0:
                        header = [args.loc]

                    command.output.messages.append(f'Current weather for {", ".join(header)}')
                    command.output.messages.append(f'Currently: {current_f}°F ({current_c}°C)')
                    command.output.messages.append(f'Feels like: {feels_like_f}°F ({feels_like_c}°C)')
                    command.output.messages.append(f'Humidity {humidity}%')
                    command.output.messages.append(f'Condition: {current_condition}')
                    command.output.messages.append(f'Low: {min_f}°F ({min_c}°C) | High: {max_f}°F ({max_c}°C)')
                    command.output.messages.append(f'Wind {wind_degrees}° @ {wind_speed} mph')
            else:
                command.output.errors.append(f'Failed to get geolocation data for {args.loc}.')
        else:
            logging.error('Missing openweathermap API key.')
            command.output.errors.append('I am currently unable to perform weather lookups. This error has been logged. Please try again later.')

    def __configure_parsers(self):
        self.apg_parser = argparse.ArgumentParser(add_help=False, prog='apg', description='Generate a series of random passwords.')
        self.apg_parser.add_argument('--length', help='The length of the generated password.', required=False, type=int, default=64)
        self.apg_parser.add_argument('-u', '--uppercase', help='Include uppercase letters in the generated passwords.', required=False, action='store_true')
        self.apg_parser.add_argument('-l', '--lowercase', help='Include lowercase letters in the generated passwords.', required=False, action='store_true')
        self.apg_parser.add_argument('-n', '--numbers', help='Include numbers in the generated passwords.', required=False, action='store_true')
        self.apg_parser.add_argument('-s', '--special', help='Include special characters in the generated passwords.', required=False, action='store_true')
        self.apg_parser.add_argument('-q', '--quantity', help='The number of passwords to generate.', required=False, type=int, default=10)

        self.ball_parser = argparse.ArgumentParser(add_help=False, prog='8ball', description='8ball <question> -- Ask the 8ball a question.')
        self.ball_parser.set_defaults(func=self.ball)

        self.bytes_parser = argparse.ArgumentParser(add_help=False, prog='bytes', description='Perform byte conversions based on input.')
        self.bytes_parser.add_argument('-a', '--amount', help='The amount to convert, without the suffix.', metavar='<int>', required=True, type=int, action='store')
        self.bytes_parser.add_argument('-u', '--unit', help='What to convert from, e.g, MB.', metavar='<str>', choices=['bytes', 'kb', 'mb', 'gb', 'tb', 'pb', 'eb'], required=True, action='store')

        self.calc_parser = argparse.ArgumentParser(add_help=False, prog='calc', description='calc <equation> -- Perform calculations using bc(1).')
        self.calc_parser.set_defaults(func=self.calc)

        self.crypto_parser = argparse.ArgumentParser(add_help=False, prog='crypto', description='Perform crypto currency conversions.')
        self.crypto_parser.add_argument('-a', '--amount', help='The amount to convert, without currency symbol.', metavar='<int>', required=True, type=int)
        self.crypto_parser.add_argument('-f', '--from', help='Currency FROM symbol, e.g., USD.', metavar='<code>', required=True, action='store')
        self.crypto_parser.add_argument('-t', '--to', help='Currency TO symbol, e.g., GBP.', metavar='<code>', required=True, action='store')

        self.currency_parser = argparse.ArgumentParser(add_help=False, prog='currency', description='Perform physical currency conversions.')
        self.currency_parser.add_argument('-a', '--amount', help='The amount to convert, without currency symbol.', metavar='<int>', required=True, type=int)
        self.currency_parser.add_argument('-f', '--from', help='Currency FROM symbol, e.g., USD.', metavar='<code>', required=True, action='store')
        self.currency_parser.add_argument('-t', '--to', help='Currency TO symbol, e.g., USD.', metavar='<code>', required=True, action='store')

        self.dict_parser = argparse.ArgumentParser(add_help=False, prog='dict', description='Perform dictionary lookups.')
        self.dict_parser.add_argument('-w', '--word', help='The word to look up.', metavar='<word>', required=True, action='store')

        self.quakes_parser = argparse.ArgumentParser(add_help=False, prog='quakes', description='Display earhtquake data from the USGS.')
        self.quakes_parser.add_argument('-l', '--limit', help='The maximum number of events to show.', metavar='<int>', required=False, default=10, action='store', type=int)
        self.quakes_parser.add_argument('-m', '--min', help='The minimum magnitude.', metavar='<int>', required=False, default=1, action='store', type=int)

        self.stocks_parser = argparse.ArgumentParser(add_help=False, prog='stocks', description='Perform stock symbol lookups.')
        self.stocks_parser.add_argument('-s', '--symbol', help='The stock symbol. Can be used more than once.', metavar='<symbol>', required=True, action='append')

        self.tiny_parser = argparse.ArgumentParser(add_help=False, prog='tiny', description='Shorten a URL via tinyurl.')
        self.tiny_parser.add_argument('-u', '--url', help='The URL to shorten.', metavar='<url>', required=True, action='store')

        self.units_parser = argparse.ArgumentParser(add_help=False, prog='units', description='A simple unit converter.')
        self.units_parser.add_argument('-a', '--amount', help='The amount to convert.', metavar='<int>', required=True, action='store', type=int)
        self.units_parser.add_argument('-f', '--from', help='The from unit.', metavar='<unit>', required=True, action='store')
        self.units_parser.add_argument('-t', '--to', help='The to unit.', metavar='<unit>', required=True, action='store')

        self.weather_parser = argparse.ArgumentParser(add_help=False, prog='weather', description='Display weather conditions for a given postal code.')
        self.weather_parser.add_argument('-l', '--loc', help='A valid postal code.', metavar='<location>', required=True, action='store')

    def __setup_methods(self):
        return {
            'apg': {
                'description': self.apg_parser.description,
                'usage': self.apg_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'private',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            '8ball': {
                'description': self.ball_parser.description,
                'usage': self.ball_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'method': 'ball',
                'hidden': 0,
                'monospace': 0,
                'split_output': 0,
            },
            'bytes': {
                'description': self.bytes_parser.description,
                'usage': self.bytes_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'calc': {
                'description': self.calc_parser.description,
                'usage': self.calc_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'crypto': {
                'description': self.crypto_parser.description,
                'usage': self.crypto_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'currency': {
                'description': self.currency_parser.description,
                'usage': self.currency_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'dict': {
                'description': self.dict_parser.description,
                'usage': self.dict_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'quakes': {
                'description': self.quakes_parser.description,
                'usage': self.quakes_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 1,
            },
            'stocks': {
                'description': self.stocks_parser.description,
                'usage': self.stocks_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 1,
            },
            'tiny': {
                'description': self.tiny_parser.description,
                'usage': self.tiny_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 1,
                'split_output': 0,
            },
            'units': {
                'description': self.units_parser.description,
                'usage': self.units_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 0,
                'split_output': 0,
            },
            'weather': {
                'description': self.weather_parser.description,
                'usage': self.weather_parser.format_help().rstrip(),
                'is_admin': 0,
                'type': 'all',
                'can_be_disabled': 1,
                'hidden': 0,
                'monospace': 0,
                'split_output': 0,
            },
        }
