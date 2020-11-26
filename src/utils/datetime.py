from calendar import month_abbr as _month_abbr
from calendar import month_name as _month_name
from datetime import date as _date
from datetime import datetime as _datetime
from datetime import timedelta as _timedelta
from datetime import timezone as _timezone

from . import constants as _constants
from . import formatting as _formatting


# ---------- Constants ----------

HISTORIC_DATA_NOTE = 'This is historic data from'

MONTH_NAME_TO_NUMBER = {v.lower(): k for k, v in enumerate(_month_name) if k > 0}
MONTH_SHORT_NAME_TO_NUMBER = {v.lower(): k for k, v in enumerate(_month_abbr) if k > 0}

FIFTEEN_HOURS: _timedelta = _timedelta(hours=15)
FIVE_MINUTES: _timedelta = _timedelta(minutes=5)
ONE_DAY: _timedelta = _timedelta(days=1)
ONE_SECOND: _timedelta = _timedelta(seconds=1)
ONE_WEEK: _timedelta = _timedelta(days=7)


# ---------- Functions ----------

def get_first_of_following_month(utc_now: _datetime) -> _datetime:
    year = utc_now.year
    month = utc_now.month + 1
    if (month == 13):
        year += 1
        month = 1
    result = _datetime(year, month, 1, 0, 0, 0, 0, _timezone.utc)
    return result


def get_first_of_next_month(utc_now: _datetime = None) -> _datetime:
    if utc_now is None:
        utc_now = get_utc_now()
    return get_first_of_following_month(utc_now)


def get_historic_data_note(dt: _datetime) -> str:
    if dt is not None:
        timestamp = _formatting.datetime(dt)
        result = f'{HISTORIC_DATA_NOTE}: {timestamp}'
        return result
    else:
        return None


def get_month_name(dt: _datetime) -> str:
    result = _month_name[dt.month]
    return result


def get_month_short_name(dt: _datetime) -> str:
    result = _month_abbr[dt.month]
    return result


def get_month_from_name(month_name: str) -> int:
    return MONTH_NAME_TO_NUMBER.get(month_name)


def get_month_from_short_name(month_short_name: str) -> int:
    return MONTH_SHORT_NAME_TO_NUMBER.get(month_short_name)


def get_next_day(utc_now: _datetime = None) -> _datetime:
    utc_now = utc_now or get_utc_now()
    result = _datetime(utc_now.year, utc_now.month, utc_now.day, tzinfo=_timezone.utc)
    result = result + _constants.ONE_DAY
    return result


def get_seconds_to_wait(interval_length: int, utc_now: _datetime = None) -> float:
    """
    interval_length: length of interval to wait in minutes
    """
    interval_length = float(interval_length)
    if utc_now is None:
        utc_now = get_utc_now()
    result = (interval_length * 60.0) - ((float(utc_now.minute) % interval_length) * 60.0) - float(utc_now.second) - float(utc_now.microsecond) / 1000000.0
    return result


def get_star_date(utc_now: _datetime) -> int:
    today = _date(utc_now.year, utc_now.month, utc_now.day)
    return (today - _constants.PSS_START_DATE).days


def get_utc_now() -> _datetime:
    return _datetime.now(_timezone.utc)


def is_valid_month(month: str) -> bool:
    result = month and (month in MONTH_NAME_TO_NUMBER or month in MONTH_SHORT_NAME_TO_NUMBER)
    if not result:
        try:
            month = int(month)
            result = month >= 1 and month <= 12
        except (TypeError, ValueError):
            pass
    return result