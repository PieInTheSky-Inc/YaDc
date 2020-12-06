import asyncpg
from datetime import datetime
from discord import Embed, Guild, Message, TextChannel
from discord.ext.commands import Bot, Context
from enum import IntEnum
from typing import Any, Callable, Dict, ItemsView, KeysView, List, Tuple, Union, ValuesView

import database as db
import pss_assert
from pss_entity import DEFAULT_DETAIL_PROPERTY_LONG_SEPARATOR
import settings as app_settings
import utils


# ---------- Constants ----------

__AUTODAILY_SETTING_COUNT: int = 9

_COLUMN_NAME_GUILD_ID: str = 'guildid'
_COLUMN_NAME_DAILY_CAN_POST: str = 'dailycanpost'
_COLUMN_NAME_DAILY_CHANNEL_ID: str = 'dailychannelid'
_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: str = 'dailylatestmessageid'
_COLUMN_NAME_USE_PAGINATION: str = 'usepagination'
_COLUMN_NAME_PREFIX: str = 'prefix'
_COLUMN_NAME_DAILY_CHANGE_MODE: str = 'dailychangemode'
_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT: str = 'dailylatestmessagecreatedate'
_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: str = 'dailylatestmessagemodifydate'
_COLUMN_NAME_BOT_NEWS_CHANNEL_ID: str = 'botnewschannelid'
_COLUMN_NAME_USE_EMBEDS: str = 'useembeds'

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

class AutoDailyChangeMode(IntEnum):
    POST_NEW = 1 # Formerly None
    DELETE_AND_POST_NEW = 2 # Formerly True
    EDIT = 3 # Formerly False





