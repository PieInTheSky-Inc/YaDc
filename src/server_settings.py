import discord
from discord.ext import commands
from enum import IntEnum
from typing import List, Union

import settings
import utility as util

import pss_assert
import pss_core as core


# ---------- Constants ----------

__AUTODAILY_SETTING_COUNT = 7


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
    def __init__(self, guild: discord.Guild, channel: discord.TextChannel, can_post: bool, latest_message_id: int, delete_on_change: bool, notify: Union[discord.Member, discord.Role]):
        self.__can_post: bool = can_post
        self.__channel: discord.TextChannel = channel
        self.__delete_on_change: bool = delete_on_change
        self.__guild: discord.Guild = guild
        self.__latest_message_id: int = latest_message_id or None
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











def create_autodaily_settings(bot: discord.ext.commands.Bot, guild_id: int) -> AutoDailySettings:
    if guild_id is None or bot is None:
        raise Exception('No parameters given. You need to specify both parameters \'bot\' and \'guild_id\'.')

    autodaily_settings = _prepare_create_autodaily_settings(guild_id)
    _, channel_id, can_post, latest_message_id, delete_on_change, notify_id, notify_type = autodaily_settings[0]
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

    return AutoDailySettings(guild, channel, can_post, latest_message_id, delete_on_change, notify)


def _prepare_create_autodaily_settings(guild_id: int) -> list:
    autodaily_settings = db_get_autodaily_settings(guild_id=guild_id)
    if not autodaily_settings:
        db_create_server_settings(guild_id)
        autodaily_settings = db_get_autodaily_settings(guild_id=guild_id)
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
            if repr(member.value) == notify_type:
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


def fix_prefixes() -> bool:
    all_prefixes = _db_get_server_settings(guild_id=None, setting_names=['guildid', 'prefix'])
    all_success = True
    if all_prefixes:
        for guild_id, prefix in all_prefixes:
            if guild_id and prefix and prefix.startswith(' '):
                new_prefix = prefix.lstrip()
                if new_prefix:
                    print(f'[fix_prefixes] Fixing prefix \'{prefix}\' for guild with id \'{guild_id}\'. New prefix is: \'{new_prefix}\'')
                    success = set_prefix(guild_id, new_prefix)
                else:
                    print(f'[fix_prefixes] Fixing prefix \'{prefix}\' for guild with id \'{guild_id}\'. New prefix is: \'{settings.PREFIX_DEFAULT}\'')
                    success = reset_prefix(guild_id)
                if not success:
                    all_success = False
    return all_success


def get_autodaily_settings(bot: discord.ext.commands.Bot, guild_id: int = None, can_post: bool = None, without_latest_message_id: bool = False) -> List[AutoDailySettings]:
    db_autodaily_settings = db_get_autodaily_settings(guild_id=guild_id, can_post=can_post, without_latest_message_id=without_latest_message_id, only_guild_ids=True)
    result = []
    for db_autodaily_setting in db_autodaily_settings:
        guild_id = db_autodaily_setting[0]
        if guild_id:
            autodaily_setting = create_autodaily_settings(bot, guild_id)
            result.append(autodaily_setting)
    return result


def get_daily_channel_mention(ctx: discord.ext.commands.Context) -> str:
    channel_id = db_get_daily_channel_id(ctx.guild.id)
    if channel_id is not None:
        text_channel = ctx.bot.get_channel(channel_id)
        if text_channel:
            channel_name = text_channel.mention
        else:
            channel_name = '_<deleted channel>_'
    else:
        channel_name = None
    return channel_name


def get_daily_channel_name(ctx: discord.ext.commands.Context) -> str:
    channel_id = db_get_daily_channel_id(ctx.guild.id)
    if channel_id is not None:
        text_channel = ctx.bot.get_channel(channel_id)
        if text_channel:
            channel_name = text_channel.name
        else:
            channel_name = '<deleted channel>'
    else:
        channel_name = '<not set>'
    return channel_name


