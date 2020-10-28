#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import calendar
from datetime import datetime
import discord
import discord.ext.commands as commands
import pprint
from typing import Dict, Iterable, List, Tuple, Union

from cache import PssCache
import emojis
import pss_core as core
import pss_crew as crew
import pss_entity as entity
import pss_item as item
import pss_lookups as lookups
import pss_room as room
import pss_training as training
import pss_sprites as sprites
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

async def get_dropship_text(bot: commands.Bot = None, guild: discord.Guild = None, daily_info: dict = None, utc_now: datetime = None, language_key: str = 'en') -> Tuple[List[str], List[discord.Embed], bool]:
    utc_now = utc_now or util.get_utcnow()
    if not daily_info:
        daily_info = await core.get_latest_settings(language_key=language_key)

    collections_designs_data = await crew.collections_designs_retriever.get_data_dict3()
    chars_designs_data = await crew.characters_designs_retriever.get_data_dict3()
    items_designs_data = await item.items_designs_retriever.get_data_dict3()
    rooms_designs_data = await room.rooms_designs_retriever.get_data_dict3()
    trainings_designs_data = await training.trainings_designs_retriever.get_data_dict3()

    try:
        daily_msg = _get_daily_news_from_data_as_text(daily_info)
        dropship_msg = await _get_dropship_msg_from_data_as_text(daily_info, chars_designs_data, collections_designs_data)
        merchantship_msg = await _get_merchantship_msg_from_data_as_text(daily_info, items_designs_data, trainings_designs_data)
        shop_msg = await _get_shop_msg_from_data_as_text(daily_info, chars_designs_data, collections_designs_data, items_designs_data, rooms_designs_data, trainings_designs_data)
        sale_msg = await _get_sale_msg_from_data_as_text(daily_info, chars_designs_data, collections_designs_data, items_designs_data, rooms_designs_data, trainings_designs_data)
        daily_reward_msg = await _get_daily_reward_from_data_as_text(daily_info, items_designs_data, trainings_designs_data)
    except Exception as e:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(daily_info)
        print(e)
        return [], False

    parts = [dropship_msg, merchantship_msg, shop_msg, sale_msg, daily_reward_msg]

    lines = list(daily_msg)
    for part in parts:
        lines.append(settings.EMPTY_LINE)
        lines.extend(part)

    title = f'Star date {util.get_star_date(utc_now)}'
    description = ''.join(daily_msg)
    fields = [(part[0], '\n'.join(part[1:]), False) for part in parts]
    sprite_url = await sprites.get_download_sprite_link(daily_info['NewsSpriteId'])
    colour = util.get_bot_member_colour(bot, guild)
    embed = util.create_embed(title, description=description, fields=fields, image_url=sprite_url, colour=colour)

    return lines, [embed], True


def compare_dropship_messages(message: discord.Message, dropship_text: str, dropship_embed: discord.Embed) -> bool:
    """
    Returns True, if messages are equal.
    """
    dropship_embed_fields = []
    message_embed_fields = []

    if dropship_embed:
        dropship_embed_fields = dropship_embed.to_dict()['fields']
    for message_embed in message.embeds:
        message_embed_fields = message_embed.to_dict()['fields']
        break
    if len(dropship_embed_fields) == len(message_embed_fields):
        for i, dropship_embed_field in enumerate(dropship_embed_fields):
            if not util.dicts_equal(dropship_embed_field, message_embed_fields[i]):
                return False
        return True

    return message.content == dropship_text



def _get_daily_news_from_data_as_text(raw_data: dict) -> List[str]:
    result = ['No news have been provided :(']
    if raw_data and 'News' in raw_data.keys():
        result = [raw_data['News']]
    return result


async def _get_dropship_msg_from_data_as_text(raw_data: dict, chars_data: dict, collections_data: dict) -> List[str]:
    result = [f'{emojis.pss_dropship} **Dropship crew**']
    if raw_data:
        common_crew_id = raw_data['CommonCrewId']
        common_crew_details = crew.get_char_details_by_id(common_crew_id, chars_data, collections_data)
        common_crew_info = await common_crew_details.get_details_as_text(entity.EntityDetailsType.SHORT)

        hero_crew_id = raw_data['HeroCrewId']
        hero_crew_details = crew.get_char_details_by_id(hero_crew_id, chars_data, collections_data)
        hero_crew_info = await hero_crew_details.get_details_as_text(entity.EntityDetailsType.SHORT)

        common_crew_rarity = common_crew_details.entity_info['Rarity']
        if common_crew_rarity in ['Unique', 'Epic', 'Hero', 'Special', 'Legendary']:
            common_crew_info.append(' - any unique & above crew that costs minerals is probably worth buying (just blend it if you don\'t need it)!')

        if common_crew_info:
            result.append(f'{emojis.pss_min_big}  {"".join(common_crew_info)}')
        if hero_crew_info:
            result.append(f'{emojis.pss_bux}  {hero_crew_info[0]}')
    else:
        result.append('-')
    return result