class AutoDailySettings():
    def __init__(self, guild: Guild, channel: TextChannel, can_post: bool, latest_message_id: int, change_mode: AutoDailyChangeMode, latest_message_created_at: datetime, latest_message_modified_at: datetime) -> None:
        self.__can_post: bool = can_post
        self.__channel: TextChannel = channel
        self.__change_mode: AutoDailyChangeMode = change_mode or AutoDailyChangeMode.POST_NEW
        self.__guild: Guild = guild
        self.__latest_message_id: int = latest_message_id or None
        self.__latest_message_created_at: datetime = latest_message_created_at or None
        self.__latest_message_modified_at: datetime = latest_message_modified_at or None


    @property
    def can_post(self) -> bool:
        return self.__can_post

    @property
    def change_mode(self) -> AutoDailyChangeMode:
        return self.__change_mode

    @property
    def channel(self) -> TextChannel:
        return self.__channel

    @property
    def channel_id(self) -> int:
        if self.channel:
            return self.channel.id
        else:
            return None

    @property
    def guild(self) -> Guild:
        return self.__guild

    @property
    def guild_id(self) -> int:
        if self.guild:
            return self.guild.id
        else:
            return None

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
            result['autodaily_error'] = 'Auto-posting of the daily announcement is not configured for this server.'
        return result


    def _get_pretty_channel_mention(self) -> str:
        if self.channel is not None:
            channel_name = self.channel.mention
        else:
            channel_name = None
        return channel_name


    def _get_pretty_channel_name(self) -> str:
        if self.channel is not None:
            channel_name = self.channel.name
        else:
            channel_name = '<not set>'
        return channel_name


    def _get_pretty_mode(self) -> str:
        result = __convert_to_edit_delete(self.change_mode)
        return result


    def get_channel_setting(self) -> Dict[str, str]:
        if self.channel:
            result = self.channel.mention
        else:
            result = self._get_pretty_channel_name()
        return {'autodaily_channel': result}


    def get_changemode_setting(self) -> Dict[str, str]:
        result = self._get_pretty_mode()
        return {'autodaily_mode': result}


    async def reset(self) -> bool:
        settings = {
            _COLUMN_NAME_DAILY_CHANNEL_ID: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None,
            _COLUMN_NAME_DAILY_CHANGE_MODE: DEFAULT_AUTODAILY_CHANGE_MODE,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: None
        }
        success = await __db_update_server_settings(self.guild_id, settings)
        if success:
            self.__channel = None
            self.__delete_on_change = None
            self.__latest_message_id = None
            self.__latest_message_created_at = None
            self.__latest_message_modified_at = None
        return success


    async def reset_channel(self) -> bool:
        settings = {
            _COLUMN_NAME_DAILY_CHANNEL_ID: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: None
        }
        success = await __db_update_server_settings(self.guild_id, settings)
        if success:
            self.__channel = None
            self.__latest_message_id = None
            self.__latest_message_created_at = None
            self.__latest_message_modified_at = None
        return success


    async def reset_daily_delete_on_change(self) -> bool:
        settings = {
            _COLUMN_NAME_DAILY_CHANGE_MODE: DEFAULT_AUTODAILY_CHANGE_MODE
        }
        success = await __db_update_server_settings(self.guild_id, settings)
        if success:
            self.__delete_on_change = None
        return success


    async def reset_latest_message(self) -> bool:
        settings = {
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: None
        }
        success = await __db_update_server_settings(self.guild_id, settings)
        if success:
            self.__latest_message_id = None
            self.__latest_message_created_at = None
            self.__latest_message_modified_at = None
        return success


    async def set_channel(self, channel: TextChannel) -> bool:
        if not self.channel_id or channel.id != self.channel_id:
            settings = {
                _COLUMN_NAME_DAILY_CHANNEL_ID: channel.id,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None
            }
            success = await __db_update_server_settings(self.guild_id, settings)
            if success:
                self.__channel = channel
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
                settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID] = message.id
                settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT] = modified_at
                if new_day:
                    settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT] = message.created_at
        else:
            settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID] = None
            settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT] = None
            settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT] = None

        if settings:
            success = await __db_update_server_settings(self.guild_id, settings)
            if success:
                self.__latest_message_id = settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID]
                self.__latest_message_modified_at = settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT]
                if _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT in settings:
                    self.__latest_message_created_at = settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT]
            return success
        else:
            return True


    async def toggle_change_mode(self) -> bool:
        int_value = int(self.change_mode)
        new_value = AutoDailyChangeMode((int_value % 3) + 1)
        settings = {
            _COLUMN_NAME_DAILY_CHANGE_MODE: new_value
        }
        success = await __db_update_server_settings(self.guild_id, settings)
        if success:
            self.__change_mode = new_value
        return success


    async def update(self, channel: TextChannel = None, can_post: bool = None, latest_message: Message = None, change_mode: AutoDailyChangeMode = None, store_now_as_created_at: bool = False) -> bool:
        settings: Dict[str, object] = {}
        update_channel = channel is not None and channel != self.channel
        update_can_post = can_post is not None and can_post != self.can_post
        update_latest_message = (latest_message is None and store_now_as_created_at) or (latest_message is not None and latest_message.id != self.latest_message_id and (latest_message.edited_at or latest_message.created_at) != self.latest_message_modified_at)
        update_change_mode = change_mode is not None and change_mode != self.change_mode
        if update_channel:
            settings[_COLUMN_NAME_DAILY_CHANNEL_ID] = channel.id
        if update_can_post:
            settings[_COLUMN_NAME_DAILY_CAN_POST] = can_post
        if update_latest_message:
            if store_now_as_created_at:
                settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT] = utils.get_utc_now()
            else:
                settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID] = latest_message.id
                settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT] = latest_message.created_at
                settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT] = latest_message.edited_at or latest_message.created_at
        if update_change_mode:
            settings[_COLUMN_NAME_DAILY_CHANGE_MODE] = change_mode
        success = await __db_update_server_settings(self.guild_id, settings)
        if success:
            if update_channel:
                self.__channel = channel
            if update_can_post:
                self.__can_post = settings.get(_COLUMN_NAME_DAILY_CAN_POST)
            if update_latest_message:
                self.__latest_message_id = settings.get(_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID)
                self.__latest_message_created_at = settings.get(_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT)
                self.__latest_message_modified_at = settings.get(_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT)
            if update_change_mode:
                self.__delete_on_change = settings[_COLUMN_NAME_DAILY_CHANGE_MODE]
        return success





