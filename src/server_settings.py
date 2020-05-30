import asyncpg
from collections import UserDict
import datetime
import discord
from discord.ext import commands
from enum import IntEnum
from typing import Callable, List, Union

import pss_assert
import pss_core as core
import pss_lookups as lookups
import settings as app_settings
import utility as util


# ---------- Constants ----------

__AUTODAILY_SETTING_COUNT = 9


_VALID_PAGINATION_SWITCH_VALUES = {
    'on': True,
    'true': True,
    '1': True,
    'yes': True,
    'off': False,
    'false': False,
    '0': False,
    'no': False
}


_COLUMN_NAME_GUILD_ID: str = 'guildid'
_COLUMN_NAME_DAILY_CAN_POST: str = 'dailycanpost'
_COLUMN_NAME_DAILY_CHANNEL_ID: str = 'dailychannelid'
_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: str = 'dailylatestmessageid'
_COLUMN_NAME_USE_PAGINATION: str = 'usepagination'
_COLUMN_NAME_PREFIX: str = 'prefix'
_COLUMN_NAME_DAILY_DELETE_ON_CHANGE: str = 'dailydeleteonchange'
_COLUMN_NAME_DAILY_NOTIFY_ID: str = 'dailynotifyid'
_COLUMN_NAME_DAILY_NOTIFY_TYPE: str = 'dailynotifytype'
_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT: str = 'dailylatestmessagecreatedate'
_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: str = 'dailylatestmessagemodifydate'










# ---------- Classes ----------

class AutoDailyNotifyType(IntEnum):
    USER = 1
    ROLE = 2





