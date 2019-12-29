#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime
import discord
import os
import random

import pss_core as core
import server_settings
import utility as util










# ---------- Constants ----------

DAILY_INFO_FIELDS = [
    'CargoItems',
    'CargoPrices',
    'CommonCrewId',
    'DailyRewardArgument',
    'DailyItemRewards',
    'DailyRewardType',
    'HeroCrewId',
    'LimitedCatalogArgument',
    'LimitedCatalogCurrencyAmount',
    'LimitedCatalogCurrencyType',
    'LimitedCatalogMaxTotal',
    'LimitedCatalogType',
    'News',
    'SaleArgument',
    'SaleItemMask',
    'SaleQuantity',
    'SaleType'
]










# ---------- ----------

def try_store_daily_channel(guild_id: int, text_channel_id: int) -> bool:
    success = False
    rows = server_settings.db_get_autodaily_settings(guild_id=guild_id, can_post=None)
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
    rows = server_settings.db_get_autodaily_settings(guild_id=None, can_post=None)
    if len(rows) == 0:
        return []
    else:
        results = [int(channel_id) for (channel_id, _, _) in rows]
        return results


def get_valid_daily_channel_ids() -> list:
    rows = server_settings.db_get_autodaily_settings(guild_id=None, can_post=True)
    if len(rows) == 0:
        return []
    else:
        results = [int(channel_id) for (channel_id, _, _) in rows]
        return results


def try_remove_daily_channel(guild_id: int) -> bool:
    success = server_settings.db_reset_autodaily_channel(guild_id)
    if success == False:
        print(f'[try_remove_daily_channel] failed to delete data row with key: {guild_id}')
    return success


def fix_daily_channel(guild_id: int, can_post: bool) -> bool:
    success = update_daily_channel(guild_id, None, can_post)
    return success


def has_daily_changed(daily_info: dict, retrieved_date: datetime) -> bool:
    fields_to_check = [
        'News',
        'LimitedCatalogArgument',
        'LimitedCatalogCurrencyAmount',
        'LimitedCatalogCurrencyType',
        'LimitedCatalogMaxTotal',
        'LimitedCatalogType',
        'SaleArgument',
        'SaleItemMask',
        'SaleQuantity',
        'SaleType'
    ]
    daily_info_cache, cache_modify_date = db_get_daily_info()
    if retrieved_date.day > cache_modify_date.day:
        for daily_info_field in fields_to_check:
            if daily_info[daily_info_field] != daily_info_cache[daily_info_field]:
                return True
    else:
        return not util.dicts_equal(daily_info, daily_info_cache)










# ---------- Utilities ----------

def convert_to_daily_info(dropship_info: dict) -> dict:
    result = {}
    for field_name in DAILY_INFO_FIELDS:
        value = None
        if field_name in dropship_info.keys():
            value = dropship_info[field_name]
        result[field_name] = value
    return result


def delete_daily_channel(guild_id: int) -> bool:
    success = server_settings.db_reset_autodaily_channel(guild_id)
    return success


def get_daily_channels(ctx: discord.ext.commands.Context, guild_id: int = None, can_post: bool = None) -> list:
    channels = server_settings.db_get_autodaily_settings(guild_id, can_post)
    result = []
    at_least_one = False
    for (channel_id, can_post, _) in channels:
        if channel_id:
            at_least_one = True
            text_channel = ctx.bot.get_channel(int(channel_id))
            if text_channel:
                guild = text_channel.guild
                result.append(f'{guild.name}: #{text_channel.name} ({can_post})')
            else:
                result.append(f'Invalid channel id: {channel_id}')
    if not at_least_one:
        result.append('Auto-posting of the daily announcement is not configured for any server!')
    return result


def get_daily_info():
    latest_settings = core.get_latest_settings()
    result = convert_to_daily_info(latest_settings)
    return result


def get_daily_info_setting_name(field_name: str) -> str:
    return f'daily{field_name}'


def insert_daily_channel(guild_id: int, channel_id: int) -> bool:
    success = server_settings.db_create_server_settings(guild_id)
    if success:
        success = update_daily_channel(guild_id, channel_id=channel_id, can_post=True, latest_message_id=None)
    return success


