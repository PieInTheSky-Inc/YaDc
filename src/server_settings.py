import asyncpg
from datetime import datetime
from discord import Embed, Guild, Message, TextChannel
from discord.ext.commands import Bot, Context
from enum import IntEnum
from enum import StrEnum
from typing import Any, Callable, Dict, ItemsView, KeysView, List, Optional, Tuple, Union, ValuesView

from . import database as db
from . import pss_assert
from . import pss_entity as entity
from . import settings as app_settings
from . import utils


# ---------- Enums ----------

class AutoMessageChangeMode(IntEnum):
    POST_NEW = 1 # Formerly None
    DELETE_AND_POST_NEW = 2 # Formerly True
    EDIT = 3 # Formerly False


class AutoMessageType(StrEnum):
    DAILY = 'autodaily'
    TRADER = 'autotrader'


class AutoMessageColumn(StrEnum):
    CHANNEL_ID = 'channel_id'
    CAN_POST = 'can_post'
    LATEST_MESSAGE_ID = 'latest_message_id'
    LATEST_MESSAGE_CREATED_AT = 'latest_message_create_date'
    LATEST_MESSAGE_MODIFIED_AT = 'latest_message_modify_date'
    CHANGE_MODE = 'change_mode'





# ---------- Constants ----------

__AUTOMESSAGE_SETTING_COUNT: int = 7

_COLUMN_NAME_GUILD_ID: str = 'guildid'
_COLUMN_NAME_USE_PAGINATION: str = 'usepagination'
_COLUMN_NAME_PREFIX: str = 'prefix'
_COLUMN_NAME_BOT_NEWS_CHANNEL_ID: str = 'botnewschannelid'
_COLUMN_NAME_USE_EMBEDS: str = 'useembeds'

_COLUMN_NAMES_AUTO_MESSAGE: Dict[AutoMessageColumn, Dict[AutoMessageType, str]] = {
    AutoMessageColumn.CHANNEL_ID: {
        AutoMessageType.DAILY: 'dailychannelid',
        AutoMessageType.TRADER: 'traderchannelid',
    },
    AutoMessageColumn.CAN_POST: {
        AutoMessageType.DAILY: 'dailycanpost',
        AutoMessageType.TRADER: 'tradercanpost',
    },
    AutoMessageColumn.LATEST_MESSAGE_ID: {
        AutoMessageType.DAILY: 'dailylatestmessageid',
        AutoMessageType.TRADER: 'traderlatestmessageid',
    },
    AutoMessageColumn.LATEST_MESSAGE_CREATED_AT: {
        AutoMessageType.DAILY: 'dailylatestmessagecreatedate',
        AutoMessageType.TRADER: 'traderlatestmessagecreatedate',
    },
    AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT: {
        AutoMessageType.DAILY: 'dailylatestmessagemodifydate',
        AutoMessageType.TRADER: 'traderlatestmessagemodifydate',
    },
    AutoMessageColumn.CHANGE_MODE: {
        AutoMessageType.DAILY: 'dailychangemode',
        AutoMessageType.TRADER: 'traderchangemode',
    },
}


_AUTO_MESSAGE_DEFAULT_CHANGE_MODE: Dict[AutoMessageType, AutoMessageChangeMode] = {
    AutoMessageType.DAILY: AutoMessageChangeMode.EDIT,
    AutoMessageType.TRADER: AutoMessageChangeMode.POST_NEW,
}


_ERROR_MESSAGES: Dict[str, Dict[AutoMessageType, str]] = {
    'not_configured': {
        AutoMessageType.DAILY: 'Auto-posting of the daily announcement is not configured for this server.',
        AutoMessageType.TRADER: 'Auto-posting of the trader offerings is not configured for this server.',
    }
}

_VALID_BOOL_SWITCH_VALUES: Dict[str, bool] = {
    'on': True,
    'true': True,
    '1': True,
    'yes': True,
    '👍': True,
    'off': False,
    'false': False,
    '0': False,
    'no': False,
    '👎': False
}





# ---------- Classes ----------

