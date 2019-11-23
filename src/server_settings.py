import pss_core as core
import utility as util

def get_server_settings(guild_id) -> tuple:
    # TODO: get server settings
    pass

# TODO: add functions for getting AND storing individual settings


def toggle_use_pagination(guild_id: int) -> bool:
    if not db_get_has_settings(guild_id):
        db_create_server_settings(guild_id)
    use_pagination = db_get_use_pagination(guild_id)
    success = db_update_use_pagination(guild_id, not use_pagination)
    if success:
        return not use_pagination
    else:
        return use_pagination


def convert_use_pagination(use_pagination: bool) -> str:
    if use_pagination is True:
        return 'ON'
    elif use_pagination is False:
        return 'OFF'
    else:
        return '<NOT SET>'











# ---------- DB functions ----------

def db_create_server_settings(guild_id: int) -> bool:
    query = f'INSERT INTO serversettings (guildid) VALUES ({guild_id})'
    success = core.db_try_execute(query)
    return success


def db_get_daily_channel_id(guild_id: int) -> int:
    setting_names = ['dailychannelid']
    settings = _db_get_server_settings(guild_id, setting_names=setting_names)
    if settings:
        for setting in settings:
            return util.db_convert_to_int(setting[0][0])
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
    wheres = []
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
            'dailychannelid': channel_id,
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
            'dailylatestmessageid': message_id
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
    query = f'SELECT {setting_string} FROM serversettings WHERE {where}'
    rows = core.db_fetchall(query)
    if rows:
        return rows
    else:
        return None


def _db_update_server_setting(guild_id: int, settings: dict) -> bool:
    where = util.db_get_where_string('guildid', guild_id, is_text_type=True)
    set_string = ', '.join([f'{key} = {value}' for key, value in settings.items()])
    query = f'UPDATE serversettings SET {set_string} WHERE {where}'
    success = core.db_try_execute(query)
    return success
