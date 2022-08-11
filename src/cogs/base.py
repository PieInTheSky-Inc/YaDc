from discord.ext.commands import Bot as _Bot
from discord.ext.commands import Cog as _Cog
from discord.ext.commands import Context as _Context


from .. import settings as _settings



class BaseCog(_Cog):
    COOLDOWN: float = 15.0
    RATE: int = 5

    def __init__(self, bot: _Bot, pretty_name: str = None) -> None:
        if not bot:
            raise ValueError('Parameter \'bot\' must not be None.')
        self.__bot = bot
        self.__cog_description__


    @property
    def bot(self) -> _Bot:
        return self.__bot


    def _log_command_use(self, ctx: _Context):
        if _settings.PRINT_DEBUG_COMMAND:
            print(f'Invoked command: {ctx.message.content}')


    def _log_command_use_error(self, ctx: _Context, err: Exception, force_printing: bool = False):
        if _settings.PRINT_DEBUG_COMMAND or force_printing:
            print(f'Invoked command had an error: {ctx.message.content}')
            if err:
                print(str(err))