class GuildSettings(object):
    def __init__(self, bot: Bot, row: asyncpg.Record) -> None:
        self.__guild_id: int = row.get(_COLUMN_NAME_GUILD_ID)
        self.__prefix: str = row.get(_COLUMN_NAME_PREFIX)
        self.__use_pagination: bool = row.get(_COLUMN_NAME_USE_PAGINATION)
        self.__bot_news_channel_id: int = row.get(_COLUMN_NAME_BOT_NEWS_CHANNEL_ID)
        self.__use_embeds: bool = row.get(_COLUMN_NAME_USE_EMBEDS)

        self.__guild: Guild = None
        self.__bot_news_channel: TextChannel = None

        daily_channel_id = row.get(_COLUMN_NAME_DAILY_CHANNEL_ID)
        can_post_daily = row.get(_COLUMN_NAME_DAILY_CAN_POST)
        daily_latest_message_id = row.get(_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID)
        daily_post_mode = row.get(_COLUMN_NAME_DAILY_CHANGE_MODE)
        daily_latest_message_created_at = row.get(_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT)
        daily_latest_message_modified_at = row.get(_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT)

        try:
            channel = bot.get_channel(daily_channel_id)
        except Exception as error:
            channel = None
            print(f'Could not get channel for id {daily_channel_id}: {error}')
        if channel is None and daily_channel_id is not None:
            print(f'Could not get channel for id {daily_channel_id}')

        try:
            self.__guild = bot.get_guild(self.__guild_id)
        except Exception as error:
            self.__guild = None
            print(f'Could not get guild for id {self.__guild_id}: {error}')
        if self.__guild is None and self.__guild_id is not None:
            print(f'Could not get channel for id {daily_channel_id}')

        try:
            self.__bot_news_channel = bot.get_channel(self.__bot_news_channel_id)
        except Exception as error:
            self.__bot_news_channel = None
            print(f'Could not get channel for id {self.__bot_news_channel_id}: {error}')
        if self.__bot_news_channel is None and self.__bot_news_channel_id is not None:
            print(f'Could not get channel for id {self.__bot_news_channel_id}')

        self.__autodaily_settings: AutoDailySettings = AutoDailySettings(self.__guild, channel, can_post_daily, daily_latest_message_id, daily_post_mode, daily_latest_message_created_at, daily_latest_message_modified_at)


    @property
    def autodaily(self) -> AutoDailySettings:
        return self.__autodaily_settings

    @property
    def bot_news_channel(self) -> TextChannel:
        return self.__bot_news_channel

    @property
    def bot_news_channel_id(self) -> int:
        return self.__bot_news_channel_id

    @property
    def guild(self) -> Guild:
        return self.__guild

    @property
    def id(self) -> int:
        return self.__guild_id

    @property
    def pretty_use_embeds(self) -> str:
        return __convert_to_on_off(self.use_embeds)

    @property
    def pretty_use_pagination(self) -> str:
        return __convert_to_on_off(self.use_pagination)

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


    async def reset(self) -> Tuple[bool, bool, bool, bool, bool]:
        success_autodaily = await self.autodaily.reset()
        success_bot_channel = await self.reset_bot_news_channel()
        success_pagination = await self.reset_use_pagination()
        success_prefix = await self.reset_prefix()
        success_embed = await self.reset_use_embeds()
        return success_autodaily, success_bot_channel, success_pagination, success_prefix, success_embed


    async def reset_bot_news_channel(self) -> bool:
        if self.__bot_news_channel_id:
            settings = {
                _COLUMN_NAME_BOT_NEWS_CHANNEL_ID: None
            }
            success = await __db_update_server_settings(self.__guild_id, settings)
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
            success = await __db_update_server_settings(self.__guild_id, settings)
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
            success = await __db_update_server_settings(self.__guild_id, settings)
            if success:
                self.__use_embeds = None
            return success
        return True


    async def reset_use_pagination(self) -> bool:
        if self.__use_pagination is not None:
            settings = {
                _COLUMN_NAME_USE_PAGINATION: None
            }
            success = await __db_update_server_settings(self.__guild_id, settings)
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
            success = await __db_update_server_settings(self.__guild_id, settings)
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
            success = await __db_update_server_settings(self.__guild_id, settings)
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
            use_embeds = __convert_from_on_off(use_embeds)
        if self.__use_embeds is None or use_embeds != self.__use_embeds:
            settings = {
                _COLUMN_NAME_USE_EMBEDS: use_embeds
            }
            success = await __db_update_server_settings(self.id, settings)
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
            use_pagination = __convert_from_on_off(use_pagination)
        if self.__use_pagination is None or use_pagination != self.__use_pagination:
            settings = {
                _COLUMN_NAME_USE_PAGINATION: use_pagination
            }
            success = await __db_update_server_settings(self.id, settings)
            if success:
                self.__use_pagination = use_pagination
            return success
        return True





