import os as _os
import json as _json
import re as _re
from typing import List as _List

from discord import Embed as _Embed
from discord import File as _File
import discord.errors as _errors
from discord.ext.commands import is_owner as _is_owner

from .base import CogBase as _CogBase
from .. import database as _db
from .. import pagination as _pagination
from .. import pss_crew as _crew
from .. import pss_daily as _daily
from .. import pss_dropship as _dropship
from ..pss_exception import Error as _Error
from .. import pss_item as _item
from .. import pss_login as _login
from .. import pss_lookups as _lookups
from .. import pss_research as _research
from .. import pss_room as _room
from .. import pss_training as _training
from .. import server_settings as _server_settings
from .. import settings as _settings
from .. import utils as _utils
from ..yadc_bot import YadcBot as _YadcBot



class OwnerSlashCog(_CogBase, name='Owner slash commands'):
    """
    This module offers commands for the owner of the bot.
    """
    pass





def setup(bot: _YadcBot):
    bot.add_cog(OwnerSlashCog(bot))