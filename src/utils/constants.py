from datetime import date as _date
from datetime import datetime as _datetime


# ---------- Miscellaneous ----------

WIKIA_BASE_ADDRESS = 'https://pixelstarships.fandom.com/wiki/'


# ---------- Defaults ----------

DEFAULT_FLOAT_PRECISION: int = 1


# ---------- Formatting / Parsing ----------

API_DATETIME_FORMAT_ISO: str = '%Y-%m-%dT%H:%M:%S'
API_DATETIME_FORMAT_ISO_DETAILED: str = '%Y-%m-%dT%H:%M:%S.%f'
API_DATETIME_FORMAT_CUSTOM: str = '%d.%m.%y %H:%M'


# ---------- PSS ----------

PSS_START_DATE: _date = _date(year=2016, month=1, day=6)
PSS_START_DATETIME: _datetime = _datetime(year=2016, month=1, day=6)