def remove_duplicate_autodaily_settings(autodaily_settings: list) -> list:
    if not autodaily_settings:
        return autodaily_settings
    result = {}
    for autodaily_setting in autodaily_settings:
        guild_id = autodaily_setting[0]
        if guild_id not in result.keys():
            result[guild_id] = autodaily_setting
    return list(result.values())


def update_daily_channel(guild_id: int, channel_id: int = None, can_post: bool = True, latest_message_id: int = None) -> bool:
    success = True
    if channel_id is not None:
        success = success and server_settings.db_update_daily_channel_id(guild_id, channel_id)
    if can_post is not None:
        success = success and server_settings.db_update_daily_can_post(guild_id, can_post)
    if latest_message_id is not None:
        success = success and server_settings.db_update_daily_latest_message_id(guild_id, latest_message_id)
    return success


def db_get_daily_info() -> (dict, datetime):
    result = {}
    modify_dates = []
    for daily_info_field in DAILY_INFO_FIELDS:
        setting_name = get_daily_info_setting_name(daily_info_field)
        value, modify_date = core.db_get_setting(setting_name)
        if modify_date:
            modify_dates.append(modify_date)
        if value:
            result[daily_info_field] = value
    if result and modify_dates:
        return (result, max(modify_dates))
    else:
        return ({}, None)


def db_set_daily_info(daily_info: dict, utc_now: datetime) -> bool:
    result = True
    for key, value in daily_info.items():
        setting_name = get_daily_info_setting_name(key)
        result = core.db_set_setting(setting_name, value, utc_now=utc_now) and result
    return result










# ---------- Mocks ----------

def mock_get_daily_info():
    utc_now = util.get_utcnow()
    if utc_now.hour < 1:
        return __mock_get_daily_info_1()
    elif utc_now.hour < 2:
        return __mock_get_daily_info_2()
    else:
        return __mock_get_daily_info_1()


def __mock_get_daily_info_1():
    result = {
        'CargoItems': f'{random.randint(0, 200)}x{random.randint(0, 10)}',
        'CargoPrices': f'starbux:{random.randint(0, 10)}',
        'CommonCrewId': f'{random.randint(0, 200)}',
        'DailyItemRewards': f'{random.randint(0, 200)}x1|{random.randint(0, 200)}x1',
        'DailyRewardArgument': f'{random.randint(0, 20)}',
        'DailyRewardType': 'Starbux',
        'HeroCrewId': f'{random.randint(0, 200)}',
        'LimitedCatalogArgument': '183',
        'LimitedCatalogCurrencyAmount': '650',
        'LimitedCatalogCurrencyType': 'Starbux',
        'LimitedCatalogMaxTotal': '100',
        'LimitedCatalogType': 'Item',
        'News': '...',
        'SaleArgument': '344',
        'SaleItemMask': '2',
        'SaleType': 'Character'
    }
    return result


def __mock_get_daily_info_2():
    result = {
        'CargoItems': f'{random.randint(0, 200)}x{random.randint(0, 10)}',
        'CargoPrices': f'starbux:{random.randint(0, 10)}',
        'CommonCrewId': f'{random.randint(0, 200)}',
        'DailyItemRewards': f'{random.randint(0, 200)}x1|{random.randint(0, 200)}x1',
        'DailyRewardArgument': f'{random.randint(0, 20)}',
        'DailyRewardType': 'Starbux',
        'HeroCrewId': f'{random.randint(0, 200)}',
        'LimitedCatalogArgument': f'{random.randint(0, 200)}',
        'LimitedCatalogCurrencyAmount': f'{random.randint(0, 20000)}',
        'LimitedCatalogCurrencyType': 'Starbux',
        'LimitedCatalogMaxTotal': '100',
        'LimitedCatalogType': random.choice(['Item', 'Character']),
        'News': '...',
        'SaleArgument': f'{random.randint(0, 200)}',
        'SaleItemMask': f'{random.randint(1, 31)}',
        'SaleType': random.choice(['Item', 'Character'])
    }
    return result

