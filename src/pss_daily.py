#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import discord
import os

import pss_core as core
import server_settings
import utility as util


def try_store_daily_channel(guild_id: int, text_channel_id: int) -> bool:
    success = False
    rows = server_settings.db_get_daily_channels(guild_id, None)
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
    rows = server_settings.db_get_daily_channel_id(guild_id)
    if len(rows) == 0:
        return -1
    else:
        result = rows[0][1]
        return int(result)


def get_all_daily_channel_ids() -> list:
    rows = server_settings.db_get_daily_channels(None, None)
    if len(rows) == 0:
        return []
    else:
        results = [int(t[1]) for t in rows]
        return results


def get_valid_daily_channel_ids() -> list:
    rows = server_settings.db_get_daily_channels(None, True)
    if len(rows) == 0:
        return []
    else:
        results = [int(t[1]) for t in rows]
        return results


def try_remove_daily_channel(guild_id: int) -> bool:
    rows = server_settings.db_get_daily_channels(guild_id)
    success = False
    if len(rows) == 0:
        print(f'[try_remove_daily_channel] key not in db: {guild_id}')
    else:
        success = delete_daily_channel(guild_id)
        if success == False:
            print(f'[try_remove_daily_channel] failed to delete data row with key: {guild_id}')
    return success


def fix_daily_channel(guild_id: int, can_post: bool) -> bool:
    success = update_daily_channel(guild_id, None, can_post)
    return success










# ---------- Utilities ----------

def delete_daily_channel(guild_id: int) -> bool:
    success = server_settings.db_reset_autodaily_settings(guild_id)
    return success


def insert_daily_channel(guild_id: int, channel_id: int) -> bool:
    success = server_settings.db_create_server_settings(guild_id)
    if success:
        success = update_daily_channel(guild_id, channel_id=channel_id, can_post=True, latest_message_id=None)
    return success


def get_daily_channels(ctx: discord.ext.commands.Context, guild_id: int = None, can_post: bool = None) -> list:
    channels = server_settings.db_get_daily_channels(guild_id, can_post)
    result = []
    for channel in channels:
        text_channel = ctx.bot.get_channel(int(channel[1]))
        if text_channel:
            guild = text_channel.guild
            result.append(f'{guild.name}: #{text_channel.name} ({channel[2]})')
        else:
            result.append(f'Invalid channel id: {channel[1]}')
    if not result:
        result.append('Auto-posting of the daily announcement is not configured for any server!')
    return result


def update_daily_channel(guild_id: int, channel_id: int = None, can_post: bool = True, latest_message_id: int = None) -> bool:
    success = True
    if channel_id is not None:
        success = success and server_settings.db_update_daily_channel_id(guild_id, channel_id)
    if can_post is not None:
        success = success and server_settings.db_update_daily_can_post(guild_id, can_post)
    if latest_message_id is not None:
        success = success and server_settings.db_update_daily_latest_message_id(guild_id, latest_message_id)
    return success
