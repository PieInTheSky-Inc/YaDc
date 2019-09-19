MIN_ENTITY_NAME_LENGTH = 3

def valid_entity_name(name: str, min_length: int = MIN_ENTITY_NAME_LENGTH, allowed_values: list = [], case_sensitive: bool = False) -> bool:
    if not name:
        return False

    if not case_sensitive:
        name = name.lower()
        allowed_values = [value.lower() for value in allowed_values]

    if len(name) < min_length and not name in allowed_values:
        return False

    return True


def string_in_list(string, lst: list, case_sensitive: bool = True) -> bool:
    if string and lst:
        if not case_sensitive:
            string = string.lower()
            lst = [value.lower() for value in lst]
        return string in lst
    return False
