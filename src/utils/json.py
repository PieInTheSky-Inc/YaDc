from datetime import date as _date
from datetime import datetime as _datetime
import json as _json

from . import format as _format
from . import parse as _parse



# ---------- Classes ----------

class YadcDecoder(_json.JSONDecoder):
    def __init__(self,):
        super().__init__(object_hook=yadc_decoder_object_hook, parse_float=None, parse_int=None, parse_constant=None, strict=True, object_pairs_hook=None)





class YadcEncoder(_json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, _datetime):
            return {
                '__type__': 'datetime',
                '__value__': _format.datetime(obj, include_time=False, include_tz=False, include_tz_brackets=False)
            }
        if isinstance(obj, _date):
            return {
                '__type__': 'date',
                '__value__': _format.datetime(obj, include_time=False, include_tz=False, include_tz_brackets=False)
            }
        return _json.JSONEncoder.default(self, obj)





# ---------- Functions ----------

def yadc_decoder_object_hook(obj):
    if '__type__' in obj and '__value__' in obj:
        if obj['__type__'] in ['date', 'datetime']:
            return _parse.formatted_datetime(obj['__value__'], include_time=False, include_tz=False, include_tz_brackets=False)
    return obj