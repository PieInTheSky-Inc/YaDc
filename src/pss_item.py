#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re

import pss_assert
from cache import PssCache
import pss_core as core
import pss_lookups as lookups
import utility as util


# ---------- Constants ----------

ITEM_DESIGN_BASE_PATH = 'ItemService/ListItemDesigns2?languageKey=en'
ITEM_DESIGN_KEY_NAME = 'ItemDesignId'
ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ItemDesignName'
ALLOWED_ITEM_NAMES = [
    'U'
]



# ---------- Initilization ----------

__item_designs_cache = PssCache(
    ITEM_DESIGN_BASE_PATH,
    'ItemDesigns',
    ITEM_DESIGN_KEY_NAME)





# ---------- Helper functions ----------

def get_item_details_from_id_as_text(item_id: str, item_designs_data: dict = None) -> list:
    if not item_designs_data:
        item_designs_data = __item_designs_cache.get_data_dict3()

    item_info = item_designs_data[item_id]
    return get_item_details_from_data_as_text(item_info)


def get_item_details_from_data_as_text(item_info: dict) -> list:
    bonus_type = item_info['EnhancementType'] # if not 'None' then print bonus_value
    bonus_value = item_info['EnhancementValue']
    equipment_slot = item_info['ItemSubType']
    item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    item_type = item_info['ItemType']  # if 'Equipment' then print equipment slot
    rarity = item_info['Rarity']

    if item_type == 'Equipment' and 'Equipment' in equipment_slot:
        slot_txt = ' ({})'.format(equipment_slot.replace('Equipment', ''))
    else:
        slot_txt = ''

    if bonus_type == 'None':
        bonus_txt = bonus_type
    else:
        bonus_txt = f'+{bonus_value} {bonus_type}'

    return [f'{item_name} ({rarity}) - {bonus_txt}{slot_txt}']


def get_item_details_short_from_id_as_text(item_id: str, item_designs_data: dict = None) -> list:
    if not item_designs_data:
        item_designs_data = __item_designs_cache.get_data_dict3()

    item_info = item_designs_data[item_id]
    return get_item_details_short_from_data_as_text(item_info)


def get_item_details_short_from_data_as_text(item_info: dict) -> list:
    name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    rarity = item_info['Rarity']
    bonus_type = item_info['EnhancementType'] # if not 'None' then print bonus_value
    bonus_value = item_info['EnhancementValue']
    if bonus_type == 'None':
        bonus_txt = ''
    else:
        bonus_txt = f', +{bonus_value} {bonus_type}'
    return [f'{name} ({rarity}{bonus_txt})']





# ---------- Item info ----------

def get_item_details(item_name: str, as_embed=False):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    return_on_first = util.is_str_in_list(item_name, ALLOWED_ITEM_NAMES, case_sensitive=False)
    item_infos = _get_item_infos(item_name, return_on_first=return_on_first)

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        if as_embed:
            return _get_item_info_as_embed(item_name, item_infos), True
        else:
            return _get_item_info_as_text(item_name, item_infos), True


def _get_item_infos(item_name: str, item_design_data: dict = None, return_on_first: bool = False):
    if item_design_data is None:
        item_design_data = __item_designs_cache.get_data_dict3()

    item_design_ids = _get_item_design_ids_from_name(item_name, item_data=item_design_data, return_on_first=return_on_first)
    result = [item_design_data[item_design_id] for item_design_id in item_design_ids if item_design_id in item_design_data.keys()]

    return result


def _get_item_design_ids_from_name(item_name: str, item_data: dict = None, return_on_first: bool = False):
    if item_data is None:
        item_data = __item_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(item_data, ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, item_name, fix_data_delegate=_fix_item_name, return_on_first=return_on_first)
    return results


def _get_item_info_as_embed(item_name: str, item_infos: dict):
    return ''


def _get_item_info_as_text(item_name: str, item_infos: dict):
    lines = [f'**Item stats for \'{item_name}\'**']

    for item_info in item_infos:
        lines.extend(get_item_details_from_data_as_text(item_info))

    return lines


def _fix_item_name(item_name):
    result = item_name.lower()
    result = re.sub('[^a-z0-9]', '', result)
    result = re.sub("(darkmatterrifle|dmr)(mark|mk)?(ii|2)", "dmrmarkii", result)
    result = result.replace('anonmask', 'anonymousmask')
    result = result.replace('armour', 'armor')
    result = result.replace('bunny', 'rabbit')
    result = result.replace('golden', 'gold')
    return result





# ---------- Price info ----------

