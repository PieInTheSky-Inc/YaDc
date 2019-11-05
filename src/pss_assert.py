import pss_exception
import settings



def valid_entity_name(name: str, min_length: int = settings.MIN_ENTITY_NAME_LENGTH, allowed_values: list = [], case_sensitive: bool = False):
    valid_parameter_value(name, parameter_name='name', min_length=min_length, allowed_values=allowed_values, case_sensitive=case_sensitive)


def valid_parameter_value(value: str, parameter_name: str, min_length: int = -1, allowed_values: list = [], case_sensitive: bool = False):
    if not value:
        raise pss_exception.InvalidParameter(parameter_name=parameter_name, invalid_value='<empty>', min_length=min_length, valid_values=allowed_values)

    if allowed_values:
        valids = list(allowed_values)
        if not case_sensitive:
            value = value.lower()
            valids = [value.lower() for value in allowed_values]
    else:
        valids = []

    if len(value) < min_length and not value in valids:
        raise pss_exception.InvalidParameter(parameter_name=parameter_name, invalid_value=value, min_length=min_length, valid_values=allowed_values)


def string_in_list(string, lst: list, case_sensitive: bool = True) -> bool:
    if string and lst:
        if not case_sensitive:
            string = string.lower()
            lst = [value.lower() for value in lst]
        return string in lst
    return False