from datetime import datetime as _datetime
from datetime import timezone as _timezone
from typing import Dict, List, Tuple
import pytz as _pytz

from . import constants as _constants


# ---------- Constants ----------

__SEPARATORS_AMOUNT_MODIFICATION_LOOKUP: Dict[str, int] = {
    'x': 0,
    '==': 0,
    '>=': 0,
    '<=': 0,
    '>': 1,
    '<': -1
}


# ---------- Functions ----------

def camel_case(s: str) -> List[str]:
    """
    https://www.geeksforgeeks.org/python-split-camelcase-string-to-individual-strings/
    """
    words = [[s[0]]]

    for c in s[1:]:
        if words[-1][-1].islower() and c.isupper():
            words.append(list(c))
        else:
            words[-1].append(c)

    return [''.join(word) for word in words]


def entity_multi_string(multi_str: str, separator: str) -> List[Tuple[str, str, int, str]]:
    """
    Parses an entity string (e.g. from ingredients) and returns a list of:
    - Entity type
    - Entity id
    - Entity amount
    - Amount modifier
    """
    entities_strs = multi_str.split(separator)
    result = [entity_string(entity_str.strip()) for entity_str in entities_strs]
    return result


def entity_string(entity_str: str, default_amount: str = '1', default_type: str = None) -> Tuple[str, str, int, str]:
    """
    Parses an entity string (e.g. from ingredients) and returns:
    - Entity type
    - Entity id
    - Entity amount
    - Amount modifier
    """
    entity_str = entity_str.lower()
    entity_type = entity_str
    if ':' in entity_str:
        entity_type, entity_str = entity_str.split(':')

    entity_id = None
    entity_amount = None
    entity_amount_modifier = None

    for entity_amount_modifier in __SEPARATORS_AMOUNT_MODIFICATION_LOOKUP.keys():
        if entity_amount_modifier in entity_str:
            entity_id, entity_amount = entity_str.split(entity_amount_modifier)
            entity_amount = str(int(entity_amount) + __SEPARATORS_AMOUNT_MODIFICATION_LOOKUP[entity_amount_modifier])
            break
        entity_amount = default_amount
        entity_amount_modifier = None
    if not entity_id:
        entity_id = entity_str
        entity_str = None
    entity_type = entity_type.strip() if entity_type else default_type
    entity_id = entity_id.strip() if entity_id else None
    entity_amount = int(entity_amount.strip()) if entity_amount else None
    if entity_type == entity_str:
        try:
            int(entity_id)
        except:
            entity_type = entity_id
            entity_id = None

    return (entity_type, entity_id, entity_amount, entity_amount_modifier)


def formatted_datetime(date_time: str, include_time: bool = True, include_tz: bool = True, include_tz_brackets: bool = True) -> _datetime:
    format_string = '%Y-%m-%d'
    if include_time:
        format_string += ' %H:%M:%S'
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


def requirement_string(requirement_str: str) -> List[Tuple[str, str, int, str]]:
    """
    Parses an entity string (e.g. from ingredients) and returns a list of:
    - Entity type
    - Entity id
    - Entity amount
    - Amount modifier
    """
    return entity_multi_string(requirement_str, '&&')