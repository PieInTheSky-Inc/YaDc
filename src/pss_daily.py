from datetime import date, datetime
import json
import random
from typing import Any, Callable, Dict, List, Tuple, Union

from discord import Embed
from discord.ext.commands import Context

from . import database as db
from . import emojis
from . import pss_core as core
from . import pss_entity as entity
from .pss_exception import Error
from . import pss_item as item
from . import pss_crew as crew
from . import pss_lookups as lookups
from . import pss_research as research
from . import pss_room as room
from . import pss_training as training
from . import server_settings
from .server_settings import AutoMessageSettings
from . import settings
from .typehints import EntityInfo, SalesCache
from . import utils


# ---------- Constants ----------

DAILY_INFO_FIELDS: List[str] = [
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
    'SaleType',
    'SaleRewardString',
    'SaleTitle'
]

DAILY_INFO_FIELDS_TO_CHECK: List[str] = [
    'LimitedCatalogArgument',
    'LimitedCatalogCurrencyAmount',
    'LimitedCatalogCurrencyType',
    'LimitedCatalogMaxTotal',
    'LimitedCatalogType',
]

DB_DAILY_INFO_COLUMN_NAMES: Dict[str, str] = {f'daily{setting_name}': setting_name for setting_name in DAILY_INFO_FIELDS}

LATE_SALES_PORTAL_HYPERLINK: str = 'https://pixelstarships.com/PlayerCenter/Sales'
LIMITED_CATALOG_TYPE_GET_ENTITY_FUNCTIONS: Dict[str, Callable] = {
    'item': item.get_item_details_by_id,
    'character': crew.get_char_details_by_id,
    'research': research.get_research_details_by_id,
    'room': room.get_room_details_by_id
}

SALES_DAILY_INFO_FIELDS: Dict[str, Callable] = {
    'LimitedCatalogArgument': int,
    'LimitedCatalogCurrencyAmount': int,
    'LimitedCatalogCurrencyType': str,
    'LimitedCatalogExpiryDate': utils.parse.pss_datetime,
    'LimitedCatalogMaxTotal': int,
    'LimitedCatalogType': str
}





# ---------- Sales info ----------

async def add_sale(entity_id: int, price: int, currency_type: str, entity_type: str, expires_at: datetime, max_amount: int) -> bool:
    already_exists = len([sale_info for sale_info in __sales_info_cache if sale_info['limitedcatalogexpirydate'] == expires_at])
    if already_exists:
        raise Error(f'There\'s already a sale info in the database expiring on: {utils.format.date(expires_at)}')
    success = await db_add_sale(entity_id, price, currency_type, entity_type, expires_at, max_amount)
    if success:
        await update_db_sales_info_cache()
    return success


async def clear_sales() -> None:
    query = f'DELETE FROM sales'
    success = await db.try_execute(query)
    return success


async def get_oldest_expired_sale_entity_details(utc_now: datetime, for_embed: bool = False) -> List[str]:
    db_sales_infos = await __db_get_sales_infos(utc_now=utc_now)
    sales_infos = await __process_db_sales_infos(db_sales_infos, utc_now)
    sales_infos = reversed(sales_infos)
    for sales_info in sales_infos:
        expiring_entity_details = '\n'.join((await sales_info['entity_details'].get_details_as_text(entity.EntityDetailsType.MEDIUM, for_embed=for_embed)))
        price = sales_info['price']
        currency = sales_info['currency']
        result = f'{expiring_entity_details}: {price} {currency}'
        return [result]
    return None


async def get_sales_infos(category_type: str = None, currency_type: str = None) -> SalesCache:
    result = list(__sales_info_cache)
    if category_type:
        result = [sales_info for sales_info in result if sales_info['limitedcatalogtype'] == category_type]
    if currency_type:
        result = [sales_info for sales_info in result if sales_info['limitedcatalogcurrencytype'] == currency_type]
    return result


