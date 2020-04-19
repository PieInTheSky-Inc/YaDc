import datetime
import discord
from discord.ext import commands
from enum import IntEnum
from typing import List, Union

import pss_assert
import pss_core as core
import settings
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










# ---------- Classes ----------

class AutoDailyNotifyType(IntEnum):
    USER = 1
    ROLE = 2





class AutoDailySettings():
    def __init__(self, guild: discord.Guild, channel: discord.TextChannel, can_post: bool, latest_message_id: int, delete_on_change: bool, notify: Union[discord.Member, discord.Role], latest_message_create_date: datetime.datetime, latest_message_modify_date: datetime.datetime):
        self.__can_post: bool = can_post
        self.__channel: discord.TextChannel = channel
        self.__delete_on_change: bool = delete_on_change
        self.__guild: discord.Guild = guild
        self.__latest_message_id: int = latest_message_id or None
        self.__latest_message_create_date: datetime.datetime = latest_message_create_date or None
        self.__latest_message_modify_date: datetime.datetime = latest_message_modify_date or None
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
    def latest_message_create_date(self) -> datetime:
        return self.__latest_message_create_date

    @property
    def latest_message_modify_date(self) -> datetime:
        return self.__latest_message_modify_date

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
        result = [f'Auto-daily channel: `{self._get_pretty_channel_name()}`']
        return result


    def get_pretty_setting_changemode(self) -> List[str]:
        result = [f'Auto-daily mode: `{self._get_pretty_mode()}`']
        return result


    def get_pretty_setting_notify(self) -> List[str]:
        result = [f'Notify on auto-daily change: `{self._get_pretty_notify_settings()}`']
        return result











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
    all_prefixes = await _db_get_server_settings(guild_id=None, setting_names=['guildid', 'prefix'])
    all_success = True
    if all_prefixes:
        for guild_id, prefix in all_prefixes:
            if guild_id and prefix and prefix.startswith(' '):
                new_prefix = prefix.lstrip()
                if new_prefix:
                    print(f'[fix_prefixes] Fixing prefix \'{prefix}\' for guild with id \'{guild_id}\'. New prefix is: \'{new_prefix}\'')
                    success = await set_prefix(guild_id, new_prefix)
                else:
                    print(f'[fix_prefixes] Fixing prefix \'{prefix}\' for guild with id \'{guild_id}\'. New prefix is: \'{settings.PREFIX_DEFAULT}\'')
                    success = await reset_prefix(guild_id)
                if not success:
                    all_success = False
    return all_success


async def get_autodaily_settings(bot: discord.ext.commands.Bot, guild_id: int = None, can_post: bool = None, no_post_yet: bool = False) -> List[AutoDailySettings]:
    db_autodaily_settings = await db_get_autodaily_settings(guild_id=guild_id, can_post=can_post, only_guild_ids=True, no_post_yet=no_post_yet)
    result = []
    for db_autodaily_setting in db_autodaily_settings:
        guild_id = db_autodaily_setting[0]
        if guild_id:
            autodaily_setting = await create_autodaily_settings(bot, guild_id)
            if not (no_post_yet and autodaily_setting.latest_message_create_date):
                result.append(autodaily_setting)
    return result


async def get_prefix(bot: discord.ext.commands.Bot, message: discord.Message) -> str:
    result = None
    if util.is_guild_channel(message.channel):
        result = await get_prefix_or_default(message.channel.guild.id)
    else:
        result = settings.PREFIX_DEFAULT
    return result


async def get_prefix_or_default(guild_id: int) -> str:
    result = await db_get_prefix(guild_id)
    if result is None or result.lower() == 'none':
        result = settings.PREFIX_DEFAULT
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
        success = await core.db_try_execute(query, [guild_id, settings.DEFAULT_MODE_REPOST_AUTODAILY])
        return success


async def db_delete_server_settings(guild_id: int) -> bool:
    query = f'DELETE FROM serversettings WHERE guildid = $1'
    success = await core.db_try_execute(query, [guild_id])
    return success


async def db_get_autodaily_settings(guild_id: int = None, can_post: bool = None, only_guild_ids: bool = False, no_post_yet: bool = False) -> list:
    wheres = ['(dailychannelid IS NOT NULL or dailynotifyid IS NOT NULL)']
    if guild_id is not None:
        wheres.append(util.db_get_where_string('guildid', guild_id))
    if can_post is not None:
        wheres.append(util.db_get_where_string('dailycanpost', can_post))
    if no_post_yet is True:
        wheres.append(util.db_get_where_string('dailylatestmessagecreatedate', None))
    if only_guild_ids:
        setting_names = ['guildid']
    else:
        setting_names = ['guildid', 'dailychannelid', 'dailycanpost', 'dailylatestmessageid', 'dailydeleteonchange', 'dailynotifyid', 'dailynotifytype', 'dailylatestmessagecreatedate', 'dailylatestmessagemodifydate']
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
    setting_names = ['dailychannelid']
    settings = await _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return setting[0]
    else:
        return None


async def db_get_daily_delete_on_change(guild_id: int) -> bool:
    setting_names = ['dailydeleteonchange']
    settings = await _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            result = setting[0]
            return result
    else:
        return None


async def db_get_daily_latest_message_create_date(guild_id: int) -> datetime.datetime:
    setting_names = ['dailylatestmessagecreatedate']
    settings = await _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return setting[0]
    else:
        return None


async def db_get_daily_latest_message_id(guild_id: int) -> int:
    setting_names = ['dailylatestmessageid']
    settings = await _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return setting[0]
    else:
        return None


