from datetime import datetime
from discord import Embed, Guild, Message
from discord.ext.commands import Bot, Context
import pprint
from typing import List, Tuple, Union

import emojis
import pss_core as core
import pss_crew as crew
import pss_daily as daily
from pss_entity import EntitiesData, EntityDetailProperty, EntityDetailPropertyCollection, EntityDetailPropertyListCollection, EntityDetails, EntityDetailsCollection, EntityDetailsCreationPropertiesCollection, EntityDetailsType, EntityInfo, entity_property_has_value
from pss_exception import Error
import pss_item as item
import pss_lookups as lookups
import pss_room as room
import pss_training as training
import pss_sprites as sprites
import settings
import utils


# ---------- Constants ----------

DROPSHIP_BASE_PATH = f'SettingService/GetLatestVersion3?deviceType=DeviceTypeAndroid&languageKey='





# ---------- Dropship info ----------

async def get_dropship_text(bot: Bot = None, guild: Guild = None, daily_info: dict = None, utc_now: datetime = None, language_key: str = 'en') -> Tuple[List[str], List[Embed], bool]:
    utc_now = utc_now or utils.get_utc_now()
    if not daily_info:
        daily_info = await core.get_latest_settings(language_key=language_key)

    collections_designs_data = await crew.collections_designs_retriever.get_data_dict3()
    chars_designs_data = await crew.characters_designs_retriever.get_data_dict3()
    items_designs_data = await item.items_designs_retriever.get_data_dict3()
    rooms_designs_data = await room.rooms_designs_retriever.get_data_dict3()
    trainings_designs_data = await training.trainings_designs_retriever.get_data_dict3()

    try:
        daily_msg = _get_daily_news_from_info_as_text(daily_info)
        dropship_msg = await _get_dropship_msg_from_info_as_text(daily_info, chars_designs_data, collections_designs_data)
        merchantship_msg = await _get_merchantship_msg_from_info_as_text(daily_info, items_designs_data, trainings_designs_data)
        shop_msg = await _get_shop_msg_from_info_as_text(daily_info, chars_designs_data, collections_designs_data, items_designs_data, rooms_designs_data, trainings_designs_data)
        sale_msg = await _get_sale_msg_from_info_as_text(daily_info, chars_designs_data, collections_designs_data, items_designs_data, rooms_designs_data, trainings_designs_data)
        daily_reward_msg = await _get_daily_reward_from_info_as_text(daily_info, items_designs_data, trainings_designs_data)
    except Exception as e:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(daily_info)
        print(e)
        return [], False

    expiring_sale_details_text = await daily.get_oldest_expired_sale_entity_details(utc_now, for_embed=False)
    expiring_sale_details_embed = await daily.get_oldest_expired_sale_entity_details(utc_now, for_embed=True)

    parts = [dropship_msg, merchantship_msg, shop_msg, sale_msg, daily_reward_msg]

    lines = list(daily_msg)
    for part in parts:
        lines.append(utils.discord.ZERO_WIDTH_SPACE)
        lines.extend(part)
    lines.append(utils.discord.ZERO_WIDTH_SPACE)
    lines.append('**Sale expiring today**')
    lines.extend(expiring_sale_details_text)
    lines.append(f'_Visit <{daily.LATE_SALES_PORTAL_HYPERLINK}> to purchase this offer._')

    title = 'Pixel Starships Dropships'
    footer = f'Star date {utils.datetime.get_star_date(utc_now)}'
    description = ''.join(daily_msg)
    fields = [(part[0], '\n'.join(part[1:]), False) for part in parts]
    expiring_sale_details_embed.append(f'_Visit the [Late Sales Portal]({daily.LATE_SALES_PORTAL_HYPERLINK}) to purchase this offer._')
    fields.append(('Sale expiring today', '\n'.join(expiring_sale_details_embed), False))
    sprite_url = await sprites.get_download_sprite_link(daily_info['NewsSpriteId'])
    colour = utils.discord.get_bot_member_colour(bot, guild)
    embed = utils.discord.create_embed(title, description=description, fields=fields, image_url=sprite_url, colour=colour, footer=footer)

    return lines, [embed], True


def compare_dropship_messages(message: Message, dropship_text: str, dropship_embed: Embed) -> bool:
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
            if not utils.dicts_equal(dropship_embed_field, message_embed_fields[i]):
                return False
        return True

    return message.content == dropship_text


def _get_daily_news_from_info_as_text(daily_info: EntityInfo) -> List[str]:
    result = ['No news have been provided :(']
    if daily_info and 'News' in daily_info.keys():
        result = [daily_info['News']]
    return result


