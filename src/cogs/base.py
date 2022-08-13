import re as _re
from typing import List as _List
from typing import Optional as _Optional
from typing import Tuple as _Tuple
from typing import Union as _Union

from discord.ext.commands import Bot as _Bot
from discord.ext.commands import Cog as _Cog
from discord.ext.commands import Context as _Context

from .. import settings as _settings



class CogBase(_Cog):
    COOLDOWN: float = 15.0
    RATE: int = 5

    def __init__(self, bot: _Bot) -> None:
        if not bot:
            raise ValueError('Parameter \'bot\' must not be None.')
        self.__bot = bot


    @property
    def bot(self) -> _Bot:
        return self.__bot


    def _extract_dash_parameters(self, full_arg: str, args: _Optional[_List[str]], *dash_parameters) -> _Tuple[_Union[bool, str], ...]:
        new_arg = full_arg or ''
        if args:
            new_arg += f' {" ".join(args)}'
        result = []

        for dash_parameter in dash_parameters:
            if dash_parameter:
                rx_dash_parameter = ''.join((r'\B', dash_parameter, r'\b'))
                dash_parameter_match = _re.search(rx_dash_parameter, new_arg)
                if dash_parameter_match:
                    remove = ''
                    parameter_pos = dash_parameter_match.span()[0]

                    if '=' in dash_parameter:
                        value_start = parameter_pos + len(dash_parameter)
                        value_end = new_arg.find('--', value_start)
                        if value_end < 0:
                            value_len = len(new_arg) - value_start
                        else:
                            value_len = value_end - value_start - 1
                        value = new_arg[value_start:value_start + value_len]
                        remove = f'{dash_parameter}{value}'
                        result.append(value)
                    else:
                        remove = dash_parameter
                        result.append(True)
                    if parameter_pos > 0:
                        remove = f' {remove}'
                    rx_remove = ''.join((' ', _re.escape(remove), r'\b'))
                    new_arg = _re.sub(rx_remove, '', new_arg).strip()
                else:
                    if '=' in dash_parameter:
                        result.append(None)
                    else:
                        result.append(False)
        return new_arg, *result


    def _log_command_use(self, ctx: _Context):
        if _settings.PRINT_DEBUG_COMMAND:
            print(f'Invoked command: {ctx.message.content}')


    def _log_command_use_error(self, ctx: _Context, err: Exception, force_printing: bool = False):
        if _settings.PRINT_DEBUG_COMMAND or force_printing:
            print(f'Invoked command had an error: {ctx.message.content}')
            if err:
                print(str(err))





class RawCogBase(CogBase):
    COOLDOWN: float = 10.0
    RATE: int = 5