class AutoDailySettings():
    def __init__(self, guild: discord.Guild, channel: discord.TextChannel, can_post: bool, latest_message_id: int, delete_on_change: bool, notify: Union[discord.Member, discord.Role], latest_message_created_at: datetime.datetime, latest_message_modified_at: datetime.datetime):
        self.__can_post: bool = can_post
        self.__channel: discord.TextChannel = channel
        self.__delete_on_change: bool = delete_on_change
        self.__guild: discord.Guild = guild
        self.__latest_message_id: int = latest_message_id or None
        self.__latest_message_created_at: datetime.datetime = latest_message_created_at or None
        self.__latest_message_modified_at: datetime.datetime = latest_message_modified_at or None
        self.__notify: Union[discord.Member, discord.Role] = notify
        self.__notify_type: AutoDailyNotifyType = None
        if notify is not None:
            if isinstance(notify, discord.Member):
                self.__notify_type = AutoDailyNotifyType.USER
            elif isinstance(notify, discord.Role):
                self.__notify_type = AutoDailyNotifyType.ROLE


    @property
    def can_post(self) -> bool:
        return self.__can_post

    @property
    def channel(self) -> discord.TextChannel:
        return self.__channel

    @property
    def channel_id(self) -> int:
        if self.channel:
            return self.channel.id
        else:
            return None

    @property
    def delete_on_change(self) -> bool:
        return self.__delete_on_change

    @property
    def guild(self) -> discord.Guild:
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

    @property
    def notify(self) -> Union[discord.Member, discord.Role]:
        return self.__notify

    @property
    def notify_id(self) -> int:
        if self.notify:
            return self.notify.id
        else:
            return None

    @property
    def notify_type(self) -> AutoDailyNotifyType:
        return self.__notify_type


    def get_pretty_settings(self) -> List[str]:
        if self.channel_id is not None or self.delete_on_change is not None or self.notify_id is not None:
            result = []
            result.extend(self.get_pretty_setting_channel())
            result.extend(self.get_pretty_setting_changemode())
            result.extend(self.get_pretty_setting_notify())
        else:
            result = ['Auto-posting of the daily announcement is not configured for this server.']
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
        result = convert_to_edit_delete(self.delete_on_change)
        return result


    def _get_pretty_notify_settings(self) -> str:
        if self.notify_id is not None and self.notify_type is not None:
            type_str = ''
            name = ''
            if self.notify_type == AutoDailyNotifyType.USER:
                member: discord.Member = self.guild.get_member(self.notify_id)
                name = f'{member.display_name} ({member.name}#{member.discriminator})'
                type_str = 'user'
            elif self.notify_type == AutoDailyNotifyType.ROLE:
                role: discord.Role = self.guild.get_role(self.notify_id)
                name = role.name
                type_str = 'role'

            if type_str and name:
                result = f'{name} ({type_str})'
            else:
                result = f'An error occured on retrieving the notify settings. Please contact the bot\'s author (in `/about`).'
        else:
            result = '<not set>'
        return result


    def get_pretty_setting_channel(self) -> List[str]:
        if self.channel:
            result = [f'Auto-daily channel: {self.channel.mention}']
        else:
            result = [f'Auto-daily channel: `{self._get_pretty_channel_name()}`']
        return result


    def get_pretty_setting_changemode(self) -> List[str]:
        result = [f'Auto-daily mode: `{self._get_pretty_mode()}`']
        return result


    def get_pretty_setting_notify(self) -> List[str]:
        result = [f'Notify on auto-daily change: `{self._get_pretty_notify_settings()}`']
        return result


    async def reset(self) -> bool:
        settings = {
            _COLUMN_NAME_DAILY_CHANNEL_ID: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None,
            _COLUMN_NAME_DAILY_DELETE_ON_CHANGE: app_settings.DEFAULT_MODE_REPOST_AUTODAILY,
            _COLUMN_NAME_DAILY_NOTIFY_ID: None,
            _COLUMN_NAME_DAILY_NOTIFY_TYPE: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: None
        }
        success = await _db_update_server_setting(self.guild_id, settings)
        if success:
            self.__channel = None
            self.__delete_on_change = None
            self.__notify = None
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
        success = await _db_update_server_setting(self.guild_id, settings)
        if success:
            self.__channel = None
            self.__latest_message_id = None
            self.__latest_message_created_at = None
            self.__latest_message_modified_at = None
        return success


    async def reset_daily_delete_on_change(self) -> bool:
        settings = {
            _COLUMN_NAME_DAILY_DELETE_ON_CHANGE: app_settings.DEFAULT_MODE_REPOST_AUTODAILY
        }
        success = await _db_update_server_setting(self.guild_id, settings)
        if success:
            self.__delete_on_change = None
        return success


    async def reset_latest_message(self) -> bool:
        settings = {
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT: None,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: None
        }
        success = await _db_update_server_setting(self.guild_id, settings)
        if success:
            self.__latest_message_id = None
            self.__latest_message_created_at = None
            self.__latest_message_modified_at = None
        return success


    async def reset_notify(self) -> bool:
        settings = {
            _COLUMN_NAME_DAILY_NOTIFY_ID: None,
            _COLUMN_NAME_DAILY_NOTIFY_TYPE: None
        }
        success = await _db_update_server_setting(self.guild_id, settings)
        if success:
            self.__notify = None
        return success


    async def set_channel(self, channel: discord.TextChannel) -> bool:
        if not self.channel_id or channel.id != self.channel_id:
            settings = {
                _COLUMN_NAME_DAILY_CHANNEL_ID: channel.id,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None
            }
            success = await _db_update_server_setting(self.guild_id, settings)
            if success:
                self.__channel = channel
            return success
        return True


    async def set_latest_message(self, message: discord.Message) -> bool:
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
            success = await _db_update_server_setting(self.guild_id, settings)
            if success:
                self.__latest_message_id = settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID]
                self.__latest_message_modified_at = settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT]
                if _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT in settings:
                    self.__latest_message_created_at = settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT]
            return success
        else:
            return True


    async def set_notify(self, notify: Union[discord.Role, discord.User]) -> bool:
        if notify:
            notify_id = notify.id
            if isinstance(notify, discord.Role):
                notify_type = AutoDailyNotifyType.ROLE
            elif isinstance(notify, discord.Member):
                notify_type = AutoDailyNotifyType.USER
            else:
                raise TypeError(f'Could not set autodaily notify: the provided mention is neither a role nor a user"')
            if not self.notify_id or notify_id != self.notify_id:
                settings = {
                    _COLUMN_NAME_DAILY_NOTIFY_ID: notify_id,
                    _COLUMN_NAME_DAILY_NOTIFY_TYPE: convert_from_autodaily_notify_type(notify_type)
                }
                success = await _db_update_server_setting(self.guild_id, settings)
                if success:
                    self.notify = notify
                return success
            return True
        else:
            return False


    async def toggle_daily_delete_on_change(self) -> bool:
        new_value = lookups.select_next_element(lookups.DELETE_ON_CHANGE_ORDER, self.__delete_on_change)
        success = await db_update_daily_delete_on_change(self.guild_id, new_value)
        if success:
            self.__delete_on_change = new_value
        return success