async def _get_dropship_msg_from_info_as_text(daily_info: EntityInfo, chars_data: EntitiesData, collections_data: EntitiesData) -> List[str]:
    result = [f'{emojis.pss_dropship} **Dropship crew**']
    if daily_info:
        common_crew_id = daily_info['CommonCrewId']
        common_crew_details = crew.get_char_details_by_id(common_crew_id, chars_data, collections_data)
        common_crew_info = await common_crew_details.get_details_as_text(EntityDetailsType.SHORT)

        hero_crew_id = daily_info['HeroCrewId']
        hero_crew_details = crew.get_char_details_by_id(hero_crew_id, chars_data, collections_data)
        hero_crew_info = await hero_crew_details.get_details_as_text(EntityDetailsType.SHORT)

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


async def _get_merchantship_msg_from_info_as_text(daily_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData) -> List[str]:
    result = [f'{emojis.pss_merchantship} **Merchant ship**']
    if daily_info:
        cargo_items = daily_info['CargoItems'].split('|')
        cargo_prices = daily_info['CargoPrices'].split('|')
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
                item_details = ''.join(await item_details.get_details_as_text(EntityDetailsType.SHORT))
                currency_type, price = cargo_prices[i].split(':')
                currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[currency_type.lower()]
                result.append(f'{amount} x {item_details}: {price} {currency_emoji}')
    else:
        result.append('-')
    return result


async def _get_shop_msg_from_info_as_text(daily_info: EntityInfo, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, rooms_data: EntitiesData, trainings_data: EntitiesData) -> List[str]:
    result = [f'{emojis.pss_shop} **Shop**']

    shop_type = daily_info['LimitedCatalogType']
    currency_type = daily_info['LimitedCatalogCurrencyType']
    currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[currency_type.lower()]
    price = daily_info['LimitedCatalogCurrencyAmount']
    can_own_max = daily_info['LimitedCatalogMaxTotal']

    entity_id = daily_info['LimitedCatalogArgument']
    entity_details = []
    if shop_type == 'Character':
        char_details = crew.get_char_details_by_id(entity_id, chars_data, collections_data)
        entity_details = await char_details.get_details_as_text(EntityDetailsType.SHORT)
    elif shop_type == 'Item':
        item_details = item.get_item_details_by_id(entity_id, items_data, trainings_data)
        entity_details = await item_details.get_details_as_text(EntityDetailsType.SHORT)
    elif shop_type == 'Room':
        room_details = room.get_room_details_by_id(entity_id, rooms_data, None, None, None)
        entity_details = await room_details.get_details_as_text(EntityDetailsType.SHORT)
    else:
        result.append('-')
        return result

    if entity_details:
        result.extend(entity_details)

    result.append(f'Cost: {price} {currency_emoji}')
    result.append(f'Can own (max): {can_own_max}')

    return result


async def _get_sale_msg_from_info_as_text(daily_info: EntityInfo, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, rooms_data: EntitiesData, trainings_data: EntitiesData) -> List[str]:
    # 'SaleItemMask': use lookups.SALE_ITEM_MASK_LOOKUP to print which item to buy
    result = [f'{emojis.pss_sale} **Sale**']

    sale_items = core.convert_iap_options_mask(int(daily_info['SaleItemMask']))
    sale_quantity = daily_info['SaleQuantity']
    result.append(f'Buy a {sale_items} _of Starbux_ and get:')

    sale_type = daily_info['SaleType']
    sale_argument = daily_info['SaleArgument']
    if sale_type == 'Character':
        char_details = crew.get_char_details_by_id(sale_argument, chars_data, collections_data)
        entity_details = ''.join(await char_details.get_details_as_text(EntityDetailsType.SHORT))
    elif sale_type == 'Item':
        item_details = item.get_item_details_by_id(sale_argument, items_data, trainings_data)
        entity_details = ''.join(await item_details.get_details_as_text(EntityDetailsType.SHORT))
    elif sale_type == 'Room':
        room_details = room.get_room_details_by_id(sale_argument, rooms_data, None, None, None)
        entity_details = ''.join(await room_details.get_details_as_text(EntityDetailsType.SHORT))
    elif sale_type == 'Bonus':
        entity_details = f'{sale_argument} % bonus starbux'
    else: # Print debugging info
        sale_title = daily_info['SaleTitle']
        debug_details = []
        debug_details.append(f'Sale Type: {sale_type}')
        debug_details.append(f'Sale Argument: {sale_argument}')
        debug_details.append(f'Sale Title: {sale_title}')
        entity_details = '\n'.join(debug_details)

    result.append(f'{sale_quantity} x {entity_details}')

    return result


