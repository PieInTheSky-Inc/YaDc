from datetime import datetime
import pprint
from typing import List, Optional, Tuple, Union

from discord import Embed, Guild, Message
from discord.ext.commands import Bot, Context

from . import emojis
from . import pss_core as core
from . import pss_crew as crew
from . import pss_daily as daily
from . import pss_entity as entity
from .pss_exception import Error
from . import pss_item as item
from . import pss_lookups as lookups
from . import pss_mission as mission
from . import pss_room as room
from . import pss_situation as situation
from . import pss_sprites as sprites
from . import pss_training as training
from . import settings
from .typehints import EntitiesData, EntityInfo
from . import utils


# ---------- Constants ----------

DROPSHIP_BASE_PATH: str = 'SettingService/GetLatestVersion3?deviceType=DeviceTypeAndroid&languageKey='
LIVEOPS_BASE_PATH: str = 'LiveOpsService/GetTodayLiveOps?deviceType=DeviceTypeAndroid&languageKey='





# ---------- Dropship info ----------

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


async def get_dropship_text(bot: Bot = None, guild: Guild = None, daily_info: dict = None, utc_now: datetime = None, language_key: str = 'en') -> Tuple[List[str], List[Embed], bool]:
    utc_now = utc_now or utils.get_utc_now()
    if not daily_info:
        daily_info = await daily.get_daily_info(language_key)

    chars_designs_data = await crew.characters_designs_retriever.get_data_dict3()
    collections_designs_data = await crew.collections_designs_retriever.get_data_dict3()
    items_designs_data = await item.items_designs_retriever.get_data_dict3()
    missions_designs_data = await mission.missions_designs_retriever.get_data_dict3()
    rooms_designs_data = await room.rooms_designs_retriever.get_data_dict3()
    situations_designs_data = await situation.situations_designs_retriever.get_data_dict3()
    trainings_designs_data = await training.trainings_designs_retriever.get_data_dict3()

    try:
        daily_msg = __get_daily_news_from_info_as_text(daily_info)
        dropship_msg = await __get_dropship_msg_from_info_as_text(daily_info, chars_designs_data, collections_designs_data)
        merchantship_msg = await __get_merchantship_msg_from_info_as_text(daily_info, items_designs_data, trainings_designs_data)
        shop_msg, image_id = await __get_shop_msg_from_info_as_text(daily_info, chars_designs_data, collections_designs_data, items_designs_data, rooms_designs_data, trainings_designs_data)
        daily_reward_msg = await __get_daily_reward_from_info_as_text(daily_info, items_designs_data, trainings_designs_data)
    except Exception as e:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(daily_info)
        print(e)
        return [], [], False

    parts_text = [dropship_msg, merchantship_msg, shop_msg, daily_reward_msg]

    expiring_sale_details_text = await daily.get_oldest_expired_sale_entity_details(utc_now, for_embed=False)
    if expiring_sale_details_text:
        expiring_sale_details_text.append(f'_Visit <{daily.LATE_SALES_PORTAL_HYPERLINK}> to purchase this offer._')
        expiring_sale_details_text.insert(0, '**Sale expiring today**')

    expiring_sale_details_embed = await daily.get_oldest_expired_sale_entity_details(utc_now, for_embed=True)
    if expiring_sale_details_embed:
        expiring_sale_details_embed.append(f'_Visit the [Late Sales Portal]({daily.LATE_SALES_PORTAL_HYPERLINK}) to purchase this offer._')
        expiring_sale_details_embed.insert(0, '**Sale expiring today**')

    current_events_details_text, event_sprite_id = await __get_current_events_details_as_text(situations_designs_data, chars_designs_data, collections_designs_data, items_designs_data, missions_designs_data, rooms_designs_data, utc_now)
    if current_events_details_text:
        plural = '(s)' if len(current_events_details_text) > 1 else ''
        current_events_details_text.insert(0, f'**Current event{plural} running**')
        parts_text.insert(0, current_events_details_text)

    parts_embed = list(parts_text)

    if expiring_sale_details_text:
        parts_text.append(expiring_sale_details_text)
    if expiring_sale_details_embed:
        parts_embed.append(expiring_sale_details_embed)

    lines = list(daily_msg)
    for part in parts_text:
        lines.append(utils.discord.ZERO_WIDTH_SPACE)
        lines.extend(part)

    title = 'Pixel Starships Dropships'
    footer = f'Star date {utils.datetime.get_star_date(utc_now)}'
    description = ''.join(daily_msg)
    fields = [(part[0], '\n'.join(part[1:]), False) for part in parts_embed if part]
    thumbnail_url = await sprites.get_download_sprite_link(daily_info['NewsSpriteId'])
    image_url = await sprites.get_download_sprite_link(image_id) if image_id else None
    icon_url = await sprites.get_download_sprite_link(event_sprite_id) if event_sprite_id else None
    if thumbnail_url == image_url:
        thumbnail_url = None
    colour = utils.discord.get_bot_member_colour(bot, guild)
    embed = utils.discord.create_embed(title, description=description, fields=fields, thumbnail_url=thumbnail_url, image_url=image_url, icon_url=icon_url, colour=colour, footer=footer)

    return lines, [embed], True