def get_daily_notify_settings(ctx: discord.ext.commands.Context) -> str:
    notify_id, notify_type = db_get_daily_notify_settings(ctx.guild.id)
    if notify_id is not None and notify_type is not None:
        type_str = ''
        name = ''
        if notify_type == AutoDailyNotifyType.USER:
            member: discord.Member = ctx.guild.get_member(notify_id)
            name = f'{member.nick} ({member.name})'
            type_str = 'user'
        elif notify_type == AutoDailyNotifyType.ROLE:
            role: discord.Role = ctx.guild.get_role(notify_id)
            name = role.name
            type_str = 'role'

        if type_str and name:
            result = f'{name} ({type_str})'
        else:
            result = f'An error occured on retrieving the notify settings. Please contact the bot\'s author (in `/about`).'
    else:
        result = '<not set>'
    return result


def get_prefix(bot: discord.ext.commands.Bot, message: discord.Message) -> str:
    result = None
    if util.is_guild_channel(message.channel):
        result = get_prefix_or_default(message.channel.guild.id)
    else:
        result = settings.PREFIX_DEFAULT
    return result


def get_prefix_or_default(guild_id: int) -> str:
    result = db_get_prefix(guild_id)
    if result is None or result.lower() == 'none':
        result = settings.PREFIX_DEFAULT
    return result


def get_pagination_mode(guild_id: int) -> str:
    use_pagination_mode = db_get_use_pagination(guild_id)
    result = convert_to_on_off(use_pagination_mode)
    return result


def reset_prefix(guild_id: int) -> bool:
    success = db_reset_prefix(guild_id)
    return success


def reset_daily_delete_on_change(guild_id: int) -> bool:
    success = db_reset_daily_delete_on_change(guild_id)
    return success


def set_autodaily_notify(guild_id: int, notify_id: int, notify_type: AutoDailyNotifyType) -> bool:
    db_create_server_settings(guild_id)

    success = db_update_daily_notify_settings(guild_id, notify_id, notify_type)
    return success


def set_pagination(guild_id: int, switch: str) -> bool:
    db_create_server_settings(guild_id)

    if switch is None:
        return toggle_use_pagination(guild_id)
    else:
        pss_assert.valid_parameter_value(switch, 'switch', min_length=1, allowed_values=_VALID_PAGINATION_SWITCH_VALUES.keys(), case_sensitive=False)
        use_pagination = convert_from_on_off(switch)
        success = db_update_use_pagination(guild_id, use_pagination)
        if success:
            return use_pagination
        else:
            return not use_pagination


def set_prefix(guild_id: int, prefix: str) -> bool:
    db_create_server_settings(guild_id)
    success = db_update_prefix(guild_id, prefix)
    return success


def toggle_daily_delete_on_change(guild_id: int) -> bool:
    db_create_server_settings(guild_id)
    delete_on_change = db_get_daily_delete_on_change(guild_id)
    if delete_on_change is True:
        new_value = None
    elif delete_on_change is False:
        new_value = True
    else:
        new_value = False
    success = db_update_daily_delete_on_change(guild_id, new_value)
    if success:
        return new_value
    else:
        return delete_on_change


def toggle_use_pagination(guild_id: int) -> bool:
    db_create_server_settings(guild_id)
    use_pagination = db_get_use_pagination(guild_id)
    success = db_update_use_pagination(guild_id, not use_pagination)
    if success:
        return not use_pagination
    else:
        return use_pagination













# ---------- DB functions ----------

def db_create_server_settings(guild_id: int) -> bool:
    if db_get_has_settings(guild_id):
        return True
    else:
        query = f'INSERT INTO serversettings (guildid, dailydeleteonchange) VALUES ({guild_id}, {util.db_convert_boolean(True)})'
        success = core.db_try_execute(query)
        return success


def db_delete_server_settings(guild_id: int) -> bool:
    where = util.db_get_where_string('guildid', guild_id, is_text_type=True)
    query = f'DELETE FROM serversettings WHERE {where}'
    success = core.db_try_execute(query)
    return success