async def _get_merchantship_msg_from_data_as_text(raw_data: dict, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData) -> List[str]:
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
                item_details = item.get_item_details_by_id(item_id, items_data, trainings_data)
                item_details = ''.join(await item_details.get_details_as_text(entity.EntityDetailsType.SHORT))
                currency_type, price = cargo_prices[i].split(':')
                currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[currency_type.lower()]
                result.append(f'{amount} x {item_details}: {price} {currency_emoji}')
    else:
        result.append('-')
    return result


async def _get_shop_msg_from_data_as_text(raw_data: dict, chars_data: entity.EntitiesData, collections_data: entity.EntitiesData, items_data: entity.EntitiesData, rooms_data: entity.EntitiesData, trainings_data: entity.EntitiesData) -> List[str]:
    result = [f'{emojis.pss_shop} **Shop**']

    shop_type = raw_data['LimitedCatalogType']
    currency_type = raw_data['LimitedCatalogCurrencyType']
    currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[currency_type.lower()]
    price = raw_data['LimitedCatalogCurrencyAmount']
    can_own_max = raw_data['LimitedCatalogMaxTotal']

    entity_id = raw_data['LimitedCatalogArgument']
    entity_details = []
    if shop_type == 'Character':
        char_details = crew.get_char_details_by_id(entity_id, chars_data, collections_data)
        entity_details = await char_details.get_details_as_text(entity.EntityDetailsType.SHORT)
    elif shop_type == 'Item':
        item_details = item.get_item_details_by_id(entity_id, items_data, trainings_data)
        entity_details = await item_details.get_details_as_text(entity.EntityDetailsType.SHORT)
    elif shop_type == 'Room':
        room_details = room.get_room_details_by_id(entity_id, rooms_data, None, None, None)
        entity_details = await room_details.get_details_as_text(entity.EntityDetailsType.SHORT)
    else:
        result.append('-')
        return result

    if entity_details:
        result.extend(entity_details)

    result.append(f'Cost: {price} {currency_emoji}')
    result.append(f'Can own (max): {can_own_max}')

    return result


async def _get_sale_msg_from_data_as_text(raw_data: dict, chars_data: entity.EntitiesData, collections_data: entity.EntitiesData, items_data: entity.EntitiesData, rooms_data: entity.EntitiesData, trainings_data: entity.EntitiesData) -> List[str]:
    # 'SaleItemMask': use lookups.SALE_ITEM_MASK_LOOKUP to print which item to buy
    result = [f'{emojis.pss_sale} **Sale**']

    sale_items = core.convert_iap_options_mask(int(raw_data['SaleItemMask']))
    sale_quantity = raw_data['SaleQuantity']
    result.append(f'Buy a {sale_items} _of Starbux_ and get:')

    sale_type = raw_data['SaleType']
    sale_argument = raw_data['SaleArgument']
    if sale_type == 'Character':
        char_details = crew.get_char_details_by_id(sale_argument, chars_data, collections_data)
        entity_details = ''.join(await char_details.get_details_as_text(entity.EntityDetailsType.SHORT))
    elif sale_type == 'Item':
        item_details = item.get_item_details_by_id(sale_argument, items_data, trainings_data)
        entity_details = ''.join(await item_details.get_details_as_text(entity.EntityDetailsType.SHORT))
    elif sale_type == 'Room':
        room_details = room.get_room_details_by_id(sale_argument, rooms_data, None, None, None)
        entity_details = ''.join(await room_details.get_details_as_text(entity.EntityDetailsType.SHORT))
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


async def _get_daily_reward_from_data_as_text(raw_data: dict, item_data: entity.EntitiesData, trainings_data: entity.EntitiesData) -> List[str]:
    result = ['**Daily rewards**']

    reward_currency = raw_data['DailyRewardType'].lower()
    reward_currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[reward_currency]
    reward_amount = int(raw_data['DailyRewardArgument'])
    reward_amount, reward_multiplier = util.get_reduced_number(reward_amount)
    result.append(f'{reward_amount:.0f}{reward_multiplier} {reward_currency_emoji}')

    item_rewards = raw_data['DailyItemRewards'].split('|')
    for item_reward in item_rewards:
        item_id, amount = item_reward.split('x')
        item_details: entity.EntityDetails = item.get_item_details_by_id(item_id, item_data, trainings_data)
        item_details_text = ''.join(await item_details.get_details_as_text(entity.EntityDetailsType.SHORT))
        result.append(f'{amount} x {item_details_text}')

    return result










# ---------- News info ----------

