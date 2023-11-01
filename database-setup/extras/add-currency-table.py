#!/usr/bin/env python3

from pprint import pprint
import csv
import logging
import os
import re
import sqlite3
import sys
import time

def dict_factory(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def parse_csv(filename):
    output = []
    with open(filename, newline='') as fh:
        reader = csv.reader(fh, delimiter=',', quotechar='"')
        for row in reader:
            output.append(row)
    return output

def main():
    filename = os.path.join(os.getcwd(), 'physical_currency_list.csv')
    currency_data = parse_csv(filename)

    confdir = os.path.join( os.path.expanduser('~'), '.swagbot' )
    database = os.path.join(confdir, 'swagbot.plugins.extras.db')
    conn = sqlite3.connect(database, check_same_thread=False)
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    for row in currency_data:
        print(row[0])
        insert = 'INSERT INTO currency_conversion (currency_code, currency_name) VALUES(?,?)'
        cursor.execute(insert, (
            row[0],
            row[1],
        ))
        conn.commit()

if __name__ == '__main__':
    main()