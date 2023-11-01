#!/usr/bin/env python3

from swagbot.bot import SwagBot
import os
import signal
import swagbot.globals as globals

def signal_handler(sig, frame):
    print('\nCaught SIGINT. Aborting.')
    exit(0)

def main():
    config_file = os.path.expanduser('~/.swagbot/bot.yml')
    debug = False
    globals.bot = SwagBot(
        config_file=config_file,
        debug=debug
    )
    globals.bot.run()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()
