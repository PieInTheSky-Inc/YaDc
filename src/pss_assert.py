import sys

import pss_exception
import settings



def valid_entity_name(name: str, parameter_name: str = None, min_length: int = settings.MIN_ENTITY_NAME_LENGTH, allowed_values: list = [], case_sensitive: bool = False, allow_none_or_empty: bool = False):
    if parameter_name is None:
        parameter_name = 'name'
    valid_parameter_value(name, parameter_name, min_length=min_length, allowed_values=allowed_values, case_sensitive=case_sensitive, allow_none_or_empty=allow_none_or_empty)


def valid_parameter_value(value: str, parameter_name: str, min_length: int = -1, allowed_values: list = [], case_sensitive: bool = False, allow_none_or_empty: bool = False):
    if not value:
        if allow_none_or_empty:
            return
        else:
            raise pss_exception.InvalidParameter(parameter_name=parameter_name, invalid_value=value, min_length=min_length, valid_values=allowed_values)

    if allowed_values:
        valids = list(allowed_values)
        if not case_sensitive:
            value = value.lower()
            valids = [value.lower() for value in allowed_values]
    else:
        valids = []

    if len(value) < min_length and not value in valids:
        raise pss_exception.InvalidParameter(parameter_name=parameter_name, invalid_value=value, min_length=min_length, valid_values=allowed_values, allow_none_or_empty=allow_none_or_empty)


def parameter_is_valid_integer(value: object, parameter_name: str, min_value: int = None, max_value: int = None, allow_none: bool = False):
    if value is None:
        if allow_none is True:
            return
        else:
            raise pss_exception.InvalidParameter(parameter_name=parameter_name, invalid_value=value)
    if isinstance(value, int):
        if (min_value is not None and value < min_value) or (max_value is not None and value > max_value):
            raise pss_exception.InvalidParameter(parameter_name=parameter_name, invalid_value=value)
    else:
        raise pss_exception.InvalidParameter(parameter_name=parameter_name, invalid_value=value)


def string_in_list(string, lst: list, case_sensitive: bool = True) -> bool:
    if string and lst:
        if not case_sensitive:
            string = string.lower()
            lst = [value.lower() for value in lst]
        return string in lst
    return False