async def get_sales_details(ctx: Context, reverse: bool = False, as_embed: bool = settings.USE_EMBEDS) -> Union[List[str], List[Embed]]:
    utc_now = utils.get_utc_now()
    db_sales_infos = await __db_get_sales_infos(utc_now=utc_now)
    sales_infos = await __process_db_sales_infos(db_sales_infos, utc_now)
    if reverse:
        sales_infos = reversed(sales_infos)

    title = 'Expired sales'
    description = f'The things listed below have been sold in the {emojis.pss_shop} shop over the past 30 days. You\'ve got the chance to buy them on the Pixel Starships website for an additional 25% on the original price.'

    sales_details = []
    for sales_info in sales_infos:
        expires_in = sales_info['expires_in']
        day = 'day' + ('' if expires_in == 1 else 's')
        details = f'**{expires_in}** {day}: **{sales_info["name"]}** ({sales_info["type"]}) {sales_info["currency"]} {sales_info["price"]}'
        sales_details.append(details)
    if as_embed:
        body_lines = [description, utils.discord.ZERO_WIDTH_SPACE]
        body_lines.extend(sales_details)
        colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
        footer = 'Click on the title to get redirected to the Late Sales portal, where you can purchase these offers.'
        result = utils.discord.create_basic_embeds_from_description(title, description=body_lines, colour=colour, footer=footer, author_url=LATE_SALES_PORTAL_HYPERLINK)
    else:
        result = [
            f'**{title}**',
            f'_{description}_'
        ]
        result.extend(sales_details)
        result.append(f'_Visit <{LATE_SALES_PORTAL_HYPERLINK}> to purchase these offers._')
    return result