class GuildSettingsCollection():
    def __init__(self) -> None:
        self.__data: Dict[int, GuildSettings] = {}


    @property
    def autodaily_settings(self) -> List[AutoDailySettings]:
        return [guild_settings.autodaily for guild_settings in self.__data.values()]

    @property
    def bot_news_channels(self) -> List[TextChannel]:
        return [guild_settings.bot_news_channel for guild_settings in self.__data.values() if guild_settings.bot_news_channel is not None]


    async def create_guild_settings(self, bot: Bot, guild_id: int) -> bool:
        success = await __db_create_server_settings(guild_id)
        if success:
            new_server_settings = await __db_get_server_settings(guild_id)
            if new_server_settings:
                self.__data[guild_id] = GuildSettings(bot, new_server_settings[0])
            else:
                print(f'WARNING: guild settings have been created, but could not be retrieved for guild_id: {guild_id}')
                return False
        return success


    async def delete_guild_settings(self, guild_id: int) -> bool:
        success = await __db_delete_server_settings(guild_id)
        if success and guild_id in self.__data:
            self.__data.pop(guild_id)
        return success


    async def get(self, bot: Bot, guild_id: int) -> GuildSettings:
        if guild_id not in self.__data:
            await self.create_guild_settings(bot, guild_id)
        return self.__data[guild_id]


    async def init(self, bot: Bot) -> None:
        for server_settings in (await __db_get_server_settings()):
            self.__data[server_settings[_COLUMN_NAME_GUILD_ID]] = GuildSettings(bot, server_settings)


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


async def get_autodaily_settings(bot: Bot, guild_id: int = None, can_post: bool = None, no_post_yet: bool = False) -> List[AutoDailySettings]:
    if guild_id:
        autodaily_settings_collection = [(await GUILD_SETTINGS.get(bot, guild_id))]
    else:
        autodaily_settings_collection = [settings for settings in GUILD_SETTINGS.autodaily_settings if settings.channel is not None]
    result = []
    for autodaily_settings in autodaily_settings_collection:
        if not (no_post_yet and autodaily_settings.latest_message_created_at):
            result.append(autodaily_settings)
    return result


async def get_prefix(bot: Bot, message: Message) -> str:
    if utils.discord.is_guild_channel(message.channel):
        guild_settings = await GUILD_SETTINGS.get(bot, message.channel.guild.id)
        result = guild_settings.prefix
    else:
        result = app_settings.DEFAULT_PREFIX
    return result


async def get_prefix_or_default(guild_id: int) -> str:
    result = await __db_get_prefix(guild_id)
    if result is None or result.lower() == 'none':
        result = app_settings.DEFAULT_PREFIX
    return result


async def get_pretty_guild_settings(ctx: Context, full_guild_settings: Dict[str, str], title: str = None, note: str = None) -> Union[List[Embed], List[str]]:
    pretty_guild_settings = __prettify_guild_settings(full_guild_settings)
    if (await get_use_embeds(ctx)):
        fields = [(pretty_setting[0], pretty_setting[1], False) for pretty_setting in pretty_guild_settings]
        colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
        result = [utils.discord.create_embed(title, description=note, fields=fields, colour=colour, icon_url=ctx.guild.icon_url)]
    else:
        result = []
        if title:
            result.append(f'**```{title}```**')
        if note:
            result.append(f'_{note}_')
        result.extend([f'{pretty_setting[0]}{DEFAULT_DETAIL_PROPERTY_LONG_SEPARATOR}{pretty_setting[1]}' for pretty_setting in pretty_guild_settings])
    return result


