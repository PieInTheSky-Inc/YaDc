from datetime import datetime as _datetime, timedelta as _timedelta
import math as _math
from typing import Iterable as _Iterable
from typing import Optional as _Optional
from typing import Tuple as _Tuple
from typing import Union as _Union

from . import constants as _constants
from . import lookups as _lookups


# ---------- Functions ----------

def date(date_time: _datetime, include_tz: bool = True, include_tz_brackets: bool = True) -> str:
    result = date_time.strftime('%Y-%m-%d')
    if include_tz:
        tz = date_time.strftime('%Z')
        if include_tz_brackets:
            result += ' ({})'.format(tz)
        else:
            result += ' {}'.format(tz)
    return result


def datetime(date_time: _datetime, include_time: bool = True, include_tz: bool = True, include_tz_brackets: bool = True) -> str:
    output_format = '%Y-%m-%d'
    if include_time:
        output_format += ' %H:%M:%S'
    if include_tz:
        if include_tz_brackets:
            output_format += ' (%Z)'
        else:
            output_format += ' %Z'
    result = date_time.strftime(output_format)
    return result


def datetime_for_excel(dt: _datetime, include_seconds: bool = True) -> _Optional[str]:
    if dt:
        format_str = '%Y-%m-%d %H:%M'
        if include_seconds:
            format_str += ':%S'
        result = dt.strftime(format_str)
        return result
    else:
        return None


def duration(total_seconds: int, include_relative_indicator: bool = True, include_seconds: bool = True, exclude_zeros: bool = False) -> str:
    is_past = total_seconds < 0
    if is_past:
        total_seconds = abs(total_seconds)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    seconds = round(seconds)
    minutes = _math.floor(minutes)
    if not include_seconds:
        minutes += 1
    hours = _math.floor(hours)
    days = _math.floor(days)
    weeks = _math.floor(weeks)
    result_parts = []
    result = ''
    print_weeks = weeks > 0
    print_days = (print_weeks and not exclude_zeros) or days > 0
    print_hours = (print_days and not exclude_zeros) or hours > 0
    print_minutes = (print_hours and not exclude_zeros) or minutes > 0
    if print_weeks:
        result_parts.append(f'{weeks:d}w')
    if print_days:
        result_parts.append(f'{days:d}d')
    if print_hours:
        result_parts.append(f'{hours:d}h')
    if print_minutes:
        result_parts.append(f'{minutes:d}m')
    if not result_parts or (include_seconds and (seconds > 0 or not exclude_zeros)):
        result_parts.append(f'{seconds:d}s')

    result = ' '.join(result_parts)

    if include_relative_indicator:
        if is_past:
            result = f'{result} ago'
        else:
            result = f'in {result}'
    return result


def get_and_list(values: _Iterable[str], emphasis: str = '') -> str:
    result = __get_comma_separated_list_with_separate_last_element(values, 'and', emphasis=emphasis)
    return result


def get_reduced_number(num: float) -> _Tuple[float, str]:
    num = float(num)
    is_negative = num < 0
    if is_negative:
        num = abs(num)

    counter = 0
    while num >= 1000:
        counter += 1
        num /= 1000

    if is_negative:
        num *= -1
    result = float(int(_math.floor(num * 10))) / 10
    return result, _lookups.REDUCE_TOKENS_LOOKUP[counter]


def get_reduced_number_compact(num: int, max_decimal_count: int = _constants.DEFAULT_FLOAT_PRECISION) -> str:
    reduced_num, multiplier = get_reduced_number(num)
    result = f'{number_up_to_decimals(reduced_num, max_decimal_count)}{multiplier}'
    return result


def get_or_list(values: _Iterable[str], emphasis: str = '') -> str:
    result = __get_comma_separated_list_with_separate_last_element(values, 'or', emphasis)
    return result


def number_up_to_decimals(num: float, max_decimal_count: int = _constants.DEFAULT_FLOAT_PRECISION) -> str:
    result = f'{num:0.{max_decimal_count}f}'
    result = result.rstrip('0').rstrip('.')
    return result


def pss_datetime(dt: _datetime) -> str:
    result = dt.strftime(_constants.API_DATETIME_FORMAT_ISO)
    return result


def range_string(min_value: _Union[float, int, str], max_value: _Union[float, int, str]) -> _Optional[str]:
    values = []
    if min_value:
        values.append(str(min_value))
    if max_value:
        values.append(str(max_value))
    return '-'.join(sorted(values))


def ranking(ranking: str) -> str:
    result = str(ranking)
    if result:
        if result.endswith(('4', '5', '6', '7', '8', '9', '0', '11', '12', '13')):
            result += 'th'
        elif result.endswith('1'):
            result += 'st'
        elif result.endswith('2'):
            result += 'nd'
        elif result.endswith('3'):
            result += 'rd'
    return result


def timedelta(delta: _timedelta, include_relative_indicator: bool = True, include_seconds: bool = True) -> str:
    if delta:
        total_seconds = delta.total_seconds()
        return duration(total_seconds, include_relative_indicator=include_relative_indicator, include_seconds=include_seconds)
    else:
        return ''


def __get_comma_separated_list_with_separate_last_element(values: _Iterable[str], last_element_separator: str, emphasis: str = '') -> str:
    if not values:
        return ''
    values = list(values)
    if len(values) == 1:
        return values[0]
    else:
        emphasis = emphasis or ''
        result = ', '.join(values[:-1])
        result += f' {emphasis}{last_element_separator}{emphasis} {values[-1]}'
        return result