import discord.ext.commands as commands
from typing import List

import settings





class Error(commands.CommandError):
    """Base class for exceptions in this module.

    Attributes:
        msg -- explanation of the error
    """
    def __init__(self, value):
        super.__init__(value)
        self.msg = ''


class InvalidParameter(Error):
    """Exception raised for invalid parameters."""
    def __init__(self, parameter_name: str = None, invalid_value = None, min_length: int = None, valid_values: List[str] = None):
        self.__parameter_name: str = parameter_name or '<unknown>'
        self.__invalid_value: str = invalid_value or '<unknown>'
        self.__min_length: int = min_length if min_length is not None else settings.MIN_ENTITY_NAME_LENGTH
        self.__valid_values: List[str] = valid_values or []
        self.__add_validity_hint: bool = min_length is not None or self.__valid_values
        self.msg = self.__get_message()


    def __get_message(self) -> str:
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