class AutoMessageSettings():
    def __init__(self, bot: Bot, guild_id: int, daily_channel_id: int, can_post: bool, latest_message_id: int, change_mode: AutoMessageChangeMode, latest_message_created_at: datetime, latest_message_modified_at: datetime, auto_message_type: AutoMessageType) -> None:
        self.__bot: Bot = bot
        self.__can_post: bool = can_post
        self.__channel_id: int = daily_channel_id
        self.__channel: TextChannel = None
        self.__change_mode: AutoMessageChangeMode = change_mode or AutoMessageChangeMode.POST_NEW
        self.__guild: Guild = None
        self.__guild_id: int = guild_id
        self.__latest_message_id: int = latest_message_id or None
        self.__latest_message_created_at: datetime = latest_message_created_at or None
        self.__latest_message_modified_at: datetime = latest_message_modified_at or None
        self.__auto_message_type: AutoMessageType = auto_message_type


    @property
    def bot(self) -> Bot:
        return self.__bot

    @property
    def can_post(self) -> bool:
        return self.__can_post

    @property
    def change_mode(self) -> AutoMessageChangeMode:
        return self.__change_mode

    @property
    def channel(self) -> TextChannel:
        if self.__channel is None:
            try:
                self.__channel = self.__bot.get_channel(self.channel_id)
            except Exception as error:
                self.__channel = None
                print(f'Could not get channel for id {self.channel_id}: {error}')
            if self.__channel is None and self.channel_id is not None:
                utils.dbg_prnt(f'Could not get channel for id {self.channel_id}')
        return self.__channel

    @property
    def channel_id(self) -> int:
        return self.__channel_id

    @property
    def guild(self) -> Guild:
        if self.__guild is None:
            try:
                self.__guild = self.bot.get_guild(self.guild_id)
            except Exception as error:
                self.__guild = None
                print(f'Could not get guild for id {self.guild_id}: {error}')
            if self.__guild is None and self.guild_id is not None:
                utils.dbg_prnt(f'Could not get guild for id {self.guild_id}')
        return self.__guild

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    @property
    def no_post_yet(self) -> bool:
        return self.channel_id and self.latest_message_created_at is None

    @property
    def latest_message_id(self) -> int:
        return self.__latest_message_id

    @property
    def latest_message_created_at(self) -> datetime:
        return self.__latest_message_created_at

    @property
    def latest_message_modified_at(self) -> datetime:
        return self.__latest_message_modified_at


    def get_full_settings(self) -> Dict[str, str]:
        result = {}
        if self.channel_id is not None:
            result.update(self.get_channel_setting())
            result.update(self.get_changemode_setting())
        else:
            result[f'{self.__auto_message_type}_error'] = _ERROR_MESSAGES['not_configured'][self.__auto_message_type]
        return result


    def _get_pretty_channel_mention(self) -> Optional[str]:
        if self.channel is not None:
            result = self.channel.mention
        else:
            result = None
        return result


    def _get_pretty_channel_name(self) -> str:
        if self.channel is not None:
            result = self.channel.name
        else:
            result = '<not set>'
        return result


    def _get_pretty_mode(self) -> str:
        result = _convert_to_edit_delete(self.change_mode)
        return result


    def get_channel_setting(self) -> Dict[str, str]:
        if self.channel is not None:
            result = self.channel.mention
        else:
            result = self._get_pretty_channel_name()
        return {f'{self.__auto_message_type}_channel': result}


    def get_changemode_setting(self) -> Dict[str, str]:
        result = self._get_pretty_mode()
        return {f'{self.__auto_message_type}_mode': result}


    async def reset(self) -> bool:
        settings = {
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANNEL_ID][self.__auto_message_type]: None,
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][self.__auto_message_type]: None,
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANGE_MODE][self.__auto_message_type]: _AUTO_MESSAGE_DEFAULT_CHANGE_MODE[self.__auto_message_type],
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][self.__auto_message_type]: None,
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][self.__auto_message_type]: None,
        }
        success = await db_update_server_settings(self.guild_id, settings)
        if success:
            self.__channel = None
            self.__channel_id = None
            self.__change_mode = _AUTO_MESSAGE_DEFAULT_CHANGE_MODE[self.__auto_message_type]
            self.__delete_on_change = None
            self.__latest_message_id = None
            self.__latest_message_created_at = None
            self.__latest_message_modified_at = None
        return success


    async def reset_channel(self) -> bool:
        settings = {
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANNEL_ID][self.__auto_message_type]: None,
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][self.__auto_message_type]: None,
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][self.__auto_message_type]: None,
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][self.__auto_message_type]: None,
        }
        success = await db_update_server_settings(self.guild_id, settings)
        if success:
            self.__channel = None
            self.__channel_id = None
            self.__latest_message_id = None
            self.__latest_message_created_at = None
            self.__latest_message_modified_at = None
        return success


    async def reset_change_mode(self) -> bool:
        settings = {
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANGE_MODE][self.__auto_message_type]: _AUTO_MESSAGE_DEFAULT_CHANGE_MODE[self.__auto_message_type],
        }
        success = await db_update_server_settings(self.guild_id, settings)
        if success:
            self.__change_mode = _AUTO_MESSAGE_DEFAULT_CHANGE_MODE[self.__auto_message_type]
            self.__delete_on_change = None
        return success


    async def reset_latest_message(self) -> bool:
        settings = {
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][self.__auto_message_type]: None,
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][self.__auto_message_type]: None,
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][self.__auto_message_type]: None,
        }
        success = await db_update_server_settings(self.guild_id, settings)
        if success:
            self.__latest_message_id = None
            self.__latest_message_created_at = None
            self.__latest_message_modified_at = None
        return success


    async def set_channel(self, channel: TextChannel) -> bool:
        if not self.channel_id or channel.id != self.channel_id:
            settings = {
                _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANNEL_ID][self.__auto_message_type]: channel.id,
                _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][self.__auto_message_type]: None,
            }
            success = await db_update_server_settings(self.guild_id, settings)
            if success:
                self.__channel = channel
                self.__channel_id = channel.id
            return success
        return True


    async def set_latest_message(self, message: Message) -> bool:
        settings = {}
        if message:
            new_day = self.latest_message_created_at is None or message.created_at.day != self.latest_message_created_at.day
            if new_day:
                modified_at = message.created_at
            else:
                modified_at = message.edited_at or message.created_at

            if not self.latest_message_id or message.id != self.latest_message_id:
                settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][self.__auto_message_type]] = message.id
                settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][self.__auto_message_type]] = modified_at
                if new_day:
                    settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][self.__auto_message_type]] = message.created_at
        else:
            settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][self.__auto_message_type]] = None
            settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][self.__auto_message_type]] = None
            settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][self.__auto_message_type]] = None

        if settings:
            success = await db_update_server_settings(self.guild_id, settings)
            if success:
                self.__latest_message_id = settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][self.__auto_message_type]]
                self.__latest_message_modified_at = settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][self.__auto_message_type]]
                if _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][self.__auto_message_type] in settings:
                    self.__latest_message_created_at = settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][self.__auto_message_type]]
            return success
        else:
            return True


    async def toggle_change_mode(self) -> bool:
        int_value = int(self.change_mode)
        new_value = AutoMessageChangeMode((int_value % 3) + 1)
        settings = {
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANGE_MODE][self.__auto_message_type]: new_value
        }
        success = await db_update_server_settings(self.guild_id, settings)
        if success:
            self.__change_mode = new_value
        return success


    async def update(self, channel: TextChannel = None, can_post: bool = None, latest_message: Message = None, change_mode: AutoMessageChangeMode = None, store_now_as_created_at: bool = False) -> bool:
        settings: Dict[str, object] = {}
        update_channel = channel is not None and channel != self.channel
        update_can_post = can_post is not None and can_post != self.can_post
        update_latest_message = (latest_message is None and store_now_as_created_at) or (latest_message is not None and latest_message.id != self.latest_message_id and (latest_message.edited_at or latest_message.created_at) != self.latest_message_modified_at)
        update_change_mode = change_mode is not None and change_mode != self.change_mode
        if update_channel:
            settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANNEL_ID][self.__auto_message_type]] = channel.id
        if update_can_post:
            settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CAN_POST][self.__auto_message_type]] = can_post
        if update_latest_message:
            if store_now_as_created_at:
                settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][self.__auto_message_type]] = utils.get_utc_now()
            else:
                settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][self.__auto_message_type]] = latest_message.id
                settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][self.__auto_message_type]] = latest_message.created_at
                settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][self.__auto_message_type]] = latest_message.edited_at or latest_message.created_at
        if update_change_mode:
            settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANGE_MODE][self.__auto_message_type]] = change_mode
        success = await db_update_server_settings(self.guild_id, settings)
        if success:
            if update_channel:
                self.__channel = channel
                self.__channel_id = channel.id
            if update_can_post:
                self.__can_post = settings.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CAN_POST][self.__auto_message_type])
            if update_latest_message:
                self.__latest_message_id = settings.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][self.__auto_message_type])
                self.__latest_message_created_at = settings.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][self.__auto_message_type])
                self.__latest_message_modified_at = settings.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][self.__auto_message_type])
            if update_change_mode:
                self.__delete_on_change = settings[_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANGE_MODE][self.__auto_message_type]]
        return success