def get_item_price(item_name: str, as_embed: bool = False):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    return_on_first = pss_assert.string_in_list(item_name, ALLOWED_ITEM_NAMES, case_sensitive=False)
    item_infos = _get_item_infos(item_name, return_on_first=return_on_first)

    if not item_infos:
        return f'Could not find an item named **{item_name}**.', False
    else:
        if as_embed:
            return _get_item_price_as_embed(item_name, item_infos), True
        else:
            return _get_item_price_as_text(item_name, item_infos), True


def _get_item_price_as_embed(item_name, item_infos):
    return ''


def _get_item_price_as_text(item_name, item_infos) -> str:
    lines = []
    lines.append(f'**Item prices matching \'{item_name}\'**')
    for item_info in item_infos:
        flags = int(item_info['Flags'])
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        fair_price = item_info['FairPrice']
        market_price = item_info['MarketPrice']
        rarity = item_info['Rarity']

        prices = f'{market_price} ({fair_price})'
        if flags & 1 == 0:
            prices = 'This item cannot be sold'

        lines.append(f'{item_name} ({rarity}) - {prices}')

    lines.append('')
    lines.append('**Note:** 1st price is the market price. 2nd price is Savy\'s fair price. Market prices listed here may not always be accurate due to transfers between alts/friends or other reasons.')

    return lines





# ---------- Ingredients info ----------

def get_ingredients_for_item(item_name: str, as_embed: bool = False):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    item_design_data = __item_designs_cache.get_data_dict3()
    item_infos = _get_item_infos(item_name, item_design_data, return_on_first=True)

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        item_info = item_infos[0]
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        ingredients_tree = _parse_ingredients_tree(item_info['Ingredients'], item_design_data)
        ingredients_dicts = _flatten_ingredients_tree(ingredients_tree)
        if as_embed:
            return _get_item_ingredients_as_embed(item_name, ingredients_dicts, item_design_data), True
        else:
            return _get_item_ingredients_as_text(item_name, ingredients_dicts, item_design_data), True


def _get_item_ingredients_as_embed(item_name, ingredients_dicts, item_design_data):
    return ''


def _get_item_ingredients_as_text(item_name, ingredients_dicts, item_design_data):
    lines = [f'**Ingredients for {item_name}**']
    ingredients_dicts = [d for d in ingredients_dicts if d]

    if ingredients_dicts:
        for ingredients_dict in ingredients_dicts:
            current_level_lines = []
            current_level_costs = 0
            for item_id, item_amount in ingredients_dict.items():
                item_info = item_design_data[item_id]
                item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
                item_price = int(item_info['MarketPrice'])
                price_sum = item_price * item_amount
                current_level_costs += price_sum
                current_level_lines.append(f'{item_amount} x {item_name} ({item_price} bux ea): {price_sum} bux')
            lines.extend(current_level_lines)
            lines.append(f'Crafting costs: {current_level_costs} bux')
            lines.append('')

        lines.append('**Note**: bux prices listed here may not always be accurate due to transfers between alts/friends or other reasons.')
    else:
        lines.append('This item can\'t be crafted')

    return lines


def _parse_ingredients_tree(ingredients_str: str, item_design_data: dict, parent_amount: int = 1) -> list:
    """returns a tree structure: [(item_id, item_amount, item_ingredients[])]"""
    if not ingredients_str:
        return []

    # Ingredients format is: [<id>x<amount>][|<id>x<amount>]*
    ingredients_dict = dict([split_str.split('x') for split_str in ingredients_str.split('|')])
    result = []

    for item_id, item_amount in ingredients_dict.items():
        item_info = item_design_data[item_id]
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME].lower()
        item_amount = int(item_amount)
        # Filter out void particles and scrap
        if 'void particle' not in item_name and ' fragment' not in item_name:
            combined_amount = item_amount * parent_amount
            item_ingredients = _parse_ingredients_tree(item_info['Ingredients'], item_design_data, combined_amount)
            result.append((item_id, combined_amount, item_ingredients))

    return result


def _flatten_ingredients_tree(ingredients_tree: list) -> list:
    """Returns a list of dicts"""
    ingredients = {}
    ingredients_without_subs = []
    sub_ingredients = []

    for item_id, item_amount, item_ingredients in ingredients_tree:
        if item_id in ingredients.keys():
            ingredients[item_id] += item_amount
        else:
            ingredients[item_id] = item_amount

        if item_ingredients:
            sub_ingredients.extend(item_ingredients)
        else:
            ingredients_without_subs.append((item_id, item_amount, item_ingredients))

    result = [ingredients]

    if len(ingredients_without_subs) != len(ingredients_tree):
        sub_ingredients.extend(ingredients_without_subs)
        flattened_subs = _flatten_ingredients_tree(sub_ingredients)
        result.extend(flattened_subs)

    return result





# ---------- Best info -----------