class GuildSettings(object):
    def __init__(self, bot: commands.Bot, row: asyncpg.Record):
        self.__guild_id: int = row.get(_COLUMN_NAME_GUILD_ID)
        self.__prefix: str = row.get(_COLUMN_NAME_PREFIX)
        self.__use_pagination: bool = row.get(_COLUMN_NAME_USE_PAGINATION)
        daily_channel_id = row.get(_COLUMN_NAME_DAILY_CHANNEL_ID)
        can_post_daily = row.get(_COLUMN_NAME_DAILY_CAN_POST)
        daily_latest_message_id = row.get(_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID)
        daily_post_mode = row.get(_COLUMN_NAME_DAILY_DELETE_ON_CHANGE)
        daily_notify_id = row.get(_COLUMN_NAME_DAILY_NOTIFY_ID)
        daily_notify_type = convert_to_autodaily_notify_type(row.get(_COLUMN_NAME_DAILY_NOTIFY_TYPE))
        daily_latest_message_created_at = row.get(_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT)
        daily_latest_message_modified_at = row.get(_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT)

        try:
            channel = bot.get_channel(daily_channel_id)
        except Exception as error:
            channel = None
        try:
            self.__guild = bot.get_guild(self.__guild_id)
        except Exception as error:
            self.__guild = None

        notify = None
        if daily_notify_id and daily_notify_type and self.__guild:
            if daily_notify_type == AutoDailyNotifyType.USER:
                notify = self.__guild.get_member(daily_notify_id)
            elif daily_notify_type == AutoDailyNotifyType.ROLE:
                notify = self.__guild.get_role(daily_notify_id)

        self.__autodaily_settings: AutoDailySettings = AutoDailySettings(self.__guild, channel, can_post_daily, daily_latest_message_id, daily_post_mode, notify, daily_latest_message_created_at, daily_latest_message_modified_at)


    @property
    def autodaily(self) -> AutoDailySettings:
        return self.__autodaily_settings

    @property
    def guild(self) -> discord.Guild:
        return self.__guild

    @property
    def id(self) -> int:
        return self.__guild.id

    @property
    def pretty_use_pagination(self) -> str:
        return convert_to_on_off(self.use_pagination)

    @property
    def prefix(self) -> str:
        return self.__prefix or app_settings.DEFAULT_PREFIX

    @property
    def use_pagination(self) -> bool:
        return self.__use_pagination or app_settings.DEFAULT_USE_EMOJI_PAGINATOR


    async def reset(self) -> (bool, bool, bool):
        success_prefix = await self.reset_prefix()
        success_pagination = await self.reset_use_pagination()
        success_autodaily = await self.autodaily.reset()
        return success_prefix, success_pagination, success_autodaily


    async def reset_prefix(self) -> bool:
        if self.__prefix:
            settings = {
                _COLUMN_NAME_PREFIX: None
            }
            success = await _db_update_server_setting(self.__guild_id, settings)
            if success:
                self.__prefix = None
            return success
        else:
            return True


    async def reset_use_pagination(self) -> bool:
        if self.__use_pagination is not None:
            settings = {
                _COLUMN_NAME_USE_PAGINATION: None
            }
            success = await _db_update_server_setting(self.__guild_id, settings)
            if success:
                self.__use_pagination = None
            return success
        return True


    async def set_prefix(self, prefix: str) -> bool:
        pss_assert.valid_parameter_value(prefix, _COLUMN_NAME_PREFIX, min_length=1)
        if not self.__prefix or prefix != self.__prefix:
            settings = {
                _COLUMN_NAME_PREFIX: prefix
            }
            success = await _db_update_server_setting(self.__guild_id, settings)
            if success:
                self.__prefix = prefix
            return success
        return True


    async def set_use_pagination(self, use_pagination: bool) -> bool:
        if use_pagination is None:
            return await toggle_use_pagination(self.id)
        else:
            pss_assert.valid_parameter_value(use_pagination, 'use_pagination', min_length=1, allowed_values=_VALID_PAGINATION_SWITCH_VALUES.keys(), case_sensitive=False)
            use_pagination = convert_from_on_off(use_pagination)
            if not self.__use_pagination or use_pagination != self.__use_pagination:
                settings = {
                    _COLUMN_NAME_USE_PAGINATION: use_pagination
                }
                success = await _db_update_server_setting(self.id, settings)
                if success:
                    self.__use_pagination = use_pagination
                return success
            return True











