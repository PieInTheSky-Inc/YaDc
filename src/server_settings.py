import discord

import pss_assert
import pss_core as core
import settings
import utility as util



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


def convert_to_on_off(value: bool) -> str:
    if value is True:
        return 'ON'
    elif value is False:
        return 'OFF'
    else:
        return '<NOT SET>'


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


def set_pagination(guild_id: int, switch: str) -> bool:
    if not db_get_has_settings(guild_id):
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
    if not db_get_has_settings(guild_id):
        db_create_server_settings(guild_id)
    success = db_update_prefix(guild_id, prefix)
    return success


def toggle_use_pagination(guild_id: int) -> bool:
    if not db_get_has_settings(guild_id):
        db_create_server_settings(guild_id)
    use_pagination = db_get_use_pagination(guild_id)
    success = db_update_use_pagination(guild_id, not use_pagination)
    if success:
        return not use_pagination
    else:
        return use_pagination













# ---------- DB functions ----------

def db_create_server_settings(guild_id: int) -> bool:
    query = f'INSERT INTO serversettings (guildid) VALUES ({guild_id})'
    success = core.db_try_execute(query)
    return success


def db_delete_server_settings(guild_id: int) -> bool:
    where = util.db_get_where_string('guildid', guild_id, is_text_type=True)
    query = f'DELETE FROM serversettings WHERE {where}'
    success = core.db_try_execute(query)
    return success


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


def db_get_autodaily_settings(guild_id: int = None, can_post: bool = None) -> list:
    wheres = ['dailychannelid IS NOT NULL']
    if can_post is not None:
        wheres.append(util.db_get_where_string('dailycanpost', util.db_convert_boolean(can_post)))
    setting_names = ['dailychannelid', 'dailycanpost', 'dailylatestmessageid']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names, additional_wheres=wheres)
    if settings:
        result = []
        for setting in settings:
            result.append((util.db_convert_to_int(setting[0]), util.db_convert_to_boolean(setting[1]), util.db_convert_to_int(setting[2])))
        return result
    else:
        return [(None, None, None)]


def db_get_daily_latest_message_id(guild_id: int) -> int:
    setting_names = ['dailylatestmessageid']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return util.db_convert_to_int(setting[0])
    else:
        return None


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


def db_reset_autodaily_settings(guild_id: int) -> bool:
    current_autodaily_settings = db_get_autodaily_settings(guild_id)
    for current_setting in current_autodaily_settings:
        if current_setting is not None:
            settings = {
                'dailychannelid': 'NULL',
                'dailycanpost': 'NULL',
                'dailylatestmessageid': 'NULL'
            }
            success = _db_update_server_setting(guild_id, settings)
            return success
    return True


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


def db_update_autodaily_settings(guild_id: int, channel_id: int = None, can_post: bool = None, latest_message_id: int = None) -> bool:
    (current_channel_id, current_can_post, current_latest_message_id) = db_get_autodaily_settings(guild_id)
    if not current_channel_id or not current_can_post or not current_latest_message_id or current_channel_id != channel_id or current_can_post != can_post or current_latest_message_id != latest_message_id:
        settings = {
            'dailychannelid': util.db_convert_text(channel_id),
            'dailycanpost': util.db_convert_to_boolean(can_post),
            'dailylatestmessageid': util.db_convert_text(latest_message_id)
        }
        success = _db_update_server_setting(guild_id, settings)
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


def db_update_daily_latest_message_id(guild_id: int, message_id: int) -> bool:
    current_daily_latest_message_id = db_get_daily_latest_message_id(guild_id)
    if not current_daily_latest_message_id or message_id != current_daily_latest_message_id:
        settings = {
            'dailylatestmessageid': util.db_convert_text(message_id)
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
        return None


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