_SLOTS_AVAILABLE = 'These are valid values for the _slot_ parameter: all/any (for all slots), {}'.format(', '.join(lookups.EQUIPMENT_SLOTS_LOOKUP.keys()))
_STATS_AVAILABLE = 'These are valid values for the _stat_ parameter: {}'.format(', '.join(lookups.STAT_TYPES_LOOKUP.keys()))

def get_best_items(slot: str, stat: str, as_embed: bool = False):
    pss_assert.valid_parameter_value(slot, 'slot', allowed_values=lookups.EQUIPMENT_SLOTS_LOOKUP.keys())
    pss_assert.valid_parameter_value(stat, 'stat', allowed_values=lookups.STAT_TYPES_LOOKUP.keys())

    error = _get_best_items_error(slot, stat)
    if error:
        return error, False

    slot = slot.lower()
    stat = stat.lower()

    any_slot = slot == 'all' or slot == 'any'

    item_design_data = __item_designs_cache.get_data_dict3()
    if any_slot:
        slot_filter = list(lookups.EQUIPMENT_SLOTS_LOOKUP.values())
    else:
        slot_filter = lookups.EQUIPMENT_SLOTS_LOOKUP[slot]
    stat_filter = lookups.STAT_TYPES_LOOKUP[stat]
    filters = {
        'ItemType': 'Equipment',
        'ItemSubType': slot_filter,
        'EnhancementType': stat_filter
    }

    filtered_data = core.filter_data_dict(item_design_data, filters, ignore_case=True)

    if not filtered_data:
        return [f'Could not find an item for slot **{slot}** providing bonus **{stat}**.'], False
    else:
        if any_slot:
            key_function = _get_key_for_best_items_sort_all
            slot_display = None
        else:
            key_function = _get_key_for_best_items_sort
            slot_display = slot_filter.replace('Equipment', '')

        match_design_data = sorted(filtered_data.values(), key=key_function)
        stat_display = stat_filter

        if as_embed:
            return _get_best_items_as_embed(slot_display, stat_display, any_slot, match_design_data), True
        else:
            if any_slot:
                return _get_best_items_as_text_all(stat_display, match_design_data), True
            else:
                return _get_best_items_as_text(slot_display, stat_display, match_design_data), True


def _get_best_items_error(slot: str, stat: str) -> list:
    if not slot:
        return [f'You must specify an equipment slot!', _SLOTS_AVAILABLE]
    if not stat:
        return [f'You must specify a stat!', _STATS_AVAILABLE]
    slot = slot.lower()
    if slot not in lookups.EQUIPMENT_SLOTS_LOOKUP.keys() and slot not in ['all', 'any']:
        return [f'The specified equipment slot is not valid!', _SLOTS_AVAILABLE]
    if stat.lower() not in lookups.STAT_TYPES_LOOKUP.keys():
        return [f'The specified stat is not valid!', _STATS_AVAILABLE]

    return []


def _get_key_for_best_items_sort(item_info: dict) -> str:
    if item_info and item_info['EnhancementValue'] and item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]:
        enhancement_value = int((1000.0 - float(item_info['EnhancementValue'])) * 10)
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        result = f'{enhancement_value}{item_name}'
        return result


def _get_key_for_best_items_sort_all(item_info: dict) -> str:
    if item_info and item_info['EnhancementValue'] and item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]:
        slot = item_info['ItemSubType']
        enhancement_value = int((1000.0 - float(item_info['EnhancementValue'])) * 10)
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        result = f'{enhancement_value}{slot}{item_name}'
        return result


def _get_best_items_as_embed(slot: str, stat: str, any_slots: bool, item_designs: list):
    return []


def _get_best_items_as_text(slot: str, stat: str, item_designs: list) -> list:
    lines = [f'**Best {stat} bonus for {slot} slot**']

    for entry in item_designs:
        lines.append(_get_best_item_line(entry))

    lines.append('')
    lines.append('**Note:** bux prices listed here may not always be accurate due to transfers between alts/friends or other reasons.')

    return lines


def _get_best_items_as_text_all(stat: str, item_designs: list) -> list:
    lines = [f'**Best {stat} bonus for...**']

    groups = core.group_data_list(item_designs, 'ItemSubType')

    for group_name, group in groups.items():
        group_name = group_name.replace('Equipment', '')
        lines.append(f'**...{group_name} slot**')
        for entry in group:
            lines.append(_get_best_item_line(entry))

    lines.append('')
    lines.append('**Note:** bux prices listed here may not always be accurate due to transfers between alts/friends or other reasons.')

    return lines


def _get_best_item_line(item_info: dict):
    name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    market_price = item_info['MarketPrice']
    rarity = item_info['Rarity']
    enhancement_value = float(item_info['EnhancementValue'])
    result = f'{name} ({rarity}): {enhancement_value:.1f} ({market_price} bux)'
    return result