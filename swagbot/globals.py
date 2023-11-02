# This file keeps things like the configuration and the plugins global.
import os

def init():
    plugins = {}
    config = {}
    bot = None
    config_root = None
    schedulers = {}
    start_time = 0
    ready_time = 0