class GuildSettingsCollection():
    def __init__(self):
        self.__data: dict = {}


    @property
    def autodaily_settings(self) -> List[AutoDailySettings]:
        return [guild_settings.autodaily for guild_settings in self.__data.values()]


    async def create_guild_settings(self, bot: commands.Bot, guild_id: int) -> bool:
        success = await db_create_server_settings(guild_id)
        if success:
            self.__data[guild_id] = GuildSettings(bot, _db_get_server_settings(guild_id))
        return success


    async def delete_guild_settings(self, guild_id: int) -> bool:
        success = await db_delete_server_settings(guild_id)
        if success and guild_id in self.__data:
            self.__data.pop(guild_id)
        return success


    async def get(self, bot: commands.Bot, guild_id: int) -> GuildSettings:
        if guild_id not in self.__data:
            self.create_guild_settings(bot, guild_id)
        return self.__data[guild_id]


    async def init(self, bot: commands.Bot):
        for server_settings in (await _db_get_server_settings()):
            self.__data[server_settings[_COLUMN_NAME_GUILD_ID]] = GuildSettings(bot, server_settings)












async def create_autodaily_settings(bot: discord.ext.commands.Bot, guild_id: int) -> AutoDailySettings:
    if guild_id is None or bot is None:
        raise Exception('No parameters given. You need to specify both parameters \'bot\' and \'guild_id\'.')

    autodaily_settings = await _prepare_create_autodaily_settings(guild_id)
    _, channel_id, can_post, latest_message_id, delete_on_change, notify_id, notify_type, latest_message_create_date, latest_message_modify_date = autodaily_settings[0]
    try:
        channel = bot.get_channel(channel_id)
    except Exception as error:
        channel = None
    try:
        guild = bot.get_guild(guild_id)
    except Exception as error:
        guild = None

    notify = None
    if notify_id and notify_type and guild:
        if notify_type == AutoDailyNotifyType.USER:
            notify = guild.get_member(notify_id)
        elif notify_type == AutoDailyNotifyType.ROLE:
            notify = guild.get_role(notify_id)

    return AutoDailySettings(guild, channel, can_post, latest_message_id, delete_on_change, notify, latest_message_create_date, latest_message_modify_date)


async def _prepare_create_autodaily_settings(guild_id: int) -> list:
    autodaily_settings = await db_get_autodaily_settings(guild_id=guild_id)
    if not autodaily_settings:
        await db_create_server_settings(guild_id)
        autodaily_settings = await db_get_autodaily_settings(guild_id=guild_id)
    if not autodaily_settings:
        raise Exception(f'No auto-daily settings found for guild_id [{guild_id}]')

    return autodaily_settings










# ---------- Functions ----------

def convert_from_autodaily_notify_type(notify_type: AutoDailyNotifyType) -> int:
    if notify_type:
        return notify_type.value
    else:
        return None


def convert_from_on_off(switch: str) -> bool:
    if switch is None:
        return None
    else:
        switch = switch.lower()
        if switch in _VALID_PAGINATION_SWITCH_VALUES.keys():
            result = _VALID_PAGINATION_SWITCH_VALUES[switch]
            return result
        else:
            return None


def convert_to_autodaily_notify_type(notify_type: int) -> AutoDailyNotifyType:
    if notify_type:
        for _, member in AutoDailyNotifyType.__members__.items():
            if member.value == notify_type:
                return member
        return None
    else:
        return None


def convert_to_on_off(value: bool) -> str:
    if value is True:
        return 'ON'
    elif value is False:
        return 'OFF'
    else:
        return '<NOT SET>'


def convert_to_edit_delete(value: bool) -> str:
    if value is True:
        return 'Delete daily post and post new daily on change.'
    elif value is False:
        return 'Edit daily post on change.'
    else:
        return 'Post new daily on change.'


