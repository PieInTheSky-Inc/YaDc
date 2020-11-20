#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
import discord
from discord.ext import commands
import random
from typing import Callable, Dict, List, Tuple, Union

import database as db
import emojis
import pss_core as core
import pss_entity as entity
import pss_item as item
import pss_crew as crew
import pss_lookups as lookups
import pss_research as research
import pss_room as room
import pss_training as training
import server_settings
import settings
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
    'LimitedCatalogExpiryDate',
    'LimitedCatalogMaxTotal',
    'LimitedCatalogType',
    'News',
    'NewsSpriteId',
    'SaleArgument',
    'SaleItemMask',
    'SaleQuantity',
    'SaleType'
]

DAILY_INFO_FIELDS_TO_CHECK = [
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

SALES_DAILY_INFO_FIELDS = {
    'LimitedCatalogArgument': int,
    'LimitedCatalogCurrencyAmount': int,
    'LimitedCatalogCurrencyType': str,
    'LimitedCatalogExpiryDate': util.parse_pss_datetime,
    'LimitedCatalogMaxTotal': int,
    'LimitedCatalogType': str
}

LATE_SALES_PORTAL_HYPERLINK: str = 'https://pixelstarships.com/PlayerCenter/Sales'

DB_DAILY_INFO_COLUMN_NAMES = {f'daily{setting_name}': setting_name for setting_name in DAILY_INFO_FIELDS}

LIMITED_CATALOG_TYPE_GET_ENTITY_FUNCTIONS: Dict[str, Callable] = {
    'item': item.get_item_details_by_id,
    'character': crew.get_char_details_by_id,
    'research': research.get_research_details_by_id,
    'room': room.get_room_details_by_id
}










# ---------- Sales ----------

async def get_sales_details(ctx: commands.Context, as_embed: bool = settings.USE_EMBEDS) -> Union[List[str], List[discord.Embed]]:
    utc_now = util.get_utcnow()
    db_sales_infos = await db_get_sales_infos(utc_now=utc_now)
    processed_db_sales_infos = await __process_db_sales_infos(db_sales_infos, utc_now)
    sales_infos = [sales_info for sales_info in processed_db_sales_infos if sales_info['expires_in'] >= 0]

    title = 'Expired sales'
    description = f'The things listed below have been sold in the {emojis.pss_shop} shop over the past 30 days. You\'ve got the chance to buy them on the Pixel Starships website for an additional 25% on the original price.'

    if as_embed:
        fields = []
        for sales_info in sales_infos:
            expires_in = sales_info['expires_in']
            day = 'day' + ('' if expires_in == 1 else 's')
            field_name = f'{sales_info["name"]} ({sales_info["type"]})'
            field_value = f'{sales_info["price"]} {sales_info["currency"]}{entity.DEFAULT_DETAILS_PROPERTIES_SEPARATOR}{expires_in} {day}'
            fields.append((field_name, field_value, True))

        colour = util.get_bot_member_colour(ctx.bot, ctx.guild)
        footer = 'Click on the title to get redirected to the Late Sales portal, where you can purchase these offers.'
        result = util.create_basic_embeds_from_fields(title, description=description, repeat_description=False, colour=colour, fields=fields, footer=footer, author_url=LATE_SALES_PORTAL_HYPERLINK)
    else:
        result = [
            f'**{title}**',
            f'_{description}_'
        ]
        for sales_info in sales_infos:
            expires_in = sales_info['expires_in']
            day = 'day' + ('' if expires_in == 1 else 's')
            details = f'{expires_in} {day}: {sales_info["name"]} ({sales_info["type"]}) {settings.DEFAULT_HYPHEN} {sales_info["price"]} {sales_info["currency"]}'
            result.append(details)
        result.append(f'_Visit <{LATE_SALES_PORTAL_HYPERLINK}> to purchase these offers._')
    return result


async def get_oldest_expired_sale_entity_details(utc_now: datetime) -> List[str]:
    db_sales_infos = await db_get_sales_infos(utc_now=utc_now)
    db_sales_infos = [db_sales_infos[-1]]
    sales_infos = __process_db_sales_infos(db_sales_infos, utc_now)
    for sales_info in sales_infos:
        return sales_info['entity_details']
    return None


async def __process_db_sales_infos(db_sales_infos: List[Dict], utc_now: datetime) -> List[Dict]:
    chars_data = await crew.characters_designs_retriever.get_data_dict3()
    collections_data = await crew.collections_designs_retriever.get_data_dict3()
    items_data = await item.items_designs_retriever.get_data_dict3()
    researches_data = await research.researches_designs_retriever.get_data_dict3()
    rooms_data = await room.rooms_designs_retriever.get_data_dict3()
    rooms_designs_sprites_data = await room.rooms_designs_sprites_retriever.get_data_dict3()
    trainings_data = await training.trainings_designs_retriever.get_data_dict3()

    result = []

    for db_sales_info in db_sales_infos:
        expiry_date = db_sales_info['limitedcatalogexpirydate']
        expires_in = 29 - (utc_now - expiry_date).days
        entity_id = db_sales_info['limitedcatalogargument']
        entity_type = db_sales_info['limitedcatalogtype']
        currency_type = db_sales_info['limitedcatalogcurrencytype']
        currency = lookups.CURRENCY_EMOJI_LOOKUP[currency_type.lower()]
        currency_amount = db_sales_info['limitedcatalogcurrencyamount']
        price = int(currency_amount * 1.25)
        if entity_type == 'Character':
            entity_details = crew.get_char_details_by_id(str(entity_id), chars_data, collections_data)
            entity_name = entity_details.entity_info.get(crew.CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME)
            entity_type = 'Crew'
        elif entity_type == 'Item':
            entity_details = item.get_item_details_by_id(str(entity_id), items_data, trainings_data)
            entity_name = entity_details.entity_info.get(item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
        elif entity_type == 'Room':
            entity_details = room.get_room_details_by_id(str(entity_id), rooms_data, items_data, researches_data, rooms_designs_sprites_data)
            entity_name = entity_details.entity_info.get(room.ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME)
        else:
            entity_details = None
            entity_name = ''
        result.append({
            'name': entity_name,
            'type': entity_type,
            'price': price,
            'original_price': currency_amount,
            'currency': currency,
            'original_currency': currency_type,
            'expiry_date': expiry_date,
            'expires_in': expires_in,
            'entity_details': entity_details
        })
    return result


async def get_sales_history(ctx: commands.Context, entity_info: Dict, as_embed: bool = settings.USE_EMBEDS) -> Union[List[discord.Embed], List[str]]:
    utc_now = util.get_utcnow()

    entity_id = entity_info.get('EntityId')
    entity_id = int(entity_id) if entity_id else None
    entity_name = entity_info.get('EntityName')

    db_sales_infos = await db_get_sales_infos(utc_now=utc_now, entity_id=entity_id)
    sales_infos = await __process_db_sales_infos(db_sales_infos, utc_now)
    sales_infos = [sales_info for sales_info in sales_infos if sales_info['expiry_date'] <= utc_now]

    if sales_infos:
        title = f'{entity_name} has been sold on'
        sales_details = []
        for sales_info in sales_infos:
            sold_on_date = sales_info['expiry_date'] - util.ONE_DAY
            sold_on = util.get_formatted_datetime(sold_on_date, include_time=False, include_tz=False)
            star_date = util.get_star_date(sold_on_date)
            sold_ago = (utc_now - sold_on_date).days
            price = sales_info['original_price']
            currency = sales_info['currency']
            day = 'day' + 's' if sold_ago != 1 else ''
            sales_details.append(f'{sold_on} (Star date {star_date}, {sold_ago} {day} ago) for {price} {currency}')

        if as_embed:
            colour = util.get_bot_member_colour(ctx.bot, ctx.guild)
            result = util.create_basic_embeds_from_description(title, description=sales_details, colour=colour)
        else:
            result = [f'**{title}**']
            result.extend(sales_details)
        return result
    return [f'There is no past sales data available for {entity_name}']


def get_sales_search_details(entity_info: Dict) -> str:
    entity_type = entity_info.get('EntityType')
    if entity_type == 'Crew':
        entity_name = entity_info[crew.CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
    elif entity_type == 'Item':
        entity_name = entity_info[item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    elif entity_type == 'Room':
        entity_name = entity_info[room.ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    else:
        entity_name = None

    result = f'{entity_name} ({entity_type})'
    return result










# ---------- Utilities ----------

async def try_store_daily_channel(guild_id: int, text_channel_id: int) -> bool:
    success = False
    rows = await server_settings.db_get_autodaily_settings(guild_id=guild_id, can_post=None)
    if len(rows) == 0:
        success = await insert_daily_channel(guild_id, text_channel_id)
        if success == False:
            print(f'[try_store_daily_channel] failed to insert new data row: {guild_id} ({text_channel_id})')
    else:
        if str(rows[0][1]) != str(text_channel_id):
            success = await update_daily_channel(guild_id, text_channel_id, None)
            if success == False:
                print(f'[try_store_daily_channel] failed to update data row: {guild_id} ({text_channel_id})')
        else:
            success = True
    return success


def has_daily_changed(daily_info: Dict[str, str], retrieved_date: datetime, db_daily_info: dict, db_modify_date: datetime) -> bool:
    if retrieved_date.hour >= 23:
        return False

    if db_modify_date is None:
        return True
    elif retrieved_date.day > db_modify_date.day:
        for daily_info_field in DAILY_INFO_FIELDS_TO_CHECK:
            if daily_info[daily_info_field] != db_daily_info[daily_info_field]:
                return True
        return False
    else:
        daily_info = daily_info.copy()
        daily_info.pop('News', None)
        db_daily_info = db_daily_info.copy()
        db_daily_info.pop('News', None)
        return not util.dicts_equal(daily_info, db_daily_info)


def convert_to_daily_info(dropship_info: dict) -> dict:
    result = {}
    for field_name in DAILY_INFO_FIELDS:
        value = None
        if field_name in dropship_info.keys():
            value = dropship_info[field_name]
        result[field_name] = value
    return result


async def get_daily_channels(ctx: discord.ext.commands.Context, guild_id: int = None, can_post: bool = None) -> list:
    settings = await server_settings.db_get_autodaily_settings(guild_id, can_post)
    result = []
    at_least_one = False
    for (_, channel_id, can_post, _, _, _, _, _, _) in settings:
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


async def get_daily_info():
    latest_settings = await core.get_latest_settings()
    result = convert_to_daily_info(latest_settings)
    return result


def get_daily_info_setting_name(field_name: str) -> str:
    return f'daily{field_name}'


async def insert_daily_channel(guild_id: int, channel_id: int) -> bool:
    success = await server_settings.db_create_server_settings(guild_id)
    if success:
        success = await update_daily_channel(guild_id, channel_id=channel_id, latest_message_id=None)
    return success


def remove_duplicate_autodaily_settings(autodaily_settings: list) -> list:
    if not autodaily_settings:
        return autodaily_settings
    result = {}
    for autodaily_setting in autodaily_settings:
        if autodaily_setting.guild_id and autodaily_setting.guild_id not in result.keys():
            result[autodaily_setting.guild_id] = autodaily_setting
    return list(result.values())


async def update_daily_channel(guild_id: int, channel_id: int = None, latest_message_id: int = None) -> bool:
    success = True
    if channel_id is not None:
        success = success and await server_settings.db_update_daily_channel_id(guild_id, channel_id)
    if latest_message_id is not None:
        success = success and await server_settings.db_update_daily_latest_message(guild_id, latest_message_id)
    return success


async def db_get_daily_info(skip_cache: bool = False) -> Tuple[Dict, datetime]:
    if __daily_info_cache is None or skip_cache:
        result = {}
        modify_dates = []
        daily_settings = await db.get_settings(DB_DAILY_INFO_COLUMN_NAMES.keys())
        result = {DB_DAILY_INFO_COLUMN_NAMES.get(db_setting_name, db_setting_name): details[0] for db_setting_name, details in daily_settings.items()}
        modify_dates = [details[1] for details in daily_settings.values() if details[1] is not None]
        if result and modify_dates:
            return (result, max(modify_dates))
        else:
            return ({}, None)
    else:
        return (__daily_info_cache, __daily_info_modified_at)


async def db_get_sales_infos(utc_now: datetime = None, entity_id: int = None, skip_cache: bool = False) -> List[Dict]:
    if not skip_cache and utc_now is not None and (__sales_info_cache_retrieved_at is None or __sales_info_cache_retrieved_at.day != utc_now.day):
        await __update_db_sales_info_cache()
    if skip_cache:
        result = await db.get_sales_infos()
    else:
        result = __sales_info_cache
    if entity_id:
        result = [db_sales_info for db_sales_info in result if db_sales_info['limitedcatalogargument'] == entity_id]
    return result


async def db_set_daily_info(daily_info: dict, utc_now: datetime) -> bool:
    settings = {get_daily_info_setting_name(key): (value, utc_now) for key, value in daily_info.items()}
    settings_success = await db.set_settings(settings)
    if settings_success:
        await __update_db_daily_info_cache()

    sales_info = {key: value(daily_info[key]) for key, value in SALES_DAILY_INFO_FIELDS.items()}
    sales_success = await db.update_sales_info(sales_info)
    if sales_success:
        await __update_db_sales_info_cache()

    return settings_success and sales_success










# ---------- Mocks ----------

def mock_get_daily_info():
    utc_now = util.get_utcnow()
    if utc_now.hour < 1:
        if utc_now.minute < 20:
            return __mock_get_daily_info_1()
        else:
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
        'SaleQuantity': '1',
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
        'SaleQuantity': f'{random.randint(1, 31)}',
        'SaleType': random.choice(['Item', 'Character'])
    }
    return result










# ---------- Initialization ----------

__daily_info_cache: dict = None
__daily_info_modified_at: datetime = None
__sales_info_cache: dict = None
__sales_info_cache_retrieved_at: datetime = None


async def __update_db_daily_info_cache():
    global __daily_info_cache
    global __daily_info_modified_at
    __daily_info_cache, __daily_info_modified_at = await db_get_daily_info(skip_cache=True)


async def __update_db_sales_info_cache():
    global __sales_info_cache
    global __sales_info_cache_retrieved_at
    __sales_info_cache = await db_get_sales_infos(skip_cache=True)
    __sales_info_cache_retrieved_at = util.get_utcnow()


async def init():
    await __update_db_daily_info_cache()
    await __update_db_sales_info_cache()