def db_get_autodaily_settings(guild_id: int = None, can_post: bool = None, without_latest_message_id: bool = False, only_guild_ids: bool = False) -> list:
    wheres = ['(dailychannelid IS NOT NULL or dailynotifyid IS NOT NULL)']
    if guild_id is not None:
        wheres.append(util.db_get_where_string('guildid', util.db_convert_text(str(guild_id))))
    if can_post is not None:
        wheres.append(util.db_get_where_string('dailycanpost', util.db_convert_boolean(can_post)))
    if without_latest_message_id is True:
        wheres.append(util.db_get_where_string('dailylatestmessageid', None))
    if only_guild_ids:
        setting_names = ['guildid']
    else:
        setting_names = ['guildid', 'dailychannelid', 'dailycanpost', 'dailylatestmessageid', 'dailydeleteonchange', 'dailynotifyid', 'dailynotifytype']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names, additional_wheres=wheres)
    result = []
    for setting in settings:
        if only_guild_ids:
            intermediate = [util.db_convert_to_int(setting[0])]
            intermediate.extend([None] * (__AUTODAILY_SETTING_COUNT - 1))
            result.append(tuple(intermediate))
        else:
            result.append((
                util.db_convert_to_int(setting[0]),
                util.db_convert_to_int(setting[1]),
                util.db_convert_to_boolean(setting[2]),
                util.db_convert_to_int(setting[3]),
                util.db_convert_to_boolean(setting[4]),
                util.db_convert_to_int(setting[5]),
                convert_to_autodaily_notify_type(setting[6])
            ))
    if not result:
        if guild_id:
            intermediate = [guild_id]
            intermediate.extend([None] * (__AUTODAILY_SETTING_COUNT - 1))
            result.append(tuple(intermediate))
        else:
            result.append(tuple([None] * __AUTODAILY_SETTING_COUNT))
    return result


def db_get_daily_channel_id(guild_id: int) -> int:
    setting_names = ['dailychannelid']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return util.db_convert_to_int(setting[0])
    else:
        return None


def db_get_daily_can_post(guild_id: int) -> bool:
    setting_names = ['dailycanpost']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return util.db_convert_to_boolean(setting[0])
    else:
        return None


def db_get_daily_delete_on_change(guild_id: int) -> bool:
    setting_names = ['dailydeleteonchange']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            result = util.db_convert_to_boolean(setting[0])
            return result
    else:
        return None


def db_get_daily_latest_message_id(guild_id: int) -> int:
    setting_names = ['dailylatestmessageid']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return util.db_convert_to_int(setting[0])
    else:
        return None


def db_get_daily_notify_settings(guild_id: int) -> (int, AutoDailyNotifyType):
    setting_names = ['dailynotifyid', 'dailynotifytype']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return (util.db_convert_to_int(setting[0]), convert_to_autodaily_notify_type(util.db_convert_to_int(setting[1])))
    else:
        return (None, None)


def db_get_has_settings(guild_id: int) -> bool:
    results = _db_get_server_settings(guild_id)
    if results:
        return True
    else:
        return False


def db_get_prefix(guild_id: int) -> str:
    setting_names = ['prefix']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return str(setting[0])
    else:
        return None


def db_get_use_pagination(guild_id: int) -> bool:
    setting_names = ['usepagination']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return util.db_convert_to_boolean(setting[0], default_if_none=True)
    else:
        return None


def db_reset_autodaily_channel(guild_id: int) -> bool:
    current_autodaily_settings = db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailychannelid': 'NULL',
                'dailycanpost': 'NULL',
                'dailylatestmessageid': 'NULL',
            }
            success = _db_update_server_setting(guild_id, settings)
            return success
    return True


def db_reset_autodaily_latest_message_id(guild_id: int) -> bool:
    current_autodaily_settings = db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailylatestmessageid': 'NULL',
            }
            success = _db_update_server_setting(guild_id, settings)
            return success
    return True