async def fix_prefixes() -> bool:
    all_prefixes = await _db_get_server_settings(guild_id=None, setting_names=[_COLUMN_NAME_GUILD_ID, _COLUMN_NAME_PREFIX])
    all_success = True
    if all_prefixes:
        for guild_id, prefix in all_prefixes:
            if guild_id and prefix and prefix.startswith(' '):
                new_prefix = prefix.lstrip()
                if new_prefix:
                    print(f'[fix_prefixes] Fixing prefix \'{prefix}\' for guild with id \'{guild_id}\'. New prefix is: \'{new_prefix}\'')
                    success = await set_prefix(guild_id, new_prefix)
                else:
                    print(f'[fix_prefixes] Fixing prefix \'{prefix}\' for guild with id \'{guild_id}\'. New prefix is: \'{app_settings.DEFAULT_PREFIX}\'')
                    success = await reset_prefix(guild_id)
                if not success:
                    all_success = False
    return all_success


async def get_autodaily_settings(bot: discord.ext.commands.Bot, guild_id: int = None, can_post: bool = None, no_post_yet: bool = False) -> List[AutoDailySettings]:
    if guild_id:
        autodaily_settings_collection = [(await GUILD_SETTINGS.get(bot, guild_id))]
    else:
        autodaily_settings_collection = GUILD_SETTINGS.autodaily_settings
    autodaily_settings_collection = [autodaily_settings for autodaily_settings in autodaily_settings_collection if autodaily_settings.channel is not None]
    result = []
    for autodaily_settings in autodaily_settings_collection:
        if not (no_post_yet and autodaily_settings.latest_message_created_at):
            result.append(autodaily_settings)
    return result


async def get_prefix(bot: discord.ext.commands.Bot, message: discord.Message) -> str:
    if util.is_guild_channel(message.channel):
        guild_settings = await GUILD_SETTINGS.get(bot, message.channel.guild.id)
        result = guild_settings.prefix
    else:
        result = app_settings.DEFAULT_PREFIX
    return result


async def get_prefix_or_default(guild_id: int) -> str:
    result = await db_get_prefix(guild_id)
    if result is None or result.lower() == 'none':
        result = app_settings.DEFAULT_PREFIX
    return result


async def get_pagination_mode(guild: discord.Guild) -> str:
    use_pagination_mode = await db_get_use_pagination(guild)
    result = convert_to_on_off(use_pagination_mode)
    return result


async def reset_prefix(guild_id: int) -> bool:
    success = await db_reset_prefix(guild_id)
    return success


async def set_autodaily_notify(guild_id: int, notify_id: int, notify_type: AutoDailyNotifyType) -> bool:
    await db_create_server_settings(guild_id)

    success = await db_update_daily_notify_settings(guild_id, notify_id, notify_type)
    return success


async def set_pagination(guild: discord.Guild, switch: str) -> bool:
    await db_create_server_settings(guild.id)

    if switch is None:
        return await toggle_use_pagination(guild.id)
    else:
        pss_assert.valid_parameter_value(switch, 'switch', min_length=1, allowed_values=_VALID_PAGINATION_SWITCH_VALUES.keys(), case_sensitive=False)
        use_pagination = convert_from_on_off(switch)
        success = await db_update_use_pagination(guild.id, use_pagination)
        if success:
            return use_pagination
        else:
            return not use_pagination


async def set_prefix(guild_id: int, prefix: str) -> bool:
    await db_create_server_settings(guild_id)
    success = await db_update_prefix(guild_id, prefix)
    return success


async def toggle_daily_delete_on_change(guild_id: int) -> bool:
    await db_create_server_settings(guild_id)
    delete_on_change = await db_get_daily_delete_on_change(guild_id)
    if delete_on_change is True:
        new_value = None
    elif delete_on_change is False:
        new_value = True
    else:
        new_value = False
    success = await db_update_daily_delete_on_change(guild_id, new_value)
    if success:
        return new_value
    else:
        return delete_on_change


async def toggle_use_pagination(guild: discord.Guild) -> bool:
    await db_create_server_settings(guild.id)
    use_pagination = await db_get_use_pagination(guild.id)
    success = await db_update_use_pagination(guild.id, not use_pagination)
    if success:
        return not use_pagination
    else:
        return use_pagination













# ---------- DB functions ----------

async def db_create_server_settings(guild_id: int) -> bool:
    if await db_get_has_settings(guild_id):
        return True
    else:
        query = f'INSERT INTO serversettings (guildid, dailydeleteonchange) VALUES ($1, $2)'
        success = await core.db_try_execute(query, [guild_id, app_settings.DEFAULT_MODE_REPOST_AUTODAILY])
        return success


