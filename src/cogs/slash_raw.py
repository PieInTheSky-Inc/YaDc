from discord.ext.commands import BucketType as _BucketType
from discord.ext.commands import cooldown as _cooldown

from .base import RawCogBase as _RawCogBase
from .. import pss_achievement as _achievement
from .. import pss_ai as _ai
from .. import pss_crew as _crew
from .. import pss_gm as _gm
from .. import pss_item as _item
from .. import pss_mission as _mission
from .. import pss_promo as _promo
from .. import pss_raw as _raw
from .. import pss_research as _research
from .. import pss_room as _room
from .. import pss_ship as _ship
from .. import pss_situation as _situation
from .. import pss_training as _training
from .. import settings as _settings
from ..yadc_bot import YadcBot as _YadcBot



class RawDataSlashCog(_RawCogBase, name='Raw Data'):
    """
    This module offers commands to obtain raw game data.
    """
    pass





def setup(bot: _YadcBot):
    bot.add_cog(RawDataSlashCog(bot))