class GuildSettings(object):
    def __init__(self, bot: Bot, row: asyncpg.Record) -> None:
        self.__bot = bot
        self.__guild_id: int = row.get(_COLUMN_NAME_GUILD_ID)
        self.__prefix: str = row.get(_COLUMN_NAME_PREFIX)
        self.__use_pagination: bool = row.get(_COLUMN_NAME_USE_PAGINATION)
        self.__bot_news_channel_id: int = row.get(_COLUMN_NAME_BOT_NEWS_CHANNEL_ID)
        self.__use_embeds: bool = row.get(_COLUMN_NAME_USE_EMBEDS)

        self.__guild: Guild = None
        self.__bot_news_channel: TextChannel = None

        self.__autodaily_settings: AutoMessageSettings = AutoMessageSettings(
            self.__bot,
            self.__guild_id,
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANNEL_ID][AutoMessageType.DAILY]),
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CAN_POST][AutoMessageType.DAILY]),
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][AutoMessageType.DAILY]),
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANGE_MODE][AutoMessageType.DAILY]),
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][AutoMessageType.DAILY]),
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][AutoMessageType.DAILY]),
            AutoMessageType.DAILY,
        )

        self.__autotrader_settings: AutoMessageSettings = AutoMessageSettings(
            self.__bot,
            self.__guild_id,
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANNEL_ID][AutoMessageType.TRADER]),
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CAN_POST][AutoMessageType.TRADER]),
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][AutoMessageType.TRADER]),
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANGE_MODE][AutoMessageType.TRADER]),
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][AutoMessageType.TRADER]),
            row.get(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][AutoMessageType.TRADER]),
            AutoMessageType.TRADER,
        )


    @property
    def autodaily(self) -> AutoMessageSettings:
        return self.__autodaily_settings

    @property
    def autotrader(self) -> AutoMessageSettings:
        return self.__autotrader_settings

    @property
    def bot(self) -> Bot:
        return self.__bot

    @property
    def bot_news_channel(self) -> TextChannel:
        if not self.__bot_news_channel:
            try:
                self.__bot_news_channel = self.__bot.get_channel(self.bot_news_channel_id)
            except Exception as error:
                self.__bot_news_channel = None
                print(f'Could not get channel for id {self.bot_news_channel_id}: {error}')
            if self.__bot_news_channel is None and self.bot_news_channel_id is not None:
                utils.dbg_prnt(f'Could not get channel for id {self.bot_news_channel_id}')
        return self.__bot_news_channel

    @property
    def bot_news_channel_id(self) -> int:
        return self.__bot_news_channel_id

    @property
    def guild(self) -> Guild:
        if not self.__guild:
            try:
                self.__guild = self.bot.get_guild(self.id)
            except Exception as error:
                self.__guild = None
                print(f'Could not get guild for id {self.id}: {error}')
            if self.__guild is None and self.id is not None:
                utils.dbg_prnt(f'Could not get guild for id {self.id}')
        return self.__guild

    @property
    def id(self) -> int:
        return self.__guild_id

    @property
    def pretty_use_embeds(self) -> str:
        return _convert_to_on_off(self.use_embeds)

    @property
    def pretty_use_pagination(self) -> str:
        return _convert_to_on_off(self.use_pagination)

    @property
    def prefix(self) -> str:
        return self.__prefix or app_settings.DEFAULT_PREFIX

    @property
    def use_embeds(self) -> bool:
        if self.__use_embeds is None:
            return app_settings.USE_EMBEDS
        else:
            return self.__use_embeds

    @property
    def use_pagination(self) -> bool:
        if self.__use_pagination is None:
            return app_settings.DEFAULT_USE_EMOJI_PAGINATOR
        else:
            return self.__use_pagination


    def get_bot_news_channel_setting(self) -> Dict[str, str]:
        if self.bot_news_channel:
            result = self.bot_news_channel.mention
        else:
            result = '<not configured>'
        return {'bot_news_channel': result}


    def get_full_settings(self) -> Dict[str, str]:
        settings = {}
        settings.update(self.autodaily.get_full_settings())
        settings.update(self.autotrader.get_full_settings())
        settings.update(self.get_bot_news_channel_setting())
        settings.update(self.get_pagination_setting())
        settings.update(self.get_prefix_setting())
        settings.update(self.get_use_embeds_setting())
        return settings


    def get_pagination_setting(self) -> Dict[str, str]:
        return {'pagination': self.pretty_use_pagination}


    def get_prefix_setting(self) -> Dict[str, str]:
        return {'prefix': self.prefix}


    def get_use_embeds_setting(self) -> Dict[str, str]:
        return {'use_embeds': self.pretty_use_embeds}


    async def reset(self) -> Tuple[bool, bool, bool, bool, bool, bool]:
        success_autodaily = await self.autodaily.reset()
        success_autotrader = await self.autotrader.reset()
        success_bot_channel = await self.reset_bot_news_channel()
        success_pagination = await self.reset_use_pagination()
        success_prefix = await self.reset_prefix()
        success_embed = await self.reset_use_embeds()
        return success_autodaily, success_autotrader, success_bot_channel, success_pagination, success_prefix, success_embed


    async def reset_bot_news_channel(self) -> bool:
        if self.__bot_news_channel_id:
            settings = {
                _COLUMN_NAME_BOT_NEWS_CHANNEL_ID: None
            }
            success = await db_update_server_settings(self.__guild_id, settings)
            if success:
                self.__bot_news_channel_id = None
                self.__bot_news_channel = None
            return success
        else:
            return True


    async def reset_prefix(self) -> bool:
        if self.__prefix:
            settings = {
                _COLUMN_NAME_PREFIX: None
            }
            success = await db_update_server_settings(self.__guild_id, settings)
            if success:
                self.__prefix = None
            return success
        else:
            return True


    async def reset_use_embeds(self) -> bool:
        if self.__use_embeds is not None:
            settings = {
                _COLUMN_NAME_USE_EMBEDS: None
            }
            success = await db_update_server_settings(self.__guild_id, settings)
            if success:
                self.__use_embeds = None
            return success
        return True


    async def reset_use_pagination(self) -> bool:
        if self.__use_pagination is not None:
            settings = {
                _COLUMN_NAME_USE_PAGINATION: None
            }
            success = await db_update_server_settings(self.__guild_id, settings)
            if success:
                self.__use_pagination = None
            return success
        return True


    async def set_bot_news_channel(self, channel: TextChannel) -> bool:
        if channel is None:
            raise ValueError('You need to provide a text channel mention to this command!')
        if not self.__bot_news_channel_id or self.__bot_news_channel_id != channel.id:
            settings = {
                _COLUMN_NAME_BOT_NEWS_CHANNEL_ID: channel.id
            }
            success = await db_update_server_settings(self.__guild_id, settings)
            if success:
                self.__bot_news_channel_id = channel.id
                self.__bot_news_channel = channel
            return success
        return True


    async def set_prefix(self, prefix: str) -> bool:
        pss_assert.valid_parameter_value(prefix, _COLUMN_NAME_PREFIX, min_length=1)
        if not self.__prefix or prefix != self.__prefix:
            settings = {
                _COLUMN_NAME_PREFIX: prefix
            }
            success = await db_update_server_settings(self.__guild_id, settings)
            if success:
                self.__prefix = prefix
            return success
        return True


    async def set_use_embeds(self, use_embeds: bool) -> bool:
        if use_embeds is None:
            if self.__use_embeds is None:
                use_embeds = app_settings.USE_EMBEDS
            else:
                use_embeds = self.__use_embeds
            use_embeds = not use_embeds
        else:
            pss_assert.valid_parameter_value(use_embeds, 'use_embeds', min_length=1, allowed_values=_VALID_BOOL_SWITCH_VALUES.keys(), case_sensitive=False)
            use_embeds = _convert_from_on_off(use_embeds)
        if self.__use_embeds is None or use_embeds != self.__use_embeds:
            settings = {
                _COLUMN_NAME_USE_EMBEDS: use_embeds
            }
            success = await db_update_server_settings(self.id, settings)
            if success:
                self.__use_embeds = use_embeds
            return success
        return True


    async def set_use_pagination(self, use_pagination: bool) -> bool:
        if use_pagination is None:
            if self.__use_pagination is None:
                use_pagination = app_settings.DEFAULT_USE_EMOJI_PAGINATOR
            else:
                use_pagination = self.__use_pagination
            use_pagination = not use_pagination
        else:
            pss_assert.valid_parameter_value(use_pagination, 'use_pagination', min_length=1, allowed_values=_VALID_BOOL_SWITCH_VALUES.keys(), case_sensitive=False)
            use_pagination = _convert_from_on_off(use_pagination)
        if self.__use_pagination is None or use_pagination != self.__use_pagination:
            settings = {
                _COLUMN_NAME_USE_PAGINATION: use_pagination
            }
            success = await db_update_server_settings(self.id, settings)
            if success:
                self.__use_pagination = use_pagination
            return success
        return True





