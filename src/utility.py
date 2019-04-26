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
    print('get_formatted_timedelta({})'.format(delta))
    is_past = delta.total_seconds() < 0
    print('is_past = '.format(is_past))
    days = abs(delta.days)
    seconds = delta.seconds
    weeks = math.floor(days/7)
    result = ''
    if (weeks > 0):
        days = days % 7
        result += '{}w {}d '.format(weeks, days)
    else:
        result += '{}d '.format(days)
    hours = math.floor(seconds/3600)
    seconds = seconds % 3600
    minutes = math.floor(seconds/60)
    seconds = seconds % 60
    result += '{}h {}m {}s'.format(hours, minutes, seconds)
    if include_relative_indicator:
        if is_past:
            result += ' ago'
        else:
            result = 'in {}'.format(result)
    return result


def get_utcnow():
    return datetime.now(timezone.utc)