async def db_delete_server_settings(guild_id: int) -> bool:
    query = f'DELETE FROM serversettings WHERE guildid = $1'
    success = await core.db_try_execute(query, [guild_id])
    return success


async def db_get_autodaily_settings(guild_id: int = None, can_post: bool = None, only_guild_ids: bool = False, no_post_yet: bool = False) -> list:
    wheres = ['(dailychannelid IS NOT NULL or dailynotifyid IS NOT NULL)']
    if guild_id is not None:
        wheres.append(util.db_get_where_string(_COLUMN_NAME_GUILD_ID, column_value=guild_id))
    if can_post is not None:
        wheres.append(util.db_get_where_string(_COLUMN_NAME_DAILY_CAN_POST, column_value=can_post))
    if no_post_yet is True:
        wheres.append(util.db_get_where_string(_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT, column_value=None))
    if only_guild_ids:
        setting_names = [_COLUMN_NAME_GUILD_ID]
    else:
        setting_names = [_COLUMN_NAME_GUILD_ID, _COLUMN_NAME_DAILY_CHANNEL_ID, _COLUMN_NAME_DAILY_CAN_POST, _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID, _COLUMN_NAME_DAILY_DELETE_ON_CHANGE, _COLUMN_NAME_DAILY_NOTIFY_ID, _COLUMN_NAME_DAILY_NOTIFY_TYPE, _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT, _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT]
    settings = await _db_get_server_settings(guild_id, setting_names=setting_names, additional_wheres=wheres)
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
                convert_to_autodaily_notify_type(setting[6]),
                setting[7],
                setting[8]
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
    result = await _db_get_server_setting(guild_id, setting_names=setting_names)
    return result[0] or None if result else None


async def db_get_daily_delete_on_change(guild_id: int) -> bool:
    setting_names = [_COLUMN_NAME_DAILY_DELETE_ON_CHANGE]
    result = await _db_get_server_setting(guild_id, setting_names=setting_names)
    return result[0] or None if result else None


async def db_get_daily_latest_message_create_date(guild_id: int) -> datetime.datetime:
    setting_names = [_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT]
    result = await _db_get_server_setting(guild_id, setting_names=setting_names)
    return result[0] or None if result else None


async def db_get_daily_latest_message_id(guild_id: int) -> int:
    setting_names = [_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID]
    result = await _db_get_server_setting(guild_id, setting_names=setting_names)
    return result[0] or None if result else None


async def db_get_daily_notify_settings(guild_id: int) -> (int, AutoDailyNotifyType):
    setting_names = [_COLUMN_NAME_DAILY_NOTIFY_ID, _COLUMN_NAME_DAILY_NOTIFY_TYPE]
    result = await _db_get_server_setting(guild_id, setting_names=setting_names)
    return result or None


async def db_get_has_settings(guild_id: int) -> bool:
    results = await _db_get_server_settings(guild_id)
    if results:
        return True
    else:
        return False


async def db_get_prefix(guild_id: int) -> str:
    await db_create_server_settings(guild_id)
    setting_names = [_COLUMN_NAME_PREFIX]
    result = await _db_get_server_setting(guild_id, setting_names=setting_names)
    return result[0] or None


async def db_get_use_pagination(guild: discord.Guild) -> bool:
    if guild:
        setting_names = [_COLUMN_NAME_USE_PAGINATION]
        settings = await _db_get_server_settings(guild.id, setting_names=setting_names)
        if settings:
            for setting in settings:
                result = setting[0]
                if result is None:
                    return True
                return result
    return app_settings.DEFAULT_USE_EMOJI_PAGINATOR


async def db_reset_autodaily_channel(guild_id: int) -> bool:
    current_autodaily_settings = await db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                _COLUMN_NAME_DAILY_CHANNEL_ID: None,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT: None,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: None
            }
            success = await _db_update_server_setting(guild_id, settings)
            return success
    return True


async def db_reset_autodaily_latest_message_id(guild_id: int) -> bool:
    current_autodaily_settings = await db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT: None,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: None
            }
            success = await _db_update_server_setting(guild_id, settings)
            return success
    return True