class GuildSettingsCollection():
    def __init__(self) -> None:
        self.__data: Dict[int, GuildSettings] = {}


    @property
    def autodaily_settings(self) -> List[AutoMessageSettings]:
        result = [guild_settings.autodaily for guild_settings in self.__data.values() if guild_settings.autodaily.channel_id is not None]
        return result

    @property
    def autotrader_settings(self) -> List[AutoMessageSettings]:
        result = [guild_settings.autotrader for guild_settings in self.__data.values() if guild_settings.autotrader.channel_id is not None]
        return result

    @property
    def bot_news_channels(self) -> List[TextChannel]:
        result = [guild_settings.bot_news_channel for guild_settings in self.__data.values() if guild_settings.bot_news_channel_id is not None]
        return result


    async def create_guild_settings(self, bot: Bot, guild_id: int) -> bool:
        success = await _db_create_server_settings(guild_id)
        if success:
            new_server_settings = await db_get_server_settings(guild_id)
            if new_server_settings:
                self.__data[guild_id] = GuildSettings(bot, new_server_settings[0])
            else:
                print(f'WARNING: guild settings have been created, but could not be retrieved for guild_id: {guild_id}')
                return False
        return success


    async def delete_guild_settings(self, guild_id: int) -> bool:
        success = await _db_delete_server_settings(guild_id)
        if success and guild_id in self.__data:
            self.__data.pop(guild_id)
        return success


    async def get(self, bot: Bot, guild_id: int) -> GuildSettings:
        if guild_id not in self.__data:
            await self.create_guild_settings(bot, guild_id)
        return self.__data[guild_id]


    async def init(self, bot: Bot) -> None:
        rows = await db_get_server_settings()
        for row in rows:
            guild_id = row.get(_COLUMN_NAME_GUILD_ID)
            if guild_id:
                self.__data[guild_id] = GuildSettings(bot, row)
            else:
                print(f'[GuildSettingsCollection.init(Bot)] Found guild settings without guildid: {row}')


    def items(self) -> ItemsView[int, GuildSettings]:
        return self.__data.items()


    def keys(self) -> KeysView[int]:
        return self.__data.keys()


    def values(self) -> ValuesView[GuildSettings]:
        return self.__data.values()





