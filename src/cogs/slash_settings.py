from discord import TextChannel as _TextChannel
from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown
import discord.ext.commands.errors as _command_errors

from .base import CogBase as _CogBase
from ..pss_exception import Error as _Error
from .. import settings as _settings
from .. import server_settings as _server_settings
from .. import utils as _utils
from ..yadc_bot import YadcBot as _YadcBot



class SettingsSlashCog(_CogBase, name='Settings'):
    pass





def setup(bot: _YadcBot):
    bot.add_cog(SettingsSlashCog(bot))