def db_reset_autodaily_mode(guild_id: int) -> bool:
    current_autodaily_settings = db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailydeleteonchange': 'NULL'
            }
            success = _db_update_server_setting(guild_id, settings)
            return success
    return True


def db_reset_autodaily_notify(guild_id: int) -> bool:
    current_autodaily_settings = db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailynotifyid': 'NULL',
                'dailynotifytype': 'NULL'
            }
            success = _db_update_server_setting(guild_id, settings)
            return success
    return True


def db_reset_autodaily_settings(guild_id: int) -> bool:
    current_autodaily_settings = db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailychannelid': 'NULL',
                'dailycanpost': 'NULL',
                'dailylatestmessageid': 'NULL',
                'dailydeleteonchange': 'NULL',
                'dailynotifyid': 'NULL',
                'dailynotifytype': 'NULL'
            }
            success = _db_update_server_setting(guild_id, settings)
            return success
    return True


def db_reset_daily_delete_on_change(guild_id: int) -> bool:
    success = db_update_daily_delete_on_change(guild_id, None)
    return success


def db_reset_daily_notify_settings(guild_id: int) -> bool:
    success = db_update_daily_notify_settings(guild_id, None, None)
    return success


def db_reset_prefix(guild_id: int) -> bool:
    current_prefix = db_get_prefix(guild_id)
    if current_prefix is not None:
        settings = {
            'prefix': 'NULL'
        }
        success = _db_update_server_setting(guild_id, settings)
        return success
    return True


def db_reset_use_pagination(guild_id: int) -> bool:
    current_use_pagination = db_get_use_pagination(guild_id)
    if current_use_pagination is not None:
        settings = {
            'usepagination': 'NULL'
        }
        success = _db_update_server_setting(guild_id, settings)
        return success
    return True


def db_update_autodaily_settings(guild_id: int, channel_id: int = None, can_post: bool = None, latest_message_id: int = None, delete_on_change: bool = None, notify_id: int = None, notify_type: AutoDailyNotifyType = None) -> bool:
    autodaily_settings = db_get_autodaily_settings(guild_id)
    current_channel_id = None
    current_can_post = None
    current_latest_message_id = None
    current_delete_on_change = None
    current_notify_id = None
    current_notify_type = None
    if autodaily_settings:
        (_, current_channel_id, current_can_post, current_latest_message_id, current_delete_on_change, current_notify_id, current_notify_type) = autodaily_settings[0]
    if (current_channel_id != channel_id
            or current_can_post != can_post
            or current_latest_message_id != latest_message_id
            or current_delete_on_change != delete_on_change
            or current_notify_id != notify_id
            or current_notify_type != notify_type):
        settings = {}
        if channel_id is not None:
            settings['dailychannelid'] = util.db_convert_text(channel_id)
        if can_post is not None:
            settings['dailycanpost'] = util.db_convert_to_boolean(can_post)
        if latest_message_id is not None:
            settings['dailylatestmessageid'] = util.db_convert_text(latest_message_id)
        if delete_on_change is not None:
            settings['dailydeleteonchange'] = util.db_convert_to_boolean(delete_on_change)
        if notify_id is not None:
            settings['dailynotifyid'] = util.db_convert_text(notify_id)
        if notify_type is not None:
            settings['dailynotifytype'] = util.db_convert_text(convert_from_autodaily_notify_type(notify_type))
        success = not settings or _db_update_server_setting(guild_id, settings)
        return success
    return True


def db_update_daily_can_post(guild_id: int, can_post: bool) -> bool:
    current_daily_can_post = db_get_daily_channel_id(guild_id)
    if not current_daily_can_post or can_post != current_daily_can_post:
        settings = {
            'dailycanpost': util.convert_to_boolean(can_post),
        }
        success = _db_update_server_setting(guild_id, settings)
        return success
    return True