# ---------- Server settings ----------

async def clean_up_invalid_server_settings(bot: Bot) -> None:
    """
    Removes server settings for all guilds the bot is not part of anymore.
    """
    if GUILD_SETTINGS is None:
        raise Exception(f'The guild settings have not been initialized, yet!')

    current_guilds = bot.guilds
    invalid_guild_ids = [guild_settings.id for guild_settings in GUILD_SETTINGS.values() if guild_settings.guild is None or guild_settings.guild not in current_guilds]
    for invalid_guild_id in invalid_guild_ids:
        await GUILD_SETTINGS.delete_guild_settings(invalid_guild_id)


async def get_autodaily_settings_legacy(bot: Bot, utc_now: datetime, guild_id: int = None, can_post: bool = None, no_post_yet: bool = False) -> List[AutoMessageSettings]:
    if guild_id:
        autodaily_settings = await GUILD_SETTINGS.get(bot, guild_id)
        return [autodaily_settings]

    result = []
    for autodaily_settings in GUILD_SETTINGS.autodaily_settings:
        if autodaily_settings.channel is not None and (not autodaily_settings.latest_message_modified_at or (not no_post_yet and autodaily_settings.latest_message_modified_at.date != utc_now.date)):
            result.append(autodaily_settings)
    return result


async def get_autodaily_settings(utc_now: datetime = None, bot: Bot = None, guild_id: int = None, can_post: bool = None, no_post_yet: bool = False) -> List[AutoMessageSettings]:
    if guild_id:
        if not bot:
            raise ValueError('You need to provide the bot, when specifying the guild_id.')
        autodaily_settings = await get_autodaily_settings_for_guild(bot, guild_id)
        return [autodaily_settings]

    result = [autodaily_settings for autodaily_settings in GUILD_SETTINGS.autodaily_settings if autodaily_settings.channel_id]
    utils.dbg_prnt(f'[get_autodaily_settings] retrieved auto-daily settings for {len(result)} guilds')
    if no_post_yet:
        return await get_autodaily_settings_without_post(result)

    if utc_now:
        result = [autodaily_settings for autodaily_settings in result if not autodaily_settings.latest_message_created_at or autodaily_settings.latest_message_created_at.date != utc_now.date]
    return result


