from datetime import date, datetime, time, timedelta, timezone

import math
import subprocess


def shell_cmd(cmd):
    result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')


def get_first_of_following_month(utcnow):
    year = utcnow.year
    month = utcnow.month + 1
    if (month == 13):
        year += 1
        month = 1
    result = datetime(year, month, 1, 0, 0, 0, 0, timezone.utc)
    return result
    

def get_first_of_next_month():
    utcnow = get_utcnow()
    return get_first_of_following_month(utcnow)


def get_formatted_datetime(date_time):
    result = date_time.strftime('%Y-%m-%d %H:%M:%S %Z (%z)')
    return result


def get_formatted_timedelta(delta, include_relative_indicator=True):
    total_seconds = delta.total_seconds()
    is_past = total_seconds < 0
    if is_past:
        total_seconds = abs(total_seconds)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    seconds = round(seconds)
    minutes = math.floor(minutes)
    hours = math.floor(hours)
    days = math.floor(days)
    weeks = math.floor(weeks)
    result = ''
    if (weeks > 0):
        result += '{:d}w '.format(weeks)
    result += '{:d}d {:d}h {:d}m {:d}s'.format(days, hours, minutes, seconds)
    if include_relative_indicator:
        if is_past:
            result += ' ago'
        else:
            result = 'in {}'.format(result)
    return result


def get_utcnow():
    return datetime.now(timezone.utc)


#---------- DB utilities ----------
TEXT_COLUMN_TYPES = ['TEXT']

def db_get_column_definition(column_name, column_type, is_primary=False, not_null=False):
    column_name_txt = column_name.upper()
    column_type_txt = column_type.upper()
    is_primary_txt = ''
    not_null_txt = ''
    if is_primary:
        is_primary_txt = ' PRIMARY KEY'
    if not_null:
        not_null_txt = ' NOT NULL'
    result = '{} {}{}{}'.format(column_name_txt, column_type_txt, is_primary_txt, not_null_txt)
    return result


def db_get_where_string(column_name, column_type, column_value):
    column_name = column_name.lower()
    column_type = column_type.upper()
    if column_type in TEXT_COLUMN_TYPES:
        column_value = column_value.replace('\'', '\'\'') # escape single quotes
        column_value = '\'{}\''.format(column_value) # add single quotes around string
    return '{} = {}'.format(column_name, column_value)