async def _get_daily_reward_from_info_as_text(daily_info: EntityInfo, item_data: EntitiesData, trainings_data: EntitiesData) -> List[str]:
    result = ['**Daily rewards**']

    reward_currency = daily_info['DailyRewardType'].lower()
    reward_currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[reward_currency]
    reward_amount = int(daily_info['DailyRewardArgument'])
    reward_amount, reward_multiplier = utils.format.get_reduced_number(reward_amount)
    result.append(f'{reward_amount:.0f}{reward_multiplier} {reward_currency_emoji}')

    item_rewards = daily_info['DailyItemRewards'].split('|')
    for item_reward in item_rewards:
        item_id, amount = item_reward.split('x')
        item_details: EntityDetails = item.get_item_details_by_id(item_id, item_data, trainings_data)
        item_details_text = ''.join(await item_details.get_details_as_text(EntityDetailsType.SHORT))
        result.append(f'{amount} x {item_details_text}')

    return result





# ---------- News info ----------

async def get_news(ctx: Context, as_embed: bool = settings.USE_EMBEDS, language_key: str = 'en') -> Union[List[Embed], List[str]]:
    path = f'SettingService/ListAllNewsDesigns?languageKey={language_key}'

    try:
        raw_text = await core.get_data_from_path(path)
        raw_data = core.xmltree_to_dict3(raw_text)
    except Exception as err:
        raw_data = None
        raise Error(f'Could not get news: {err}')

    if raw_data:
        news_infos = sorted(list(raw_data.values()), key=lambda news_info: news_info['UpdateDate'])
        news_count = len(news_infos)
        if news_count > 5:
            news_infos = news_infos[news_count-5:]
        news_details_collection = __create_news_details_collection_from_infos(news_infos)

        if as_embed:
            return (await news_details_collection.get_entities_details_as_embed(ctx))
        else:
            return (await news_details_collection.get_entities_details_as_text())





# ---------- Create EntityDetails ----------

def __create_news_design_data_from_info(news_info: EntityInfo) -> EntityDetails:
    return EntityDetails(news_info, __properties['title_news'], __properties['description_news'], __properties['properties_news'], __properties['embed_settings'])


def __create_news_details_list_from_infos(news_infos: List[EntityInfo]) -> List[EntityDetails]:
    return [__create_news_design_data_from_info(news_info) for news_info in news_infos]


def __create_news_details_collection_from_infos(news_infos: List[EntityInfo]) -> EntityDetailsCollection:
    base_details = __create_news_details_list_from_infos(news_infos)
    result = EntityDetailsCollection(base_details, big_set_threshold=0)
    return result





# ---------- Transformation functions ----------

def __get_news_footer(news_info: EntityInfo, **kwargs) -> str:
    return 'PSS News'


def __get_pss_datetime(*args, **kwargs) -> datetime:
    entity_property = kwargs.get('entity_property')
    result = utils.parse.pss_datetime(entity_property)
    return result


def __get_value(*args, **kwargs) -> str:
    entity_property = kwargs.get('entity_property')
    if entity_property_has_value(entity_property):
        return entity_property
    else:
        return None


def __sanitize_text(*args, **kwargs) -> str:
    entity_property = kwargs.get('entity_property')
    if entity_property:
        result = utils.escape_escape_sequences(entity_property)
        while '\n\n' in result:
            result = result.replace('\n\n', '\n')
        return result
    else:
        return None





# ---------- Initilization ----------

__properties: EntityDetailsCreationPropertiesCollection = {
    'title_news': EntityDetailPropertyCollection(
        EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name='Title')
    ),
    'description_news': EntityDetailPropertyCollection(
        EntityDetailProperty('Description', False, entity_property_name='Description', transform_function=__sanitize_text)
    ),
    'properties_news': EntityDetailPropertyListCollection(
        [
            EntityDetailProperty('Link', True, entity_property_name='Link', transform_function=__get_value)
        ]
    ),
    'embed_settings': {
        'image_url': EntityDetailProperty('image_url', False, entity_property_name='SpriteId', transform_function=sprites.get_download_sprite_link_by_property),
        'footer': EntityDetailProperty('footer', False, transform_function=__get_news_footer),
        'timestamp': EntityDetailProperty('timestamp', False, entity_property_name='UpdateDate', transform_function=__get_pss_datetime)
    }
}