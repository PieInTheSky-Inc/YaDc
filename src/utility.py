from datetime import date, datetime, time, timedelta, timezone

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
    next_first_of_month = datetime(year, month, 1, 0, 0, 0, 0, timezone.utc)
    return next_first_of_month
    

def get_first_of_next_month():
    utcnow = get_utcnow()
    return get_first_of_following_month(utcnow)


def get_formatted_datetime(date_time):
    txt = date_time.strftime('%Y-%m-%d %H:%M:%S')
    return txt


def get_utcnow():
    return datetime.now(timezone.utc)