async def db_reset_autodaily_mode(guild_id: int) -> bool:
    current_autodaily_settings = await db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                _COLUMN_NAME_DAILY_DELETE_ON_CHANGE: app_settings.DEFAULT_MODE_REPOST_AUTODAILY
            }
            success = await _db_update_server_setting(guild_id, settings)
            return success
    return True


async def db_reset_autodaily_notify(guild_id: int) -> bool:
    current_autodaily_settings = await db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                _COLUMN_NAME_DAILY_NOTIFY_ID: None,
                _COLUMN_NAME_DAILY_NOTIFY_TYPE: None
            }
            success = await _db_update_server_setting(guild_id, settings)
            return success
    return True


async def db_reset_autodaily_settings(guild_id: int) -> bool:
    current_autodaily_settings = await db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                _COLUMN_NAME_DAILY_CHANNEL_ID: None,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None,
                _COLUMN_NAME_DAILY_DELETE_ON_CHANGE: app_settings.DEFAULT_MODE_REPOST_AUTODAILY,
                _COLUMN_NAME_DAILY_NOTIFY_ID: None,
                _COLUMN_NAME_DAILY_NOTIFY_TYPE: None,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT: None,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: None
            }
            success = await _db_update_server_setting(guild_id, settings)
            return success
    return True


async def db_reset_prefix(guild_id: int) -> bool:
    current_prefix = await db_get_prefix(guild_id)
    if current_prefix is not None:
        settings = {
            _COLUMN_NAME_PREFIX: None
        }
        success = await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_reset_use_pagination(guild: discord.Guild) -> bool:
    current_use_pagination = await db_get_use_pagination(guild)
    if current_use_pagination is not None:
        settings = {
            _COLUMN_NAME_USE_PAGINATION: None
        }
        success = await _db_update_server_setting(guild.id, settings)
        return success
    return True


async def db_update_autodaily_settings(guild_id: int, channel_id: int = None, can_post: bool = None, latest_message_id: int = None, delete_on_change: bool = None, notify_id: int = None, notify_type: AutoDailyNotifyType = None, latest_message_modify_date: datetime.datetime = None) -> bool:
    autodaily_settings = await db_get_autodaily_settings(guild_id)
    current_can_post = None
    current_channel_id = None
    current_latest_message_id = None
    current_delete_on_change = None
    current_notify_id = None
    current_notify_type = None
    if autodaily_settings:
        (_, current_channel_id, current_can_post, current_latest_message_id, current_delete_on_change, current_notify_id, current_notify_type, current_latest_message_create_date, current_latest_message_modify_date) = autodaily_settings[0]
    if (current_channel_id != channel_id
            or current_latest_message_id != latest_message_id
            or current_can_post != can_post
            or current_delete_on_change != delete_on_change
            or current_notify_id != notify_id
            or current_notify_type != notify_type
            or latest_message_modify_date and (current_latest_message_create_date is None or current_latest_message_modify_date != latest_message_modify_date)):
        settings = {}
        if channel_id is not None:
            settings[_COLUMN_NAME_DAILY_CHANNEL_ID] = channel_id
        if can_post is not None:
            settings[_COLUMN_NAME_DAILY_CAN_POST] = can_post
        if latest_message_id is not None:
            settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_ID] = latest_message_id
        if delete_on_change is not None:
            settings[_COLUMN_NAME_DAILY_DELETE_ON_CHANGE] = delete_on_change
        if notify_id is not None:
            settings[_COLUMN_NAME_DAILY_NOTIFY_ID] = notify_id
        if notify_type is not None:
            settings[_COLUMN_NAME_DAILY_NOTIFY_TYPE] = convert_from_autodaily_notify_type(notify_type)
        if latest_message_modify_date is not None:
            settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT] = latest_message_modify_date
            if current_latest_message_create_date is None:
                settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT] = settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT]
        success = not settings or await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_update_daily_channel_id(guild_id: int, channel_id: int) -> bool:
    current_daily_channel_id = await db_get_daily_channel_id(guild_id)
    if not current_daily_channel_id or channel_id != current_daily_channel_id:
        settings = {
            _COLUMN_NAME_DAILY_CHANNEL_ID: channel_id,
            _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: None
        }
        success = await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_update_daily_delete_on_change(guild_id: int, delete_on_change: bool) -> bool:
    current_daily_delete_on_change = await db_get_daily_delete_on_change(guild_id)
    if not current_daily_delete_on_change or delete_on_change != current_daily_delete_on_change:
        settings = {
            _COLUMN_NAME_DAILY_DELETE_ON_CHANGE: delete_on_change,
        }
        success = await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_update_daily_latest_message(guild_id: int, message: discord.Message) -> bool:
    if message:
        current_daily_latest_message_id = await db_get_daily_latest_message_id(guild_id)
        current_daily_latest_message_create_date = await db_get_daily_latest_message_create_date(guild_id)
        new_day = current_daily_latest_message_create_date is None or message.created_at.day != current_daily_latest_message_create_date.day
        if new_day:
            modify_date = message.created_at
        else:
            modify_date = message.edited_at or message.created_at

        if not current_daily_latest_message_id or message.id != current_daily_latest_message_id:
            settings = {
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_ID: message.id,
                _COLUMN_NAME_DAILY_LATEST_MESSAGE_MODIFIED_AT: modify_date
            }
            if new_day:
                settings[_COLUMN_NAME_DAILY_LATEST_MESSAGE_CREATED_AT] = message.created_at

            success = await _db_update_server_setting(guild_id, settings)
            return success
    else:
        success = await db_reset_autodaily_latest_message_id(guild_id)
        return success
    return True


