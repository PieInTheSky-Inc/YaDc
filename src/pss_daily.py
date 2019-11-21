#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os

import pss_core as core
import server_settings
import utility as util


def try_store_daily_channel(guild_id: int, text_channel_id: int) -> bool:
    success = False
    rows = select_daily_channel(guild_id, None)
    if len(rows) == 0:
        success = insert_daily_channel(guild_id, text_channel_id)
        if success == False:
            print(f'[try_store_daily_channel] failed to insert new data row: {guild_id} ({text_channel_id})')
    else:
        if str(rows[0][1]) != str(text_channel_id):
            success = update_daily_channel(guild_id, text_channel_id, True)
            if success == False:
                print(f'[try_store_daily_channel] failed to update data row: {guild_id} ({text_channel_id})')
        else:
            success = True
    return success


def get_daily_channel_id(guild_id: int) -> int:
    rows = select_daily_channel(guild_id, None)
    if len(rows) == 0:
        return -1
    else:
        result = rows[0][1]
        return int(result)


def get_all_daily_channel_ids() -> list:
    rows = select_daily_channel(None, None)
    if len(rows) == 0:
        return []
    else:
        results = [int(t[1]) for t in rows]
        return results


def get_valid_daily_channel_ids() -> list:
    rows = select_daily_channel(None, True)
    if len(rows) == 0:
        return []
    else:
        results = [int(t[1]) for t in rows]
        return results


def try_remove_daily_channel(guild_id: int) -> bool:
    rows = select_daily_channel(guild_id)
    success = False
    if len(rows) == 0:
        print(f'[try_remove_daily_channel] key not in db: {guild_id}')
    else:
        success = delete_daily_channel(guild_id)
        if success == False:
            print(f'[try_remove_daily_channel] failed to delete data row with key: {guild_id}')
    return success


def fix_daily_channel(guild_id: int, can_post: bool) -> bool:
    success = update_daily_channel(guild_id, None, util.db_convert_boolean(can_post))
    return success










# ---------- Utilities ----------

def delete_daily_channel(guild_id: int) -> bool:
    query = f'DELETE FROM serversettings WHERE guildid = \'{guild_id}\''
    success = core.db_try_execute(query)
    return success


def insert_daily_channel(guild_id: int, channel_id: int) -> bool:
    query = f'INSERT INTO serversettings (guildid, dailychannelid, dailycanpost) VALUES ({guild_id}, {channel_id}, TRUE)'
    success = core.db_try_execute(query)
    return success


def select_daily_channel(guild_id: int = None, can_post: bool = None) -> list:
    query = 'SELECT * FROM serversettings'
    if guild_id:
        query += f' WHERE guildid = \'{guild_id}\''.format()
        if can_post != None:
            query += f' AND canpost = {util.db_convert_boolean(can_post)}'
    if can_post != None:
        query += f' WHERE canpost = {util.db_convert_boolean(can_post)}'
    result = core.db_fetchall(query)
    return result


def update_daily_channel(guild_id: int, channel_id: int = None, can_post: bool = True) -> bool:
    query = 'UPDATE serversettings SET '
    if channel_id != None:
        query += f'channelid = \'{channel_id}\', '
    query += f'dailycanpost = {util.db_convert_boolean(can_post)} WHERE guildid = \'{guild_id}\''
    success = core.db_try_execute(query)
    return success