async def __get_current_events_details_as_text(situations_designs_data: EntitiesData, chars_designs_data: EntitiesData, collections_designs_data: EntitiesData, items_designs_data: EntitiesData, missions_designs_data: EntitiesData, rooms_designs_data: EntitiesData, utc_now: datetime) -> Optional[Tuple[List[str], str]]:
    events_details = await situation.get_current_events_details(situations_designs_data, chars_designs_data, collections_designs_data, items_designs_data, missions_designs_data, rooms_designs_data, utc_now)
    if events_details:
        result = []
        sprite_id = None
        for event_details in events_details:
            result.append(''.join(await event_details.get_details_as_text(entity.EntityDetailsType.MEDIUM)))
            icon_sprite_id = event_details.entity_info['IconSpriteId']
            if not sprite_id and entity.entity_property_has_value(icon_sprite_id):
                sprite_id = icon_sprite_id
        return result, sprite_id
    else:
        return None, None


def __get_daily_news_from_info_as_text(daily_info: EntityInfo) -> List[str]:
    result = ['No news have been provided :(']
    if daily_info and 'News' in daily_info.keys():
        result = [daily_info['News']]
    return result


async def __get_dropship_msg_from_info_as_text(daily_info: EntityInfo, chars_data: EntitiesData, collections_data: EntitiesData) -> List[str]:
    result = [f'{emojis.pss_dropship} **Dropship crew**']
    if daily_info:
        common_crew_id = daily_info['CommonCrewId']
        common_crew_details = crew.get_char_details_by_id(common_crew_id, chars_data, collections_data)
        common_crew_info = await common_crew_details.get_details_as_text(entity.EntityDetailsType.MEDIUM)

        hero_crew_id = daily_info['HeroCrewId']
        hero_crew_details = crew.get_char_details_by_id(hero_crew_id, chars_data, collections_data)
        hero_crew_info = await hero_crew_details.get_details_as_text(entity.EntityDetailsType.MEDIUM)

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


async def __get_merchantship_msg_from_info_as_text(daily_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData) -> List[str]:
    result = [f'{emojis.pss_merchantship} **Merchant ship**']
    if daily_info:
        cargo_items = daily_info['CargoItems'].split('|')
        cargo_prices = daily_info['CargoPrices'].split('|')
        for i, cargo_info in enumerate(cargo_items):
            _, item_id, amount, _ = utils.parse.entity_string(cargo_info)
            if item_id:
                item_details = item.get_item_details_by_id(item_id, items_data, trainings_data)
                item_details = ''.join(await item_details.get_details_as_text(entity.EntityDetailsType.MEDIUM))
                currency_type, currency_id, currency_amount, _ = utils.parse.entity_string(cargo_prices[i])
                currency_type = currency_type.lower()
                if 'item' in currency_type:
                    key = f'item{currency_id}'
                    currency = lookups.get_lookup_value_or_default(lookups.CURRENCY_EMOJI_LOOKUP, key)
                    if not currency:
                        currency_item_details = item.get_item_details_by_id(currency_id, items_data, trainings_data)
                        currency = ''.join(await currency_item_details.get_details_as_text(entity.EntityDetailsType.MINI))
                else:
                    currency_amount = currency_id
                    currency = lookups.get_lookup_value_or_default(lookups.CURRENCY_EMOJI_LOOKUP, currency_type, default=currency_type)
                result.append(f'{amount} x {item_details}: {currency_amount} {currency}')
    else:
        result.append('-')
    return result