async def get_autodaily_settings_for_guild(bot: Bot, guild_id: int) -> AutoMessageSettings:
    autodaily_settings = await GUILD_SETTINGS.get(bot, guild_id)
    return autodaily_settings


async def get_autodaily_settings_without_post(autodaily_settings: List[AutoMessageSettings]) -> List[AutoMessageSettings]:
    if autodaily_settings is None:
        autodaily_settings = GUILD_SETTINGS.autodaily_settings

    result = [autodaily_settings for autodaily_settings in autodaily_settings if autodaily_settings.no_post_yet]
    utils.dbg_prnt(f'[get_autodaily_settings_without_post] retrieved auto-daily settings for {len(result)} guilds, without a post yet.')
    return result


async def get_autotrader_settings(utc_now: datetime = None, bot: Bot = None, guild_id: int = None, can_post: bool = None, no_post_yet: bool = False) -> List[AutoMessageSettings]:
    if guild_id:
        if not bot:
            raise ValueError('You need to provide the bot, when specifying the guild_id.')
        autotrader_settings = await get_autotrader_settings_for_guild(bot, guild_id)
        return [autotrader_settings]

    result = [autotrader_settings for autotrader_settings in GUILD_SETTINGS.autotrader_settings if autotrader_settings.channel_id]
    utils.dbg_prnt(f'[get_autotrader_settings] retrieved auto-trader settings for {len(result)} guilds')
    if no_post_yet:
        return await get_autotrader_settings_without_post(result)

    if utc_now:
        result = [autotrader_settings for autotrader_settings in result if not autotrader_settings.latest_message_created_at or autotrader_settings.latest_message_created_at.date != utc_now.date]
    return result


async def get_autotrader_settings_for_guild(bot: Bot, guild_id: int) -> AutoMessageSettings:
    autotrader_settings = await GUILD_SETTINGS.get(bot, guild_id)
    return autotrader_settings


async def get_autotrader_settings_without_post(autotrader_settings: List[AutoMessageSettings]) -> List[AutoMessageSettings]:
    if autotrader_settings is None:
        autotrader_settings = GUILD_SETTINGS.autotrader_settings

    result = [autotrader_settings for autotrader_settings in autotrader_settings if autotrader_settings.no_post_yet]
    utils.dbg_prnt(f'[get_autotrader_settings_without_post] retrieved auto-trader settings for {len(result)} guilds, without a post yet.')
    return result


async def get_prefix(bot: Bot, message: Message) -> str:
    if utils.discord.is_guild_channel(message.channel):
        guild_settings = await GUILD_SETTINGS.get(bot, message.channel.guild.id)
        result = guild_settings.prefix
    else:
        result = app_settings.DEFAULT_PREFIX
    return result


async def get_prefix_or_default(guild_id: int) -> str:
    result = await _db_get_prefix(guild_id)
    if result is None or result.lower() == 'none':
        result = app_settings.DEFAULT_PREFIX
    return result


async def get_pretty_guild_settings(ctx: Context, full_guild_settings: Dict[str, str], title: str = None, note: str = None) -> Union[List[Embed], List[str]]:
    pretty_guild_settings = __prettify_guild_settings(full_guild_settings)
    if (await get_use_embeds(ctx)):
        fields = [(pretty_setting[0], pretty_setting[1], False) for pretty_setting in pretty_guild_settings]
        colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
        icon_url = ctx.guild.icon.url if ctx.guild.icon else None
        result = [utils.discord.create_embed(title, description=note, fields=fields, colour=colour, icon_url=icon_url)]
    else:
        result = []
        if title:
            result.append(f'**```{title}```**')
        if note:
            result.append(f'_{note}_')
        result.extend([f'{pretty_setting[0]}{entity.DEFAULT_DETAIL_PROPERTY_LONG_SEPARATOR}{pretty_setting[1]}' for pretty_setting in pretty_guild_settings])
    return result


async def get_use_embeds(ctx: Context, bot: Bot = None, guild: Guild = None) -> bool:
    if not ctx and (not guild or not bot):
        return app_settings.USE_EMBEDS
    if ctx and not utils.discord.is_guild_channel(ctx.channel):
        return False
    bot = bot or ctx.bot
    guild = guild or ctx.guild
    guild_settings = await GUILD_SETTINGS.get(bot, guild.id)
    return guild_settings.use_embeds


async def reset_prefix(guild_id: int) -> bool:
    success = await _db_reset_prefix(guild_id)
    return success


