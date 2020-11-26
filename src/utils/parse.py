from datetime import datetime as _datetime
from datetime import timezone as _timezone
import pytz as _pytz

from . import constants as _constants


# ---------- Functions ----------

def formatted_datetime(date_time: _datetime, include_tz: bool = True, include_tz_brackets: bool = True) -> _datetime:
    format_string = '%Y-%m-%d %H:%M:%S'
    if include_tz:
        if include_tz_brackets:
            format_string += ' (%Z)'
        else:
            format_string += ' %Z'
    result = _datetime.strptime(date_time, format_string)
    if result.tzinfo is None:
        result = result.replace(tzinfo=_timezone.utc)
    return result


def pss_datetime(pss_datetime: str) -> _datetime:
    result = None
    if pss_datetime:
        try:
            result = _datetime.strptime(pss_datetime, _constants.API_DATETIME_FORMAT_ISO)
        except ValueError:
            result = _datetime.strptime(pss_datetime, _constants.API_DATETIME_FORMAT_ISO_DETAILED)
        result = _pytz.utc.localize(result)
    return result