async def get_sales_history(ctx: Context, entity_info: EntityInfo, reverse: bool = False, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    utc_now = utils.get_utc_now()

    category_type = entity_info.get('entity_type')
    entity_id = entity_info.get('entity_id')
    entity_id = int(entity_id) if entity_id else None
    entity_name = entity_info.get('entity_name')

    db_sales_infos = await __db_get_sales_infos(utc_now=utc_now, category_type=category_type, entity_id=entity_id)
    sales_infos = await __process_db_sales_infos(db_sales_infos, utc_now, filter_old=(entity_id is None))
    if reverse:
        sales_infos = reversed(sales_infos)

    if sales_infos:
        title = f'{entity_name} has been sold on'
        sales_details = []
        for sales_info in sales_infos:
            sold_on_date = sales_info['expiry_date'] - utils.datetime.ONE_DAY
            sold_on = utils.datetime.get_discord_datestamp(sold_on_date)
            star_date = utils.datetime.get_star_date(sold_on_date)
            sold_ago = (utc_now - sold_on_date).days
            price = sales_info['original_price']
            currency = sales_info['currency']
            day = 'day' + 's' if sold_ago != 1 else ''
            sales_details.append(f'{sold_on} (Star date {star_date}, {sold_ago} {day} ago) for {price} {currency}')

        if as_embed:
            colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            result = utils.discord.create_basic_embeds_from_description(title, description=sales_details, colour=colour)
        else:
            result = [f'**{title}**']
            result.extend(sales_details)
        return result
    raise Error(f'There is no past sales data available for {entity_name}.')


async def get_sales_history_for_rooms(ctx: Context, room_type: str, room_type_pretty: str, reverse: bool = False, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    if not room_type:
        raise ValueError('The room type must neither be None nor empty.')
    utc_now = utils.get_utc_now()

    db_sales_infos = await __db_get_sales_infos(utc_now=utc_now, category_type='Room')
    sales_infos = await __process_db_sales_infos(db_sales_infos, utc_now, filter_old=False)
    sales_infos = [sales_info for sales_info in sales_infos if sales_info['entity_details'].entity_info['RoomType'] == room_type]

    if sales_infos:
        title = f'{room_type_pretty.capitalize()}s have been sold on'
        sales_details = []
        for sales_info in sales_infos:
            name = sales_info['name']
            sold_on_date = sales_info['expiry_date'] - utils.datetime.ONE_DAY
            sold_on = utils.datetime.get_discord_datestamp(sold_on_date)
            star_date = utils.datetime.get_star_date(sold_on_date)
            sold_ago = (utc_now - sold_on_date).days
            price = sales_info['original_price']
            currency = sales_info['currency']
            day = 'day' + 's' if sold_ago != 1 else ''
            sales_details.append(f'{sold_on} (Star date {star_date}, {sold_ago} {day} ago): **{name}** for {price} {currency}')

        if as_embed:
            colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            result = utils.discord.create_basic_embeds_from_description(title, description=sales_details, colour=colour)
        else:
            result = [f'**{title}**']
            result.extend(sales_details)
        return result
    raise Error(f'There is no past sales data available for {room_type_pretty}s.')


def get_sales_search_details(entity_info: EntityInfo) -> str:
    entity_type = entity_info.get('entity_type')
    entity_name = entity_info.get('entity_name')
    if not entity_name:
        if entity_type in ['Character', 'Crew']:
            entity_name = entity_info[crew.CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
        elif entity_type == 'Item':
            entity_name = entity_info[item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        elif entity_type == 'Room':
            entity_name = entity_info[room.ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]

    result = f'{entity_name} ({entity_type})'
    return result


def get_sales_search_details_with_id(entity_info: EntityInfo) -> str:
    result = get_sales_search_details(entity_info)
    entity_id = entity_info.get('entity_id')
    result += f' id: {entity_id}'
    return result


async def __process_db_sales_infos(db_sales_infos: List[Dict[str, Any]], utc_now: datetime, filter_old: bool = True) -> List[Dict[str, Any]]:
    chars_data = await crew.characters_designs_retriever.get_data_dict3()
    collections_data = await crew.collections_designs_retriever.get_data_dict3()
    items_data = await item.items_designs_retriever.get_data_dict3()
    researches_data = await research.researches_designs_retriever.get_data_dict3()
    rooms_data = await room.rooms_designs_retriever.get_data_dict3()
    rooms_designs_sprites_data = await room.rooms_designs_sprites_retriever.get_data_dict3()
    trainings_data = await training.trainings_designs_retriever.get_data_dict3()

    result = []

    for db_sales_info in db_sales_infos:
        expiry_date: datetime = db_sales_info['limitedcatalogexpirydate']
        if expiry_date.date() > utc_now.date():
            continue
        expires_in = 30 - (utc_now - expiry_date).days
        if filter_old and expires_in < 1:
            continue
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





# ---------- Helper functions ----------

__SALES_FIELDS: List[str] = [
    'limitedcatalogargument',
    'limitedcatalogtype',
    'limitedcatalogcurrencytype',
    'limitedcatalogcurrencyamount',
    'limitedcatalogmaxtotal',
    'limitedcatalogexpirydate',
]

__SALES_FIELDS_PLACEHOLDERS_TEXT: str = ', '.join(f'${i+1}' for i, _ in enumerate(__SALES_FIELDS))
__SALES_FIELDS_TEXT: List[str] = ', '.join(__SALES_FIELDS)


async def db_add_sale(entity_id: int, price: int, currency_type: str, entity_type: str, expires_at: datetime, max_amount: int, overwrite: bool = False) -> bool:
    query = f'INSERT INTO sales ({__SALES_FIELDS_TEXT}) VALUES ({__SALES_FIELDS_PLACEHOLDERS_TEXT})'
    args = [
        entity_id,
        entity_type,
        currency_type,
        price,
        max_amount,
        expires_at
    ]
    try:
        success = await db.try_execute(query, args, raise_db_error=True)
    except Exception as ex:
        success = False
        if not overwrite:
            error_msg = '\n'.join([
                'Could not add sales to database.',
                f'Query: {query}',
                f'Values: {args}'
            ])
            raise Error(error_msg) from ex
    if not success and overwrite:
        success_delete = await _db_try_remove_sale(expires_at)
        if success_delete:
            success = await db_add_sale(entity_id, price, currency_type, entity_type, expires_at, max_amount)
    return success


async def _db_try_remove_sale(expiry_date: datetime) -> bool:
    if not expiry_date:
        raise ValueError('The parameter \'expiry_date\' is required.')
    query = f'DELETE FROM sales WHERE limitedcatalogexpirydate = $1'
    args = (expiry_date,)
    success = db.try_execute(query, args)
    return success


async def db_get_daily_info(skip_cache: bool = False) -> Tuple[EntityInfo, datetime]:
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


async def db_set_daily_info(daily_info: EntityInfo, utc_now: datetime) -> bool:
    settings = {__get_daily_info_setting_name(key): (value or None, utc_now) for key, value in daily_info.items()}
    settings_success = await db.set_settings(settings)
    if settings_success:
        await __update_db_daily_info_cache()

    sales_info = {key: value(daily_info[key]) for key, value in SALES_DAILY_INFO_FIELDS.items()}
    sales_success = await db.update_sales_info(sales_info)
    if sales_success:
        await update_db_sales_info_cache()

    return settings_success


async def get_daily_channels(ctx: Context, guild_id: int = None, can_post: bool = None) -> List[str]:
    settings = await server_settings.db_get_automessage_settings(server_settings.AutoMessageType.DAILY, guild_id, can_post)
    result = []
    at_least_one = False
    for (guild_id, channel_id, can_post, _, _, _, _) in settings:
        if channel_id:
            at_least_one = True
            text_channel = ctx.bot.get_channel(int(channel_id))
            if text_channel:
                guild = text_channel.guild
                result.append(f'{guild.name}: #{text_channel.name} ({can_post})')
            else:
                guild = ctx.bot.get_guild(guild_id)
                result.append(f'{guild.name}: Invalid channel id: {channel_id}')
    if not at_least_one:
        result.append('Auto-posting of the daily announcement is not configured for any server!')
    return result


async def get_daily_info(language_key: str = 'en') -> EntityInfo:
    latest_settings = await core.get_latest_settings(language_key)
    live_ops_info = await core.get_liveops_info(language_key)
    latest_settings.update(live_ops_info)
    result = __convert_to_daily_info(latest_settings)
    return result


def has_daily_changed(daily_info: Dict[str, str], retrieved_date: datetime, db_daily_info: EntityInfo, db_modify_date: datetime) -> bool:
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
        daily_info.pop('News', None) # News and SaleTitle are language-dependent
        daily_info.pop('SaleTitle', None) 
        db_daily_info = db_daily_info.copy()
        db_daily_info.pop('News', None)
        db_daily_info.pop('SaleTitle', None)
        return not utils.dicts_equal(daily_info, db_daily_info)


def remove_duplicate_autodaily_settings(autodaily_settings: List[AutoMessageSettings]) -> List[AutoMessageSettings]:
    if not autodaily_settings:
        return autodaily_settings
    result = {}
    for autodaily_setting in autodaily_settings:
        if autodaily_setting.guild_id and autodaily_setting.guild_id not in result.keys():
            result[autodaily_setting.guild_id] = autodaily_setting
    return list(result.values())


def __convert_to_daily_info(dropship_info: EntityInfo) -> EntityInfo:
    result = {}
    for field_name in DAILY_INFO_FIELDS:
        value = None
        if field_name in dropship_info.keys():
            value = dropship_info[field_name]
        result[field_name] = value or None
    return result


async def __db_get_sales_infos(utc_now: datetime = None, category_type: str = None, entity_id: int = None, skip_cache: bool = False) -> SalesCache:
    if not skip_cache and utc_now is not None and (__sales_info_cache_retrieved_at is None or __sales_info_cache_retrieved_at.day != utc_now.day):
        await update_db_sales_info_cache()
    if skip_cache:
        result = await db.get_sales_infos()
    else:
        result = __sales_info_cache
    if entity_id:
        result = [db_sales_info for db_sales_info in result if db_sales_info['limitedcatalogargument'] == entity_id]
    if category_type:
        result = [db_sales_info for db_sales_info in result if db_sales_info['limitedcatalogtype'] == category_type]
    return result


def __get_daily_info_setting_name(field_name: str) -> str:
    return f'daily{field_name}'





# ---------- Mocks ----------

def mock_get_daily_info() -> EntityInfo:
    utc_now = utils.get_utc_now()
    if utc_now.hour < 1:
        if utc_now.minute < 20:
            return __mock_get_daily_info_1()
        else:
            return __mock_get_daily_info_2()
    else:
        return __mock_get_daily_info_1()


def __mock_get_daily_info_1() -> EntityInfo:
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


def __mock_get_daily_info_2() -> EntityInfo:
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
__sales_info_cache: SalesCache = None
__sales_info_cache_retrieved_at: datetime = None


async def __update_db_daily_info_cache() -> None:
    global __daily_info_cache
    global __daily_info_modified_at
    __daily_info_cache, __daily_info_modified_at = await db_get_daily_info(skip_cache=True)


async def update_db_sales_info_cache() -> None:
    global __sales_info_cache
    global __sales_info_cache_retrieved_at
    __sales_info_cache = await __db_get_sales_infos(skip_cache=True)
    __sales_info_cache_retrieved_at = utils.get_utc_now()


async def init() -> None:
    await __update_db_daily_info_cache()
    await update_db_sales_info_cache()