from datetime import date, datetime, time, timedelta, timezone

import discord
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
    result = date_time.strftime('%Y-%m-%d %H:%M:%S (%Z)')
    return result


def get_formatted_date(date_time):
    result = date_time.strftime('%Y-%m-%d (%Z)')
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
    result = datetime.now(timezone.utc)
    return result


async def get_latest_message(from_channel, by_member_id=None, with_content=None, after=None, before=None):
    if from_channel is not None:
        messages = from_channel.history(limit=100, after=after, before=before, older_first=True).flatten()
        for msg in reversed(messages):
            process = not by_member_id or msg.author.id == by_member_id
            if process and msg.content == with_content:
                return msg
    return None      



#---------- DB utilities ----------
DB_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

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


def db_get_where_and_string(where_strings):
    if where_strings:
        result = ''
        for i in range(0, len(where_strings)):
            if i > 0:
                result += ' AND '
            result += where_strings[i]
        return result


def db_get_where_or_string(where_strings):
    if where_strings:
        result = ''
        for i in range(0, len(where_strings)):
            if i > 0:
                result += ' OR '
            result += where_strings[i]
        return result


def db_get_where_string(column_name, column_value, is_text_type=False):
    column_name = column_name.lower()
    if is_text_type:
        column_value = db_convert_text(column_value)
    return '{} = {}'.format(column_name, column_value)


def db_convert_boolean(value):
    if value:
        return 'TRUE'
    else:
        return 'FALSE'
    
def db_convert_text(value):
    if value:
        result = str(value)
        result = result.replace('\'', '\'\'')
        result = '\'{}\''.format(result)
        return result
    else:
        return ''
    
def db_convert_timestamp(datetime):
    if datetime:
        result = 'TIMESTAMPTZ \'{}\''.format(datetime.strftime(DB_TIMESTAMP_FORMAT))
        return result
    else:
        return None

def db_convert_to_boolean(db_boolean):
    if db_boolean is None:
        return None
    db_upper = db_boolean.upper()
    if db_upper == 'TRUE' or db_upper == '1' or db_upper == 'T' or db_upper == 'Y' or db_upper == 'YES':
        return True
    else:
        return False
    
def db_convert_to_datetime(db_timestamp):
    if db_timestamp is None:
        return None
    result = db_timestamp.strptime(DB_TIMESTAMP_FORMAT)
    return result

def db_convert_to_int(db_int):
    if db_int is None:
        return None
    result = int(db_int)
    return result

def db_convert_to_float(db_float):
    if db_float is None:
        return None
    result = float(db_float)
    return result