async def get_news(ctx: commands.Context, as_embed: bool = settings.USE_EMBEDS, language_key: str = 'en'):
    path = f'SettingService/ListAllNewsDesigns?languageKey={language_key}'

    try:
        raw_text = await core.get_data_from_path(path)
        raw_data = core.xmltree_to_dict3(raw_text)
    except Exception as err:
        raw_data = None
        return [f'Could not get news: {err}'], False

    if raw_data:
        news_infos = sorted(list(raw_data.values()), key=lambda news_info: news_info['UpdateDate'])
        news_count = len(news_infos)
        if news_count > 5:
            news_infos = news_infos[news_count-5:]
        news_details_collection = __create_news_details_collection_from_infos(news_infos)

        if as_embed:
            return (await news_details_collection.get_entity_details_as_embed(ctx)), True
        else:
            return (await news_details_collection.get_entity_details_as_text()), True


async def _get_news_as_embed(ctx: commands.Context, news_infos: dict) -> List[discord.Embed]:
    result = []
    for news_info in news_infos:
        news_details = await _get_news_details_as_embed(ctx, news_info)
        if news_details:
            result.append(news_details)

    return result

def _get_news_as_text(news_infos: dict) -> list:
    result = []
    for news_info in news_infos.values():
        news_details = _get_news_details_as_text(news_info)
        if news_details:
            result.extend(news_details)
            result.append(settings.EMPTY_LINE)

    return result


async def _get_news_details_as_embed(ctx: commands.Context, news_info: dict) -> discord.Embed:
    title = news_info['Title']
    description = util.escape_escape_sequences(news_info['Description'])
    while '\n\n' in description:
        description = description.replace('\n\n', '\n')
    sprite_url = await sprites.get_download_sprite_link(news_info['SpriteId'])
    timestamp = util.parse_pss_datetime(news_info['UpdateDate'])
    colour = util.get_bot_member_colour(ctx.bot, ctx.guild)
    link = news_info['Link'].strip()
    if link:
        fields = [('Link', link, False)]
    else:
        fields = []
    result = util.create_embed(title, description=description, image_url=sprite_url, colour=colour, footer='PSS News', timestamp=timestamp, fields=fields)
    return result


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










# ---------- Create EntityDetails ----------

def __create_news_design_data_from_info(news_info: entity.EntityInfo) -> entity.EntityDetails:
    return entity.EntityDetails(news_info, __properties['title_news'], __properties['description_news'], __properties['properties_news'], __properties['embed_settings'])


def __create_news_details_list_from_infos(news_infos: List[entity.EntityInfo]) -> List[entity.EntityDetails]:
    return [__create_news_design_data_from_info(news_info) for news_info in news_infos]


def __create_news_details_collection_from_infos(news_infos: List[entity.EntityInfo]) -> entity.EntityDetailsCollection:
    base_details = __create_news_details_list_from_infos(news_infos)
    result = entity.EntityDetailsCollection(base_details, big_set_threshold=0)
    return result










# ---------- Transformation functions ----------

def __get_news_footer(news_info: entity.EntityInfo, **kwargs) -> str:
    return 'PSS News'


def __get_pss_datetime(*args, **kwargs) -> datetime:
    entity_property = kwargs.get('entity_property')
    result = util.parse_pss_datetime(entity_property)
    return result


def __get_value(*args, **kwargs) -> str:
    entity_property = kwargs.get('entity_property')
    if entity.has_value(entity_property):
        return entity_property
    else:
        return None


def __sanitize_text(*args, **kwargs) -> str:
    entity_property = kwargs.get('entity_property')
    if entity_property:
        result = util.escape_escape_sequences(entity_property)
        while '\n\n' in result:
            result = result.replace('\n\n', '\n')
        return result
    else:
        return None










# ---------- Helper functions ----------










# ---------- Initilization ----------

__properties: Dict[str, Union[entity.EntityDetailProperty, entity.EntityDetailPropertyCollection, entity.EntityDetailPropertyListCollection]] = {
    'title_news': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name='Title')
    ),
    'description_news': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, entity_property_name='Description', transform_function=__sanitize_text)
    ),
    'properties_news': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Link', True, entity_property_name='Link', transform_function=__get_value)
        ]
    ),
    'embed_settings': {
        'image_url': entity.EntityDetailProperty('image_url', False, entity_property_name='SpriteId', transform_function=sprites.get_download_sprite_link_by_property),
        'footer': entity.EntityDetailProperty('footer', False, transform_function=__get_news_footer),
        'timestamp': entity.EntityDetailProperty('timestamp', False, entity_property_name='UpdateDate', transform_function=__get_pss_datetime)
    }
}









# ---------- Testing ----------

#if __name__ == '__main__':
#    result, success = await get_dropship_text(as_embed=False, language_key='en')
#    print('\n'.join(result))