def db_update_daily_channel_id(guild_id: int, channel_id: int) -> bool:
    current_daily_channel_id = db_get_daily_channel_id(guild_id)
    if not current_daily_channel_id or channel_id != current_daily_channel_id:
        settings = {
            'dailychannelid': util.db_convert_text(channel_id),
            'dailycanpost': util.convert_to_boolean(True),
            'dailylatestmessageid': 'NULL'
        }
        success = _db_update_server_setting(guild_id, settings)
        return success
    return True


def db_update_daily_delete_on_change(guild_id: int, delete_on_change: bool) -> bool:
    current_daily_delete_on_change = db_get_daily_delete_on_change(guild_id)
    if not current_daily_delete_on_change or delete_on_change != current_daily_delete_on_change:
        settings = {
            'dailydeleteonchange': util.db_convert_boolean(delete_on_change),
        }
        success = _db_update_server_setting(guild_id, settings)
        return success
    return True


def db_update_daily_latest_message_id(guild_id: int, message_id: int) -> bool:
    current_daily_latest_message_id = db_get_daily_latest_message_id(guild_id)
    if not current_daily_latest_message_id or message_id != current_daily_latest_message_id:
        settings = {
            'dailylatestmessageid': util.db_convert_text(message_id)
        }
        success = _db_update_server_setting(guild_id, settings)
        return success
    return True


def db_update_daily_notify_settings(guild_id: int, notify_id: int, notify_type: AutoDailyNotifyType) -> bool:
    current_daily_notify_id, _ = db_get_daily_notify_settings(guild_id)
    if not current_daily_notify_id or notify_id != current_daily_notify_id:
        settings = {
            'dailynotifyid': util.db_convert_text(notify_id),
            'dailynotifytype': util.db_convert_text(convert_from_autodaily_notify_type(notify_type))
        }
        success = _db_update_server_setting(guild_id, settings)
        return success
    return True


def db_update_prefix(guild_id: int, prefix: str) -> bool:
    current_prefix = db_get_prefix(guild_id)
    if not current_prefix or prefix != current_prefix:
        settings = {
            'prefix': util.db_convert_text(prefix)
        }
        success = _db_update_server_setting(guild_id, settings)
        return success
    return True


def db_update_use_pagination(guild_id: int, use_pagination: bool) -> bool:
    current_use_pagination = db_get_use_pagination(guild_id)
    if not current_use_pagination or use_pagination != current_use_pagination:
        settings = {
            'usepagination': util.db_convert_boolean(use_pagination)
        }
        success = _db_update_server_setting(guild_id, settings)
        return success
    return True










# ---------- Utilities ----------

def _db_get_server_settings(guild_id: int = None, setting_names: list = None, additional_wheres: list = []) -> list:
    wheres = []
    if guild_id is not None:
        wheres.append(util.db_get_where_string('guildid', guild_id, is_text_type=True))

    if setting_names:
        setting_string = ', '.join(setting_names)
    else:
        setting_string = '*'

    if additional_wheres:
        wheres.extend(additional_wheres)

    where = util.db_get_where_and_string(wheres)
    if where:
        query = f'SELECT {setting_string} FROM serversettings WHERE {where}'
    else:
        query = f'SELECT {setting_string} FROM serversettings'
    rows = core.db_fetchall(query)
    if rows:
        return rows
    else:
        return []


def _db_reset_server_setting(guild_id: int, settings: dict) -> bool:
    where = util.db_get_where_string('guildid', guild_id, is_text_type=True)
    set_string = ', '.join([f'{key} = NULL' for key in settings.keys()])
    query = f'UPDATE serversettings SET {set_string} WHERE {where}'
    success = core.db_try_execute(query)
    return success


def _db_update_server_setting(guild_id: int, settings: dict) -> bool:
    where = util.db_get_where_string('guildid', guild_id, is_text_type=True)
    set_string = ', '.join([f'{key} = {value}' for key, value in settings.items()])
    query = f'UPDATE serversettings SET {set_string} WHERE {where}'
    success = core.db_try_execute(query)
    return success









# ---------- Main ----------

fix_prefixes()