async def get_use_embeds(ctx: Context, bot: Bot = None, guild: Guild = None) -> bool:
    if (not ctx or not ctx.guild) and (not guild or not bot):
        return app_settings.USE_EMBEDS
    bot = bot or ctx.bot
    guild = guild or ctx.guild
    guild_settings = await GUILD_SETTINGS.get(bot, guild.id)
    return guild_settings.use_embeds


async def reset_prefix(guild_id: int) -> bool:
    success = await __db_reset_prefix(guild_id)
    return success


async def __fix_prefixes() -> bool:
    all_prefixes = await __db_get_server_settings(guild_id=None, setting_names=[_COLUMN_NAME_GUILD_ID, _COLUMN_NAME_PREFIX])
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
    if 'autodaily_error' in guild_settings:
        result.append(('Auto-daily settings', guild_settings['autodaily_error']))
    else:
        if 'autodaily_channel' in guild_settings:
            result.append(('Auto-daily channel', guild_settings['autodaily_channel']))
        if 'autodaily_mode' in guild_settings:
            result.append(('Auto-daily mode', guild_settings['autodaily_mode']))
    if 'bot_news_channel' in guild_settings:
        result.append(('Bot news channel', guild_settings['bot_news_channel']))
    if 'pagination' in guild_settings:
        result.append(('Pagination', guild_settings['pagination']))
    if 'prefix' in guild_settings:
        result.append(('Prefix', guild_settings['prefix']))
    if 'use_embeds' in guild_settings:
        result.append(('Use Embeds', guild_settings['use_embeds']))
    return result


async def __set_prefix(guild_id: int, prefix: str) -> bool:
    await __db_create_server_settings(guild_id)
    success = await __db_update_prefix(guild_id, prefix)
    return success





# ---------- Helper functions ----------


def __convert_from_on_off(switch: str) -> bool:
    if switch is None:
        return None
    else:
        switch = switch.lower()
        if switch in _VALID_BOOL_SWITCH_VALUES.keys():
            result = _VALID_BOOL_SWITCH_VALUES[switch]
            return result
        else:
            return None


def __convert_to_edit_delete(value: AutoDailyChangeMode) -> str:
    if value == AutoDailyChangeMode.DELETE_AND_POST_NEW:
        return 'Delete daily post and post new daily on change.'
    elif value == AutoDailyChangeMode.EDIT:
        return 'Edit daily post on change.'
    elif value == AutoDailyChangeMode.POST_NEW:
        return 'Post new daily on change.'
    else:
        return '<not specified>'


def __convert_to_on_off(value: bool) -> str:
    if value is True:
        return 'ON'
    elif value is False:
        return 'OFF'
    else:
        return '<NOT SET>'





# ---------- DB functions ----------

async def db_get_autodaily_settings(guild_id: int = None, can_post: bool = None, only_guild_ids: bool = False, no_post_yet: bool = False) -> List[Tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any]]:
    wheres = [f'({_COLUMN_NAME_DAILY_CHANNEL_ID} IS NOT NULL)']
    if guild_id is not None:
        wheres.append(utils.database.get_where_string(_COLUMN_NAME_GUILD_ID, column_value=guild_id))
    if can_post is not None:
        wheres.append(utils.database.get_where_string(_COLUMN_NAME_DAILY_CAN_POST, column_value=can_post))
    if no_post_yet is True:
        wheres.append(utils.database.get_where_string(_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT, column_value=None))
    if only_guild_ids:
        setting_names = [_COLUMN_NAME_GUILD_ID]
    else:
        setting_names = [_COLUMN_NAME_GUILD_ID, _COLUMN_NAME_DAILY_CHANNEL_ID, _COLUMN_NAME_DAILY_CAN_POST, _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID, _COLUMN_NAME_DAILY_CHANGE_MODE, _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT, _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT]
    settings = await __db_get_server_settings(guild_id, setting_names=setting_names, additional_wheres=wheres)
    result = []
    for setting in settings:
        if only_guild_ids:
            intermediate = [setting[0]]
            intermediate.extend([None] * (__AUTODAILY_SETTING_COUNT - 1))
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
            intermediate.extend([None] * (__AUTODAILY_SETTING_COUNT - 1))
            result.append(tuple(intermediate))
        else:
            result.append(tuple([None] * __AUTODAILY_SETTING_COUNT))
    return result


