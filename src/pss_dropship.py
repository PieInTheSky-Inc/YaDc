#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime
import discord
import pprint
from typing import Dict, Iterable, List, Tuple, Union

from cache import PssCache
import emojis
import pss_core as core
import pss_crew as crew
import pss_item as item
import pss_lookups as lookups
import pss_room as room
import settings
import utility as util


# ---------- Constants ----------

DROPSHIP_BASE_PATH = f'SettingService/GetLatestVersion3?deviceType=DeviceTypeAndroid&languageKey='










# ---------- Initilization ----------










# ---------- Helper functions ----------

def _convert_sale_item_mask(sale_item_mask: int) -> str:
    result = []
    for flag in lookups.IAP_OPTIONS_MASK_LOOKUP.keys():
        if (sale_item_mask & flag) != 0:
            item, value = lookups.IAP_OPTIONS_MASK_LOOKUP[flag]
            result.append(f'_{item}_ ({value})')
    if result:
        if len(result) > 1:
            return f'{", ".join(result[:-1])} or {result[-1]}'
        else:
            return result[0]
    else:
        return ''










# ---------- Dropship info ----------

async def get_dropship_text(daily_info: dict = None, as_embed: bool = settings.USE_EMBEDS, language_key: str = 'en') -> (List[str], bool):
    if not daily_info:
        daily_info = await core.get_latest_settings(language_key=language_key)

    collection_design_data = await crew.collections_designs_retriever.get_data_dict3()
    char_design_data = await crew.characters_designs_retriever.get_data_dict3()
    item_design_data = await item.items_designs_retriever.get_data_dict3()
    room_design_data = await room.rooms_designs_retriever.get_data_dict3()

    try:
        daily_msg = _get_daily_news_from_data_as_text(daily_info)
        dropship_msg = await _get_dropship_msg_from_data_as_text(daily_info, char_design_data, collection_design_data)
        merchantship_msg = await _get_merchantship_msg_from_data_as_text(daily_info, item_design_data)
        shop_msg = await _get_shop_msg_from_data_as_text(daily_info, char_design_data, collection_design_data, item_design_data, room_design_data)
        sale_msg = await _get_sale_msg_from_data_as_text(daily_info, char_design_data, collection_design_data, item_design_data, room_design_data)
        daily_reward_msg = await _get_daily_reward_from_data_as_text(daily_info, item_design_data)
    except Exception as e:
        print(e)
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(daily_info)
        return [], False

    lines = daily_msg
    lines.append(settings.EMPTY_LINE)
    lines.extend(dropship_msg)
    lines.append(settings.EMPTY_LINE)
    lines.extend(merchantship_msg)
    lines.append(settings.EMPTY_LINE)
    lines.extend(shop_msg)
    lines.append(settings.EMPTY_LINE)
    lines.extend(sale_msg)
    lines.append(settings.EMPTY_LINE)
    lines.extend(daily_reward_msg)

    return lines, True


def _get_daily_news_from_data_as_text(raw_data: dict) -> list:
    result = ['No news have been provided :(']
    if raw_data and 'News' in raw_data.keys():
        result = [raw_data['News']]
    return result


async def _get_dropship_msg_from_data_as_text(raw_data: dict, chars_designs_data: dict, collections_designs_data: dict) -> list:
    result = [f'{emojis.pss_dropship} **Dropship crew**']
    if raw_data:
        common_crew_id = raw_data['CommonCrewId']
        common_crew_details = crew.get_char_design_details_by_id(common_crew_id, chars_designs_data, collections_designs_data, level=40)
        common_crew_info = await common_crew_details.get_details_as_text_short()

        hero_crew_id = raw_data['HeroCrewId']
        hero_crew_details = crew.get_char_design_details_by_id(hero_crew_id, chars_designs_data, collections_designs_data, level=40)
        hero_crew_info = await hero_crew_details.get_details_as_text_short()

        common_crew_rarity = common_crew_details.entity_design_info['Rarity']
        if common_crew_rarity in ['Unique', 'Epic', 'Hero', 'Special', 'Legendary']:
            common_crew_info.append(' - any unique & above crew that costs minerals is probably worth buying (just blend it if you don\'t need it)!')

        if common_crew_info:
            result.append(f'{emojis.pss_min_big}  {"".join(common_crew_info)}')
        if hero_crew_info:
            result.append(f'{emojis.pss_bux}  {hero_crew_info[0]}')
    else:
        result.append('-')
    return result


async def _get_merchantship_msg_from_data_as_text(raw_data: dict, item_designs_data: dict) -> list:
    result = [f'{emojis.pss_merchantship} **Merchant ship**']
    if raw_data:
        cargo_items = raw_data['CargoItems'].split('|')
        cargo_prices = raw_data['CargoPrices'].split('|')
        for i, cargo_info in enumerate(cargo_items):
            if 'x' in cargo_info:
                item_id, amount = cargo_info.split('x')
            else:
                item_id = cargo_info
                amount = '1'
            if ':' in item_id:
                _, item_id = item_id.split(':')
            if item_id:
                item_design_details = item.get_item_design_details_by_id(item_id, item_designs_data)
                item_details = ''.join(await item_design_details.get_details_as_text_long())
                currency_type, price = cargo_prices[i].split(':')
                currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[currency_type.lower()]
                result.append(f'{amount} x {item_details}: {price} {currency_emoji}')
    else:
        result.append('-')
    return result