async def db_update_daily_notify_settings(guild_id: int, notify_id: int, notify_type: AutoDailyNotifyType) -> bool:
    current_daily_notify_id, _ = await db_get_daily_notify_settings(guild_id)
    if not current_daily_notify_id or notify_id != current_daily_notify_id:
        settings = {
            _COLUMN_NAME_DAILY_NOTIFY_ID: notify_id,
            _COLUMN_NAME_DAILY_NOTIFY_TYPE: convert_from_autodaily_notify_type(notify_type)
        }
        success = await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_update_prefix(guild_id: int, prefix: str) -> bool:
    current_prefix = await db_get_prefix(guild_id)
    if not current_prefix or prefix != current_prefix:
        settings = {
            _COLUMN_NAME_PREFIX: prefix
        }
        success = await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_update_use_pagination(guild: discord.Guild, use_pagination: bool) -> bool:
    current_use_pagination = await db_get_use_pagination(guild.id)
    if not current_use_pagination or use_pagination != current_use_pagination:
        settings = {
            _COLUMN_NAME_USE_PAGINATION: use_pagination
        }
        success = await _db_update_server_setting(guild.id, settings)
        return success
    return True










# ---------- Utilities ----------

async def _db_get_server_settings(guild_id: int = None, setting_names: list = None, additional_wheres: list = None) -> list:
    additional_wheres = additional_wheres or []
    wheres = []
    if guild_id is not None:
        wheres.append(f'guildid = $1')

    if setting_names:
        setting_string = ', '.join(setting_names)
    else:
        setting_string = '*'

    if additional_wheres:
        wheres.extend(additional_wheres)

    where = util.db_get_where_and_string(wheres)
    if where:
        query = f'SELECT {setting_string} FROM serversettings WHERE {where}'
        if guild_id is not None:
            records = await core.db_fetchall(query, [guild_id])
        else:
            records = await core.db_fetchall(query)
    else:
        query = f'SELECT {setting_string} FROM serversettings'
        records = await core.db_fetchall(query)
    if records:
        return records
    else:
        return []


async def _db_get_server_setting(guild_id: int = None, setting_names: list = None, additional_wheres: list = None, conversion_functions: List[Callable[[object], object]] = None) -> object:
    settings = await _db_get_server_settings(guild_id, setting_names=setting_names, additional_wheres=additional_wheres)
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


async def _db_update_server_setting(guild_id: int, settings: dict) -> bool:
    set_names = []
    set_values = [guild_id]
    for i, (key, value) in enumerate(settings.items(), start=2):
        set_names.append(f'{key} = ${i:d}')
        set_values.append(value)
    set_string = ', '.join(set_names)
    query = f'UPDATE serversettings SET {set_string} WHERE guildid = $1'
    success = await core.db_try_execute(query, set_values)
    return success









# ---------- Initialization ----------

GUILD_SETTINGS: GuildSettingsCollection = GuildSettingsCollection()










# ---------- Main ----------

async def init(bot: commands.Bot):
    await fix_prefixes()
    await GUILD_SETTINGS.init(bot)