async def db_get_daily_channel_id(guild_id: int) -> int:
    setting_names = [_COLUMN_NAME_DAILY_CHANNEL_ID]
    result = await __db_get_server_setting(guild_id, setting_names=setting_names)
    return result[0] or None if result else None


async def db_get_use_pagination(guild: Guild) -> bool:
    if guild:
        setting_names = [_COLUMN_NAME_USE_PAGINATION]
        settings = await __db_get_server_settings(guild.id, setting_names=setting_names)
        if settings:
            for setting in settings:
                result = setting[0]
                if result is None:
                    return True
                return result
    return app_settings.DEFAULT_USE_EMOJI_PAGINATOR


async def __db_create_server_settings(guild_id: int) -> bool:
    if await __db_get_has_settings(guild_id):
        return True
    else:
        query = f'INSERT INTO serversettings ({_COLUMN_NAME_GUILD_ID}, {_COLUMN_NAME_DAILY_CHANGE_MODE}) VALUES ($1, $2)'
        success = await db.try_execute(query, [guild_id, DEFAULT_AUTODAILY_CHANGE_MODE])
        return success


async def __db_delete_server_settings(guild_id: int) -> bool:
    query = f'DELETE FROM serversettings WHERE {_COLUMN_NAME_GUILD_ID} = $1'
    success = await db.try_execute(query, [guild_id])
    return success


async def __db_get_has_settings(guild_id: int) -> bool:
    results = await __db_get_server_settings(guild_id)
    if results:
        return True
    else:
        return False


async def __db_get_prefix(guild_id: int) -> str:
    await __db_create_server_settings(guild_id)
    setting_names = [_COLUMN_NAME_PREFIX]
    result = await __db_get_server_setting(guild_id, setting_names=setting_names)
    return result[0] or None


async def __db_get_server_setting(guild_id: int = None, setting_names: list = None, additional_wheres: list = None, conversion_functions: List[Callable[[object], object]] = None) -> object:
    settings = await __db_get_server_settings(guild_id, setting_names=setting_names, additional_wheres=additional_wheres)
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


async def __db_get_server_settings(guild_id: int = None, setting_names: list = None, additional_wheres: list = None) -> List[asyncpg.Record]:
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


async def __db_reset_prefix(guild_id: int) -> bool:
    current_prefix = await __db_get_prefix(guild_id)
    if current_prefix is not None:
        settings = {
            _COLUMN_NAME_PREFIX: None
        }
        success = await __db_update_server_settings(guild_id, settings)
        return success
    return True


async def __db_update_prefix(guild_id: int, prefix: str) -> bool:
    current_prefix = await __db_get_prefix(guild_id)
    if not current_prefix or prefix != current_prefix:
        settings = {
            _COLUMN_NAME_PREFIX: prefix
        }
        success = await __db_update_server_settings(guild_id, settings)
        return success
    return True


async def __db_update_server_settings(guild_id: int, settings: Dict[str, Any]) -> bool:
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





# ---------- Initialization & DEFAULT ----------

DEFAULT_AUTODAILY_CHANGE_MODE: AutoDailyChangeMode = AutoDailyChangeMode.POST_NEW

GUILD_SETTINGS: GuildSettingsCollection = GuildSettingsCollection()





async def init(bot: Bot) -> None:
    await __fix_prefixes()
    await GUILD_SETTINGS.init(bot)