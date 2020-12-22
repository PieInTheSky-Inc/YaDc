from datetime import datetime as _datetime
from typing import Any as _Any
from typing import List as _List


# ---------- Constants ----------

DB_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'


# ---------- Functions ----------

def convert_boolean(value: bool) -> str:
    """Convert from python bool to postgresql BOOLEAN"""
    if value is True:
        return 'TRUE'
    elif value is False:
        return 'FALSE'
    else:
        return 'NULL'


def convert_text(value: _Any) -> str:
    """Convert from python object to postgresql TEXT"""
    if value is None:
        result = 'NULL'
    elif value:
        result = str(value)
        result = result.replace('\'', '\'\'')
        result = f'\'{result}\''
    else:
        result = ''
    return result


def convert_timestamp(dt: _datetime) -> str:
    """Convert from python datetime to postgresql TIMESTAMPTZ"""
    if dt:
        result = f'TIMESTAMPTZ \'{dt.strftime(DB_TIMESTAMP_FORMAT)}\''
        return result
    else:
        return convert_text(None)


def get_column_definition(column_name: str, column_type: str, is_primary: bool = False, not_null: bool = False, default: _Any = None) -> str:
    modifiers = []
    column_name_txt = column_name.lower()
    column_type_txt = column_type.upper()
    if is_primary:
        modifiers.append('PRIMARY KEY')
    if not_null:
        modifiers.append('NOT NULL')
    if default is not None:
        modifiers.append(f'DEFAULT {default}')
    result = f'{column_name_txt} {column_type_txt}'
    if modifiers:
        result += ' ' + ' '.join(modifiers)
    return result.strip()


def get_where_and_string(where_strings: _List[str]) -> str:
    if where_strings:
        return ' AND '.join(where_strings)
    else:
        return ''


def get_where_or_string(where_strings: _List[str]) -> str:
    if where_strings:
        return ' OR '.join(where_strings)
    else:
        return ''


def get_where_string(column_name: str, column_value: _Any, is_text_type: bool = False) -> str:
    column_name = column_name.lower()
    if column_value is None:
        return f'{column_name} IS NULL'
    if is_text_type:
        column_value = convert_text(column_value)
    return f'{column_name} = {column_value}'