async def __fix_prefixes() -> bool:
    all_prefixes = await db_get_server_settings(guild_id=None, setting_names=[_COLUMN_NAME_GUILD_ID, _COLUMN_NAME_PREFIX])
    all_success = True
    if all_prefixes:
        for guild_id, prefix in all_prefixes:
            if guild_id and prefix and prefix.startswith(' '):
                new_prefix = prefix.lstrip()
                if new_prefix:
                    print(f'[fix_prefixes] Fixing prefix \'{prefix}\' for guild with id \'{guild_id}\'. New prefix is: \'{new_prefix}\'')
                    success = await __set_prefix(guild_id, new_prefix)
                else:
                    print(f'[fix_prefixes] Fixing prefix \'{prefix}\' for guild with id \'{guild_id}\'. New prefix is: \'{app_settings.DEFAULT_PREFIX}\'')
                    success = await reset_prefix(guild_id)
                if not success:
                    all_success = False
    return all_success


def __prettify_guild_settings(guild_settings: Dict[str, str]) -> List[Tuple[str, str]]:
    result = []
    autodaily_error = guild_settings.get(f'{AutoMessageType.DAILY}_error')
    if autodaily_error:
        result.append(('Auto-daily settings', autodaily_error))
    else:
        autodaily_channel = guild_settings.get(f'{AutoMessageType.DAILY}_channel')
        if autodaily_channel:
            result.append(('Auto-daily channel', autodaily_channel))
        autodaily_mode = guild_settings.get(f'{AutoMessageType.DAILY}_mode')
        if autodaily_mode:
            result.append(('Auto-daily mode', autodaily_mode))

    autotrader_error = guild_settings.get(f'{AutoMessageType.TRADER}_error')
    if autotrader_error:
        result.append(('Auto-trader settings', autotrader_error))
    else:
        autotrader_channel = guild_settings.get(f'{AutoMessageType.TRADER}_channel')
        if autotrader_channel:
            result.append(('Auto-trader channel', autotrader_channel))
        autotrader_mode = guild_settings.get(f'{AutoMessageType.TRADER}_mode')
        if autotrader_mode:
            result.append(('Auto-trader mode', autotrader_mode))

    if 'pagination' in guild_settings:
        result.append(('Pagination', guild_settings['pagination']))
    if 'prefix' in guild_settings:
        result.append(('Prefix', guild_settings['prefix']))
    if 'use_embeds' in guild_settings:
        result.append(('Use Embeds', guild_settings['use_embeds']))
    return result


async def __set_prefix(guild_id: int, prefix: str) -> bool:
    await _db_create_server_settings(guild_id)
    success = await _db_update_prefix(guild_id, prefix)
    return success





# ---------- Helper functions ----------


def _convert_from_on_off(switch: str) -> bool:
    if switch is None:
        return None
    else:
        switch = switch.lower()
        if switch in _VALID_BOOL_SWITCH_VALUES.keys():
            result = _VALID_BOOL_SWITCH_VALUES[switch]
            return result
        else:
            return None


def _convert_to_on_off(value: bool) -> str:
    if value is True:
        return 'ON'
    elif value is False:
        return 'OFF'
    else:
        return '<NOT SET>'


def _convert_to_edit_delete(value: AutoMessageChangeMode) -> str:
    if value == AutoMessageChangeMode.DELETE_AND_POST_NEW:
        return 'Delete current post and post new message on change.'
    elif value == AutoMessageChangeMode.EDIT:
        return 'Edit current post on change.'
    elif value == AutoMessageChangeMode.POST_NEW:
        return 'Post new message on change.'
    else:
        return '<not specified>'





# ---------- DB functions ----------

async def db_get_automessage_settings(auto_message_type: AutoMessageType, guild_id: int = None, can_post: bool = None, only_guild_ids: bool = False, no_post_yet: bool = False) -> List[Tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any]]:
    wheres = [f'({_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANNEL_ID][auto_message_type]} IS NOT NULL)']
    if guild_id is not None:
        wheres.append(utils.database.get_where_string(_COLUMN_NAME_GUILD_ID, column_value=guild_id))
    if can_post is not None:
        wheres.append(utils.database.get_where_string(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CAN_POST][auto_message_type], column_value=can_post))
    if no_post_yet is True:
        wheres.append(utils.database.get_where_string(_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][auto_message_type], column_value=None))
    if only_guild_ids:
        setting_names = [_COLUMN_NAME_GUILD_ID]
    else:
        setting_names = [
            _COLUMN_NAME_GUILD_ID,
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANNEL_ID][auto_message_type],
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CAN_POST][auto_message_type],
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_ID][auto_message_type],
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANGE_MODE][auto_message_type],
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_CREATED_AT][auto_message_type],
            _COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.LATEST_MESSAGE_MODIFIED_AT][auto_message_type],
        ]
    settings = await db_get_server_settings(guild_id, setting_names=setting_names, additional_wheres=wheres)
    result = []
    for setting in settings:
        if only_guild_ids:
            intermediate = [setting[0]]
            intermediate.extend([None] * (__AUTOMESSAGE_SETTING_COUNT - 1))
            result.append(tuple(intermediate))
        else:
            result.append((
                setting[0],
                setting[1],
                setting[2],
                setting[3],
                setting[4],
                setting[5],
                setting[6]
            ))
    if not result:
        if guild_id:
            intermediate = [guild_id]
            intermediate.extend([None] * (__AUTOMESSAGE_SETTING_COUNT - 1))
            result.append(tuple(intermediate))
        else:
            result.append(tuple([None] * __AUTOMESSAGE_SETTING_COUNT))
    return result


