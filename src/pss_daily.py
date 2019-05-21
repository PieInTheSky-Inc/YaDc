#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import pss_core as core
import utility as util

DAILY_TABLE_NAME = 'Daily'


def try_store_daily_channel(guild_id, text_channel_id):
    success = False
    rows = select_daily_channel(guild_id, None)
    if len(rows) == 0:
        success = insert_daily_channel(guild_id, text_channel_id)
        if success == False:
            print('[try_store_daily_channel] failed to insert new data row: {} ({})'.format(guild_id, text_channel_id))
    else:
        if str(rows[0][1]) != str(text_channel_id):
            success = update_daily_channel(guild_id, text_channel_id, True)
            if success == False:
                print('[try_store_daily_channel] failed to update data row: {} ({})'.format(guild_id, text_channel_id))
        else:
            success = True
    return success

        
def get_daily_channel_id(guild_id):
    rows = select_daily_channel(guild_id, None)
    if len(rows) == 0:
        return -1
    else:
        result = rows[0][1]
        return int(result)
    
    
def get_all_daily_channels():
    print('+ called get_all_daily_channels()')
    rows = select_daily_channel(None, None)
    if rows:
        print('[get_all_daily_channels] retrieved {} daily channels: {}'.format(len(rows), rows))
        print('- exiting get_all_daily_channels, returning: {}'.format(rows))
        return rows
    else:
        print('[get_all_daily_channels] retrieved 0 daily channels.')
        print('- exiting get_all_daily_channels, returning: {}'.format([]))
        return []
    
    
def get_all_daily_channel_ids():
    rows = get_all_daily_channels()
    if not rows or len(rows) == 0:
        return []
    else:
        results = [int(t[1]) for t in rows]
        return results
    
    
def get_valid_daily_channels():
    rows = select_daily_channel(None, True)
    if rows:
        return rows
    else:
        return []
    
    
def get_valid_daily_channel_ids():
    rows = get_valid_daily_channels()
    if not rows or len(rows) == 0:
        return []
    else:
        results = [int(t[1]) for t in rows]
        return results

    
def try_remove_daily_channel(guild_id):
    rows = select_daily_channel(guild_id)
    success = False
    if len(rows) == 0:
        print('[try_remove_daily_channel] key not in db: {}'.format(guild_id))
    else:
        success = delete_daily_channel(guild_id)
        if success == False:
            print('[try_remove_daily_channel] failed to delete data row with key: {}'.format(guild_id))
    return success

            
def fix_daily_channel(guild_id, can_post):
    success = update_daily_channel(guild_id, None, util.db_convert_boolean(can_post))
    return success

    
# ---------- Utilities ----------
def delete_daily_channel(guild_id):
    query = 'DELETE FROM daily WHERE guildid = \'{}\''.format(guild_id)
    success = core.db_try_execute(query)
    return success
    
def insert_daily_channel(guild_id, channel_id):
    query = 'INSERT INTO daily (guildid, channelid, canpost) VALUES ({},{},TRUE)'.format(guild_id, channel_id)
    success = core.db_try_execute(query)
    return success

def select_daily_channel(guild_id=None, can_post=None):
    where = []
    if guild_id:
        where_guild_id = util.db_get_where_string('guildid', guild_id, True)
        where.append(where_guild_id)
    if can_post != None:
        can_post_converted = util.db_convert_boolean(can_post)
        where_can_post = util.db_get_where_string('canpost', can_post_converted)
        where.append(where_can_post)
    result = core.db_select_any_from_where_and(DAILY_TABLE_NAME, where)
    return result
    
def update_daily_channel(guild_id, channel_id=None, can_post=True, latest_message_id=None):
    can_post_converted = util.db_convert_boolean(can_post)
    set_strings = [util.db_get_where_string('canpost', can_post_converted)]
    if channel_id:
        set_strings.append(util.db_get_where_string('channelid', channel_id, True))
    if latest_message_id:
        set_strings.append(util.db_get_where_string('latestmessageid', latest_message_id, True))
    set_string = ', '.join(set_strings)
    query = 'UPDATE {} SET {} WHERE {}'.format(DAILY_TABLE_NAME, set_string, util.db_get_where_string('guildid', guild_id, True))
    success = core.db_try_execute(query)
    return success
