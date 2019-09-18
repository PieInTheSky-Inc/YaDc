#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from cache import PssCache
import pss_core as core
import pss_crew as crew
import pss_item as item
import pss_lookups as lookups
import pss_room as room


# ---------- Constants ----------





# ---------- Initilization ----------





# ---------- Helper functions ----------

def _get_daily_item_info(item_id: str, item_designs_data: dict) -> str:
    result = ''

    pass


def _convert_sale_item_mask(sale_item_mask: int) -> str:
    result = []
    for flag in lookups.SALE_ITEM_MASK_LOOKUP.keys():
        if (sale_item_mask & flag) != 0:
            result.append(lookups.SALE_ITEM_MASK_LOOKUP[flag])
    if result:
        if len(result) > 1:
            return f'{", ".join(result[:-1])} or {result[-1]}'
        else:
            return result[0]
    else:
        return ''




# ---------- Dropship info ----------

def get_dropship_text(as_embed: bool = False):
    path = 'SettingService/GetLatestVersion3?languageKey=en&deviceType=DeviceTypeAndroid'
    raw_text = core.get_data_from_path(path)
    raw_data = core.xmltree_to_dict2(raw_text, None)[0]

    collection_design_data = crew.__collection_designs_cache.get_data_dict3()
    char_design_data = crew.__character_designs_cache.get_data_dict3()
    item_design_data = item.__item_designs_cache.get_data_dict3()
    room_design_data = room.__room_designs_cache.get_data_dict3()

    daily_msg = _get_daily_msg(raw_data)
    dropship_msg = _get_dropship_msg(raw_data, char_design_data, collection_design_data)
    merchantship_msg = _get_merchantship_msg(raw_data, item_design_data)
    shop_msg = _get_shop_msg(raw_data, char_design_data, collection_design_data, item_design_data, room_design_data)
    sale_msg = _get_sale_msg(raw_data, char_design_data, collection_design_data, item_design_data, room_design_data)

    lines = daily_msg
    lines.append('')
    lines.extend(dropship_msg)
    lines.append('')
    lines.extend(merchantship_msg)
    lines.append('')
    lines.extend(shop_msg)
    lines.append('')
    lines.extend(sale_msg)

    return lines, True


def _get_daily_msg(raw_data: dict) -> list:
    result = ['No news have been provided :(']
    if raw_data and 'News' in raw_data.keys():
        result = [raw_data['News']]
    return result


def _get_dropship_msg(raw_data: dict, char_designs_data: dict, collection_designs_data: dict) -> list:
    result = ['**Dropship crew**']
    if raw_data:
        common_crew_id = raw_data['CommonCrewId']
        hero_crew_id = raw_data['HeroCrewId']

        common_crew_info = crew.get_char_info_short_from_id_as_text(common_crew_id, char_designs_data, collection_designs_data)
        hero_crew_info = crew.get_char_info_short_from_id_as_text(hero_crew_id, char_designs_data, collection_designs_data)

        common_crew_rarity = char_designs_data[common_crew_id]['Rarity']
        if common_crew_rarity in ['Unique', 'Epic', 'Hero', 'Special', 'Legendary']:
            common_crew_info.append(' - any unique & above crew that costs minerals is probably worth buying (just blend it if you don\'t need it)!')

        if common_crew_info:
            result.append(f'Common crew: {"".join(common_crew_info)}')
        if hero_crew_info:
            result.append(f'Hero crew: {hero_crew_info[0]}')
    else:
        result.append('-')
    return result


def _get_merchantship_msg(raw_data: dict, item_designs_data: dict) -> list:
    result = ['**Merchant ship**']
    if raw_data:
        cargo_items = raw_data['CargoItems'].split('|')
        cargo_prices = raw_data['CargoPrices'].split('|')
        for i, cargo_info in enumerate(cargo_items):
            item_id, amount = cargo_info.split('x')
            item_details = ''.join(item.get_item_details_short_from_id_as_text(item_id, item_designs_data))
            currency, price = cargo_prices[i].split(':')
            result.append(f'{amount} x {item_details}: {price} {currency}')
    else:
        result.append('-')
    return result


def _get_shop_msg(raw_data: dict, char_designs_data: dict, collection_designs_data: dict, item_designs_data: dict, room_designs_data: dict) -> list:
    result = ['**Shop**']

    shop_type = raw_data['LimitedCatalogType']
    currency_type = raw_data['LimitedCatalogCurrencyType']
    price = raw_data['LimitedCatalogCurrencyAmount']
    can_own_max = raw_data['LimitedCatalogMaxTotal']

    if shop_type == 'Character':
        char_id = raw_data['LimitedCatalogArgument']
        char_details = crew.get_char_info_short_from_id_as_text(char_id, char_designs_data, collection_designs_data)
        result.extend(char_details)
    elif shop_type == 'Item':
        item_id = raw_data['LimitedCatalogArgument']
        item_details = item.get_item_details_short_from_id_as_text(item_id, item_designs_data)
        result.extend(item_details)
    elif shop_type == 'Room':
        room_id = raw_data['LimitedCatalogArgument']
        room_details = room.get_room_details_short_from_id_as_text(room_id, room_designs_data)
        result.extend(room_details)
    else:
        result.append('-')
        return result

    result.append(f'Cost: {price} {currency_type}')
    result.append(f'Can own (max): {can_own_max}')

    return result


def _get_sale_msg(raw_data: dict, char_designs_data: dict, collection_designs_data: dict, item_designs_data: dict, room_designs_data: dict) -> list:
    # 'SaleItemMask': use lookups.SALE_ITEM_MASK_LOOKUP to print which item to buy
    result = ['**Sale**']

    sale_item_mask = raw_data['SaleItemMask']
    sale_items = _convert_sale_item_mask(int(sale_item_mask))
    sale_quantity = raw_data['SaleQuantity']
    result.append(f'Buy a {sale_items} of Starbux and get:')

    sale_type = raw_data['SaleType']
    entity_id = raw_data['SaleArgument']
    if sale_type == 'Character':
        entity_details = ''.join(crew.get_char_info_short_from_id_as_text(entity_id, char_designs_data, collection_designs_data))
    elif sale_type == 'Item':
        entity_details = ''.join(item.get_item_details_short_from_id_as_text(entity_id, item_designs_data))
    elif sale_type == 'Room':
        entity_details = ''.join(room.get_room_details_short_from_id_as_text(entity_id, room_designs_data))
    else: # Print debugging info
        sale_title = raw_data['SaleTitle']
        debug_details = []
        debug_details.append(f'Sale Type: {sale_type}')
        debug_details.append(f'Sale Argument: {entity_id}')
        debug_details.append(f'Sale Title: {sale_title}')
        entity_details = '\n'.join(debug_details)

    result.append(f'{sale_quantity} x {entity_details}')

    return result