async def db_get_automessage_channel_id(auto_message_type: AutoMessageType, guild_id: int) -> int:
    setting_names = [_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANNEL_ID][auto_message_type]]
    result = await _db_get_server_setting(guild_id, setting_names=setting_names)
    return result[0] or None if result else None


async def db_get_server_settings(guild_id: int = None, setting_names: list = None, additional_wheres: list = None) -> List[asyncpg.Record]:
    additional_wheres = additional_wheres or []
    wheres = []
    if guild_id is not None:
        wheres.append(f'{_COLUMN_NAME_GUILD_ID} = $1')

    if setting_names:
        setting_string = ', '.join(setting_names)
    else:
        setting_string = '*'

    if additional_wheres:
        wheres.extend(additional_wheres)

    where = utils.database.get_where_and_string(wheres)
    if where:
        query = f'SELECT {setting_string} FROM serversettings WHERE {where}'
        if guild_id is not None:
            records = await db.fetchall(query, [guild_id])
        else:
            records = await db.fetchall(query)
    else:
        query = f'SELECT {setting_string} FROM serversettings'
        records = await db.fetchall(query)

    return records or []


async def db_get_use_pagination(guild: Guild) -> bool:
    if guild:
        setting_names = [_COLUMN_NAME_USE_PAGINATION]
        settings = await db_get_server_settings(guild.id, setting_names=setting_names)
        if settings:
            for setting in settings:
                result = setting[0]
                if result is None:
                    return True
                return result
    return app_settings.DEFAULT_USE_EMOJI_PAGINATOR


async def db_update_server_settings(guild_id: int, settings: Dict[str, Any]) -> bool:
    if settings:
        set_names = []
        set_values = [guild_id]
        for i, (key, value) in enumerate(settings.items(), start=2):
            set_names.append(f'{key} = ${i:d}')
            set_values.append(value)
        set_string = ', '.join(set_names)
        query = f'UPDATE serversettings SET {set_string} WHERE {_COLUMN_NAME_GUILD_ID} = $1'
        success = await db.try_execute(query, set_values)
        return success
    else:
        return True


async def _db_create_server_settings(guild_id: int) -> bool:
    if await _db_get_has_settings(guild_id):
        return True
    else:
        query = f'INSERT INTO serversettings ({_COLUMN_NAME_GUILD_ID}, {_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANGE_MODE][AutoMessageType.DAILY]}, {_COLUMN_NAMES_AUTO_MESSAGE[AutoMessageColumn.CHANGE_MODE][AutoMessageType.TRADER]}) VALUES ($1, $2, $3)'
        success = await db.try_execute(query, [guild_id, _AUTO_MESSAGE_DEFAULT_CHANGE_MODE[AutoMessageType.DAILY], _AUTO_MESSAGE_DEFAULT_CHANGE_MODE[AutoMessageType.TRADER]])
        return success


async def _db_delete_server_settings(guild_id: int) -> bool:
    query = f'DELETE FROM serversettings WHERE {_COLUMN_NAME_GUILD_ID} = $1'
    success = await db.try_execute(query, [guild_id])
    return success


async def _db_get_has_settings(guild_id: int) -> bool:
    results = await db_get_server_settings(guild_id)
    if results:
        return True
    else:
        return False


async def _db_get_prefix(guild_id: int) -> Optional[str]:
    await _db_create_server_settings(guild_id)
    setting_names = [_COLUMN_NAME_PREFIX]
    result = await _db_get_server_setting(guild_id, setting_names=setting_names)
    return result[0] or None


async def _db_get_server_setting(guild_id: int = None, setting_names: list = None, additional_wheres: list = None, conversion_functions: List[Callable[[object], object]] = None) -> object:
    settings = await db_get_server_settings(guild_id, setting_names=setting_names, additional_wheres=additional_wheres)
    if settings:
        for setting in settings:
            result = []
            if conversion_functions:
                for i, value in enumerate(setting):
                    result.append(conversion_functions[i](value))
            else:
                result = setting
            if not result:
                result = [None] * len(setting_names)
            return result
    else:
        return None


async def _db_reset_prefix(guild_id: int) -> bool:
    current_prefix = await _db_get_prefix(guild_id)
    if current_prefix is not None:
        settings = {
            _COLUMN_NAME_PREFIX: None
        }
        success = await db_update_server_settings(guild_id, settings)
        return success
    return True


async def _db_update_prefix(guild_id: int, prefix: str) -> bool:
    current_prefix = await _db_get_prefix(guild_id)
    if not current_prefix or prefix != current_prefix:
        settings = {
            _COLUMN_NAME_PREFIX: prefix
        }
        success = await db_update_server_settings(guild_id, settings)
        return success
    return True





# ---------- Initialization & DEFAULT ----------

GUILD_SETTINGS: GuildSettingsCollection = GuildSettingsCollection()





async def init(bot: Bot) -> None:
    await __fix_prefixes()
    await GUILD_SETTINGS.init(bot)
    utils.dbg_prnt(f'Loaded {len(GUILD_SETTINGS.keys())} guild settings with {len(GUILD_SETTINGS.autodaily_settings)} auto-daily and {len(GUILD_SETTINGS.autotrader_settings)} auto-trader settings.')