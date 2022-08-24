from typing import Any, List, Optional

from . import settings


# ---------- Classes -----------

class Error(Exception):
    """Base class for exceptions in this module.

    Attributes:
        msg -- explanation of the error
    """
    def __init__(self, msg: Optional[str] = None) -> None:
        super().__init__()
        self.__msg: str = msg or ''

    @property
    def msg(self) -> str:
        return self.__msg


class InvalidParameterValueError(Error):
    """Exception raised for invalid parameter values."""
    def __init__(self, parameter_name: str = None, invalid_value: Any = None, min_length: int = None, valid_values: List[str] = None, allow_none_or_empty: bool = False) -> None:
        self.__parameter_name: str = parameter_name or '<unknown>'
        self.__invalid_value: str = invalid_value
        self.__min_length: int = min_length if min_length is not None else settings.MIN_ENTITY_NAME_LENGTH
        self.__valid_values: List[str] = valid_values or []
        self.__add_validity_hint: bool = min_length is not None or self.__valid_values
        if allow_none_or_empty:
            self.__valid_values.append('<empty>')
        super().__init__(self.__get_message())


    def __get_message(self) -> str:
        if self.__invalid_value is None:
            result = f'Parameter `{self.__parameter_name}` is mandatory.'
        else:
            result = f'Parameter `{self.__parameter_name}` received invalid value `{self.__invalid_value}`.'
        if self.__add_validity_hint:
            hints = []
            if self.__min_length > 1:
                hints.append(f'have at least {self.__min_length} characters')
            if self.__valid_values:
                hints.append(f'be one of these values: {", ".join(self.__valid_values)}')
            result += f' The value must {" or ".join(hints)}.'
        return result


    def __repr__(self) -> str:
        return self.msg


    def __str__(self) -> str:
        return self.msg


    def __unicode__(self) -> str:
        return self.msg


class MaintenanceError(Error):
    pass


class MissingParameterError(Error):
    pass


class NotFound(Error):
    pass


class ParameterTypeError(TypeError):
    pass


class SelectTimeoutError(Error):
    pass