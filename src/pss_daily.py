#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import pss_core as core

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


def get_all_daily_channel_ids():
    rows = select_daily_channel(None, None)
    if len(rows) == 0:
        return []
    else:
        results = [int(t[1]) for t in rows]
        return results


def get_valid_daily_channel_ids():
    rows = select_daily_channel(None, True)
    if len(rows) == 0:
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
    success = update_daily_channel(guild_id, None, convert_can_post(can_post))
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

def select_daily_channel(guild_id = None, can_post = None):
    query = 'SELECT * FROM daily'
    if guild_id:
        query += ' WHERE guildid = \'{}\''.format(guild_id)
        if can_post != None:
            query += ' AND canpost = {}'.format(convert_can_post(can_post))
    if can_post != None:
        query += ' WHERE canpost = {}'.format(convert_can_post(can_post))
    result = core.db_fetchall(query)
    return result

def update_daily_channel(guild_id, channel_id = None, can_post = True):
    query = 'UPDATE daily SET '
    if channel_id != None:
        query += 'channelid = \'{}\', '.format(channel_id)
    query += 'canpost = {} WHERE guildid = \'{}\''.format(convert_can_post(can_post), guild_id)
    success = core.db_try_execute(query)
    return success

def convert_can_post(can_post):
    if can_post:
        return 'TRUE'
    else:
        return 'FALSE'
