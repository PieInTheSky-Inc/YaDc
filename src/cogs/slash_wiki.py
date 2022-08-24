import os as _os
from typing import Dict as _Dict
from typing import List as _List
from typing import Tuple as _Tuple

from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import RawCogBase as _RawCogBase
from .. import pss_achievement as _achievement
from .. import pss_ai as _ai
from .. import pss_craft as _craft
from .. import pss_crew as _crew
from ..pss_exception import Error as _Error
from .. import pss_item as _item
from .. import pss_raw as _raw
from .. import pss_research as _research
from .. import pss_room as _room
from .. import pss_ship as _ship
from .. import pss_training as _training
from .. import pss_wiki as _wiki
from .. import settings as _settings
from .. import utils as _utils
from ..yadc_bot import YadcBot as _YadcBot



class WikiSlashCog(_RawCogBase, name='Wiki data'):
    """
    This module offers commands to transform raw game data into data that can be used by fandom wiki Data Modules.
    """
    pass





def setup(bot: _YadcBot):
    bot.add_cog(WikiSlashCog(bot))