async def db_get_daily_notify_settings(guild_id: int) -> (int, AutoDailyNotifyType):
    setting_names = ['dailynotifyid', 'dailynotifytype']
    settings = await _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return (setting[0], convert_to_autodaily_notify_type(setting[1]))
    else:
        return (None, None)


async def db_get_has_settings(guild_id: int) -> bool:
    results = await _db_get_server_settings(guild_id)
    if results:
        return True
    else:
        return False


async def db_get_prefix(guild_id: int) -> str:
    setting_names = ['prefix']
    settings = await _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return setting[0]
    else:
        return None


async def db_get_use_pagination(guild: discord.Guild) -> bool:
    if guild:
        setting_names = ['usepagination']
        settings = await _db_get_server_settings(guild.id, setting_names=setting_names)
        if settings:
            for setting in settings:
                result = setting[0]
                if result is None:
                    return True
                return result
    return settings.DEFAULT_USE_EMOJI_PAGINATOR


async def db_reset_autodaily_channel(guild_id: int) -> bool:
    current_autodaily_settings = await db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailychannelid': None,
                'dailylatestmessageid': None,
                'dailylatestmessagecreatedate': None,
                'dailylatestmessagemodifydate': None
            }
            success = await _db_update_server_setting(guild_id, settings)
            return success
    return True


async def db_reset_autodaily_latest_message_id(guild_id: int) -> bool:
    current_autodaily_settings = await db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailylatestmessageid': None,
                'dailylatestmessagecreatedate': None,
                'dailylatestmessagemodifydate': None
            }
            success = await _db_update_server_setting(guild_id, settings)
            return success
    return True


async def db_reset_autodaily_mode(guild_id: int) -> bool:
    current_autodaily_settings = await db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailydeleteonchange': settings.DEFAULT_MODE_REPOST_AUTODAILY
            }
            success = await _db_update_server_setting(guild_id, settings)
            return success
    return True


async def db_reset_autodaily_notify(guild_id: int) -> bool:
    current_autodaily_settings = await db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailynotifyid': None,
                'dailynotifytype': None
            }
            success = await _db_update_server_setting(guild_id, settings)
            return success
    return True


async def db_reset_autodaily_settings(guild_id: int) -> bool:
    current_autodaily_settings = await db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailychannelid': None,
                'dailylatestmessageid': None,
                'dailydeleteonchange': settings.DEFAULT_MODE_REPOST_AUTODAILY,
                'dailynotifyid': None,
                'dailynotifytype': None,
                'dailylatestmessagecreatedate': None,
                'dailylatestmessagemodifydate': None
            }
            success = await _db_update_server_setting(guild_id, settings)
            return success
    return True


async def db_reset_prefix(guild_id: int) -> bool:
    current_prefix = await db_get_prefix(guild_id)
    if current_prefix is not None:
        settings = {
            'prefix': None
        }
        success = await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_reset_use_pagination(guild: discord.Guild) -> bool:
    current_use_pagination = await db_get_use_pagination(guild.id)
    if current_use_pagination is not None:
        settings = {
            'usepagination': None
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
            settings['dailychannelid'] = channel_id
        if can_post is not None:
            settings['dailycanpost'] = can_post
        if latest_message_id is not None:
            settings['dailylatestmessageid'] = latest_message_id
        if delete_on_change is not None:
            settings['dailydeleteonchange'] = delete_on_change
        if notify_id is not None:
            settings['dailynotifyid'] = notify_id
        if notify_type is not None:
            settings['dailynotifytype'] = convert_from_autodaily_notify_type(notify_type)
        if latest_message_modify_date is not None:
            settings['dailylatestmessagemodifydate'] = latest_message_modify_date
            if current_latest_message_create_date is None:
                settings['dailylatestmessagecreatedate'] = settings['dailylatestmessagemodifydate']
        success = not settings or await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_update_daily_channel_id(guild_id: int, channel_id: int) -> bool:
    current_daily_channel_id = await db_get_daily_channel_id(guild_id)
    if not current_daily_channel_id or channel_id != current_daily_channel_id:
        settings = {
            'dailychannelid': channel_id,
            'dailylatestmessageid': None
        }
        success = await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_update_daily_delete_on_change(guild_id: int, delete_on_change: bool) -> bool:
    current_daily_delete_on_change = await db_get_daily_delete_on_change(guild_id)
    if not current_daily_delete_on_change or delete_on_change != current_daily_delete_on_change:
        settings = {
            'dailydeleteonchange': delete_on_change,
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
                'dailylatestmessageid': message.id,
                'dailylatestmessagemodifydate': modify_date
            }
            if new_day:
                settings['dailylatestmessagecreatedate'] = message.created_at

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
            'dailynotifyid': notify_id,
            'dailynotifytype': convert_from_autodaily_notify_type(notify_type)
        }
        success = await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_update_prefix(guild_id: int, prefix: str) -> bool:
    current_prefix = await db_get_prefix(guild_id)
    if not current_prefix or prefix != current_prefix:
        settings = {
            'prefix': prefix
        }
        success = await _db_update_server_setting(guild_id, settings)
        return success
    return True


async def db_update_use_pagination(guild: discord.Guild, use_pagination: bool) -> bool:
    current_use_pagination = await db_get_use_pagination(guild.id)
    if not current_use_pagination or use_pagination != current_use_pagination:
        settings = {
            'usepagination': use_pagination
        }
        success = await _db_update_server_setting(guild.id, settings)
        return success
    return True










# ---------- Utilities ----------

async def _db_get_server_settings(guild_id: int = None, setting_names: list = None, additional_wheres: list = []) -> list:
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









# ---------- Main ----------

async def init():
    await fix_prefixes()