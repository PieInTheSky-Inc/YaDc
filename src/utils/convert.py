from typing import Any as _Any
from urllib.parse import quote as _quote

from . import formatting as _formatting
from . import parsing as _parsing


# ---------- Functions ----------

def pss_timestamp_to_excel(pss_timestamp: str) -> str:
    if pss_timestamp:
        dt = _parsing.pss_datetime(pss_timestamp)
        result = _formatting.datetime_for_excel(dt)
        return result
    else:
        return ''


def ticks_to_seconds(ticks: int) -> float:
    if ticks:
        ticks = float(ticks)
        return ticks / 40.0
    else:
        return 0.0


def to_boolean(value: _Any, default_if_none: bool = False) -> bool:
    if value is None:
        return default_if_none
    if isinstance(value, str):
        try:
            value = bool(value)
        except:
            try:
                value = float(value)
            except:
                try:
                    value = int(value)
                except:
                    return len(value) > 0
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    if isinstance(value, float):
        return value > 0.0
    if isinstance(value, (tuple, list, dict, set)):
        return len(value) > 0
    raise NotImplementedError


def url_escape(s: str) -> str:
    if s:
        s = _quote(s, safe=' ')
        s = s.replace(' ', '+')
    return s