async def _get_shop_msg_from_data_as_text(raw_data: dict, chars_designs_data: dict, collections_designs_data: dict, items_designs_data: dict, rooms_designs_data: dict) -> List[str]:
    result = [f'{emojis.pss_shop} **Shop**']

    shop_type = raw_data['LimitedCatalogType']
    currency_type = raw_data['LimitedCatalogCurrencyType']
    currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[currency_type.lower()]
    price = raw_data['LimitedCatalogCurrencyAmount']
    can_own_max = raw_data['LimitedCatalogMaxTotal']

    entity_id = raw_data['LimitedCatalogArgument']
    entity_details = []
    if shop_type == 'Character':
        char_design_details = crew.get_char_design_details_by_id(entity_id, chars_designs_data, collections_designs_data, level=40)
        entity_details = await char_design_details.get_details_as_text_short()
    elif shop_type == 'Item':
        item_design_details = item.get_item_design_details_by_id(entity_id, items_designs_data)
        entity_details = await item_design_details.get_details_as_text_long()
    elif shop_type == 'Room':
        entity_details = room.get_room_details_short_from_id_as_text(entity_id, rooms_designs_data)
    else:
        result.append('-')
        return result

    if entity_details:
        result.extend(entity_details)

    result.append(f'Cost: {price} {currency_emoji}')
    result.append(f'Can own (max): {can_own_max}')

    return result


async def _get_sale_msg_from_data_as_text(raw_data: dict, chars_designs_data: dict, collections_designs_data: dict, items_designs_data: dict, rooms_designs_data: dict) -> list:
    # 'SaleItemMask': use lookups.SALE_ITEM_MASK_LOOKUP to print which item to buy
    result = [f'{emojis.pss_sale} **Sale**']

    sale_items = core.convert_iap_options_mask(int(raw_data['SaleItemMask']))
    sale_quantity = raw_data['SaleQuantity']
    result.append(f'Buy a {sale_items} _of Starbux_ and get:')

    sale_type = raw_data['SaleType']
    sale_argument = raw_data['SaleArgument']
    if sale_type == 'Character':
        char_design_details = crew.get_char_design_details_by_id(sale_argument, chars_designs_data, collections_designs_data, level=40)
        entity_details = ''.join(await char_design_details.get_details_as_text_short())
    elif sale_type == 'Item':
        item_design_details = item.get_item_design_details_by_id(sale_argument, items_designs_data)
        entity_details = ''.join(await item_design_details.get_details_as_text_long())
    elif sale_type == 'Room':
        entity_details = ''.join(room.get_room_details_short_from_id_as_text(sale_argument, rooms_designs_data))
    elif sale_type == 'Bonus':
        entity_details = f'{sale_argument} % bonus starbux'
    else: # Print debugging info
        sale_title = raw_data['SaleTitle']
        debug_details = []
        debug_details.append(f'Sale Type: {sale_type}')
        debug_details.append(f'Sale Argument: {sale_argument}')
        debug_details.append(f'Sale Title: {sale_title}')
        entity_details = '\n'.join(debug_details)

    result.append(f'{sale_quantity} x {entity_details}')

    return result


async def _get_daily_reward_from_data_as_text(raw_data: dict, item_designs_data: dict) -> list:
    result = ['**Daily rewards**']

    reward_currency = raw_data['DailyRewardType'].lower()
    reward_currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[reward_currency]
    reward_amount = int(raw_data['DailyRewardArgument'])
    reward_amount, reward_multiplier = util.get_reduced_number(reward_amount)
    result.append(f'{reward_amount:.0f}{reward_multiplier} {reward_currency_emoji}')

    item_rewards = raw_data['DailyItemRewards'].split('|')
    for item_reward in item_rewards:
        item_id, amount = item_reward.split('x')
        item_design_details = item.get_item_design_details_by_id(item_id, item_designs_data)
        item_details = ''.join(await item_design_details.get_details_as_text_long())
        result.append(f'{amount} x {item_details}')

    return result










# ---------- News info ----------

async def get_news(as_embed: bool = settings.USE_EMBEDS, language_key: str = 'en'):
    path = f'SettingService/ListAllNewsDesigns?languageKey={language_key}'

    try:
        raw_text = await core.get_data_from_path(path)
        raw_data = core.xmltree_to_dict3(raw_text)
    except Exception as err:
        raw_data = None

    if not raw_data:
        return [f'Could not get news: {err}'], False
    else:
        if as_embed:
            return _get_news_as_embed(raw_data), True
        else:
            return _get_news_as_text(raw_data), True


def _get_news_as_embed(news_infos: dict) -> list:
    result = []
    for news_info in news_infos.values():
        news_details = _get_news_details_as_embed(news_info)
        if news_details:
            result.append(news_details)

    return []


def _get_news_as_text(news_infos: dict) -> list:
    result = []
    for news_info in news_infos.values():
        news_details = _get_news_details_as_text(news_info)
        if news_details:
            result.extend(news_details)
            result.append(settings.EMPTY_LINE)

    return result


def _get_news_details_as_embed(news_info: dict) -> discord.Embed:
    return ''


def _get_news_details_as_text(news_info: dict) -> list:
    news_title = news_info['Title']
    title = f'__{news_title}__'
    description = util.escape_escape_sequences(news_info['Description'])
    while '\n\n' in description:
        description = description.replace('\n\n', '\n')

    news_modify_date = util.parse_pss_datetime(news_info['UpdateDate'])
    if news_modify_date:
        modify_date = util.get_formatted_date(news_modify_date)
        title = f'{title} ({modify_date})'

    link = news_info['Link'].strip()

    result = [f'**{title}**', description]
    if link:
        result.append(f'<{link}>')

    return result









# ---------- Testing ----------

#if __name__ == '__main__':
#    result, success = await get_dropship_text(as_embed=False, language_key='en')
#    print('\n'.join(result))