async def __get_shop_msg_from_info_as_text(daily_info: EntityInfo, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, rooms_data: EntitiesData, trainings_data: EntitiesData) -> Tuple[List[str], str]:
    result = [f'{emojis.pss_shop} **Shop**']

    shop_type = daily_info['LimitedCatalogType']
    currency_type = daily_info['LimitedCatalogCurrencyType']
    currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP.get(currency_type.lower(), currency_type)
    price = daily_info['LimitedCatalogCurrencyAmount']
    can_own_max = daily_info['LimitedCatalogMaxTotal']

    entity_id = daily_info['LimitedCatalogArgument']
    entity_details_txt = []
    if shop_type == 'Character':
        char_details = crew.get_char_details_by_id(entity_id, chars_data, collections_data)
        entity_details_txt = await char_details.get_details_as_text(entity.EntityDetailsType.MEDIUM)
        sprite_id = char_details.entity_info.get('ProfileSpriteId')
    elif shop_type == 'Item':
        item_details = item.get_item_details_by_id(entity_id, items_data, trainings_data)
        entity_details_txt = await item_details.get_details_as_text(entity.EntityDetailsType.MEDIUM)
        logo_sprite_id = item_details.entity_info.get('LogoSpriteId')
        image_sprite_id = item_details.entity_info.get('ImageSpriteId')
        sprite_id = logo_sprite_id if logo_sprite_id != image_sprite_id else None
    elif shop_type == 'Room':
        room_details = room.get_room_details_by_id(entity_id, rooms_data, None, None, None)
        entity_details_txt = await room_details.get_details_as_text(entity.EntityDetailsType.MEDIUM)
        sprite_id = room_details.entity_info.get('ImageSpriteId')
    else:
        result.append('-')
        return result, None

    if entity_details_txt:
        result.extend(entity_details_txt)

    sprite_id = sprite_id if entity.entity_property_has_value(sprite_id) else None

    result.append(f'Cost: {price} {currency_emoji}')
    result.append(f'Can own (max): {can_own_max}')

    return result, sprite_id


async def __get_daily_reward_from_info_as_text(daily_info: EntityInfo, item_data: EntitiesData, trainings_data: EntitiesData) -> List[str]:
    result = ['**Daily rewards**']

    reward_currency = daily_info['DailyRewardType'].lower()
    reward_currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[reward_currency]
    reward_amount = int(daily_info['DailyRewardArgument'])
    reward_amount, reward_multiplier = utils.format.get_reduced_number(reward_amount)
    result.append(f'{reward_amount:.0f}{reward_multiplier} {reward_currency_emoji}')

    item_rewards = daily_info['DailyItemRewards'].split('|')
    for item_reward in item_rewards:
        item_id, amount = item_reward.split('x')
        item_details: entity.EntityDetails = item.get_item_details_by_id(item_id, item_data, trainings_data)
        item_details_text = ''.join(await item_details.get_details_as_text(entity.EntityDetailsType.MEDIUM))
        result.append(f'{amount} x {item_details_text}')

    return result





# ---------- News info ----------

async def get_news(ctx: Context, take: int = 5, as_embed: bool = settings.USE_EMBEDS, language_key: str = 'en') -> Union[List[Embed], List[str]]:
    path = f'SettingService/ListAllNewsDesigns?languageKey={language_key}'

    try:
        raw_text = await core.get_data_from_path(path)
        raw_data = utils.convert.xmltree_to_dict3(raw_text)
    except Exception as err:
        raw_data = None
        raise Error(f'Could not get news: {err}')

    if raw_data:
        news_infos = sorted(list(raw_data.values()), key=lambda news_info: news_info['UpdateDate'])
        news_count = len(news_infos)
        if news_count > take:
            news_infos = news_infos[news_count-take:]
        news_details_collection = __create_news_details_collection_from_infos(news_infos)

        if as_embed:
            return (await news_details_collection.get_entities_details_as_embed(ctx))
        else:
            return (await news_details_collection.get_entities_details_as_text())





# ---------- Transformation functions ----------

def __get_news_footer(news_info: EntityInfo, **kwargs) -> Optional[str]:
    return 'PSS News'


def __get_pss_datetime(*args, **kwargs) -> datetime:
    entity_property = kwargs.get('entity_property')
    result = utils.parse.pss_datetime(entity_property)
    return result


def __get_value(*args, **kwargs) -> Optional[str]:
    entity_property = kwargs.get('entity_property')
    if entity.entity_property_has_value(entity_property):
        return entity_property
    else:
        return None


def __sanitize_text(*args, **kwargs) -> Optional[str]:
    entity_property = kwargs.get('entity_property')
    if entity_property:
        result = utils.escape_escape_sequences(entity_property)
        while '\n\n' in result:
            result = result.replace('\n\n', '\n')
        return result
    else:
        return None





# ---------- Create entity.EntityDetails ----------

def __create_news_details_collection_from_infos(news_infos: List[EntityInfo]) -> entity.EntityDetailsCollection:
    base_details = [__create_news_details_from_info(news_info) for news_info in news_infos]
    result = entity.EntityDetailsCollection(base_details, big_set_threshold=0)
    return result


def __create_news_details_from_info(news_info: EntityInfo) -> entity.EntityDetails:
    return entity.EntityDetails(news_info, __properties['title_news'], __properties['description_news'], __properties['properties_news'], __properties['embed_settings'])





# ---------- Initilization ----------

__properties: entity.EntityDetailsCreationPropertiesCollection = {
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