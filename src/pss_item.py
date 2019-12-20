#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import re

import pss_assert
from cache import PssCache
import pss_core as core
import pss_lookups as lookups
import settings
import utility as util


# TODO: Create allowed values dictionary upon start.
# Get all item designs, split each ones name on ' ' and add each combination of 2 characters found to ALLOWED_ITEM_NAMES


# ---------- Constants ----------

ITEM_DESIGN_BASE_PATH = 'ItemService/ListItemDesigns2?languageKey=en'
ITEM_DESIGN_KEY_NAME = 'ItemDesignId'
ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ItemDesignName'



# ---------- Initilization ----------

__item_designs_cache = PssCache(
    ITEM_DESIGN_BASE_PATH,
    'ItemDesigns',
    ITEM_DESIGN_KEY_NAME)


NOT_ALLOWED_ITEM_NAMES = [
    'AI',
    'I',
    'II',
    'III',
    'IV',
    'V',
    'VI'
]


def __get_allowed_item_names():
    result = []
    item_designs_data = __item_designs_cache.get_data_dict3()
    for item_design_data in item_designs_data.values():
        if ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME in item_design_data.keys():
            item_name = item_design_data[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            if item_name:
                item_name = core.fix_allowed_value_candidate(item_name)
                if len(item_name) < settings.MIN_ENTITY_NAME_LENGTH:
                    result.append(item_name)
                else:
                    item_name_parts = item_name.split(' ')
                    for item_name_part in item_name_parts:
                        part_length = len(item_name_part)
                        length_matches = part_length > 1 and part_length < settings.MIN_ENTITY_NAME_LENGTH
                        is_proper_name = item_name_part == item_name_part.upper()
                        if length_matches and is_proper_name:
                            try:
                                int(item_name_part)
                                continue
                            except:
                                if item_name_part not in NOT_ALLOWED_ITEM_NAMES:
                                    result.append(item_name_part)
    if result:
        result = list(set(result))
    return result


__allowed_item_names = sorted(__get_allowed_item_names())






# ---------- Helper functions ----------

def get_item_details_from_id_as_text(item_id: str, item_designs_data: dict = None) -> list:
    if not item_designs_data:
        item_designs_data = __item_designs_cache.get_data_dict3()

    item_info = item_designs_data[item_id]
    return get_item_details_from_data_as_text(item_info)


def get_item_details_from_data_as_text(item_info: dict) -> list:
    bonus_type = item_info['EnhancementType'] # if not 'None' then print bonus_value
    bonus_value = item_info['EnhancementValue']
    item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    item_type = item_info['ItemType']  # if 'Equipment' then print equipment slot
    item_sub_type = item_info['ItemSubType']
    rarity = item_info['Rarity']

    slot = _get_item_slot(item_type, item_sub_type)
    if slot:
        slot_txt = f' ({slot})'
    else:
        slot_txt = ''

    if bonus_type == 'None':
        bonus_txt = bonus_type
    else:
        bonus_txt = f'{bonus_type} +{bonus_value}'

    return [f'{item_name} ({rarity}) - {bonus_txt}{slot_txt}']


def get_item_details_short_from_id_as_text(item_id: str, item_designs_data: dict = None) -> list:
    if not item_designs_data:
        item_designs_data = __item_designs_cache.get_data_dict3()

    item_info = item_designs_data[item_id]
    return get_item_details_short_from_data_as_text(item_info)


def get_item_details_short_from_data_as_text(item_info: dict) -> list:
    name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    rarity = item_info['Rarity']
    bonus_type = item_info['EnhancementType']  # if not 'None' then print bonus_value
    item_type = item_info['ItemType']
    item_sub_type = item_info['ItemSubType']
    bonus_value = item_info['EnhancementValue']

    slot = _get_item_slot(item_type, item_sub_type)
    details = [rarity]
    if slot:
        details.append(slot)
    if bonus_type != 'None':
        details.append(f'+{bonus_value} {bonus_type}')
    details_txt = ', '.join(details)
    return [f'{name} ({details_txt})']


def get_item_info_from_id(item_id: str) -> dict:
    item_data = __item_designs_cache.get_data_dict3()
    return item_data[item_id]


def _get_item_slot(item_type: str, item_sub_type: str) -> str:
    if item_type == 'Equipment' and 'Equipment' in item_sub_type:
        result = item_sub_type.replace('Equipment', '')
    else:
        result = None
    return result





# ---------- Item info ----------

def get_item_details(item_name: str, as_embed=False):
    pss_assert.valid_entity_name(item_name, allowed_values=__allowed_item_names)

    item_infos = _get_item_infos_by_name(item_name)

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        item_infos = util.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])

        if as_embed:
            return _get_item_info_as_embed(item_name, item_infos), True
        else:
            return _get_item_info_as_text(item_name, item_infos), True


def _get_item_infos_by_name(item_name: str, item_design_data: dict = None, return_best_match: bool = False) -> list:
    if item_design_data is None:
        item_design_data = __item_designs_cache.get_data_dict3()

    item_design_ids = _get_item_design_ids_from_name(item_name, item_data=item_design_data)
    result = [item_design_data[item_design_id] for item_design_id in item_design_ids if item_design_id in item_design_data.keys()]

    if result:
        get_best_match = return_best_match or util.is_str_in_list(item_name, __allowed_item_names, case_sensitive=False) and len(item_name) < settings.MIN_ENTITY_NAME_LENGTH - 1
        if get_best_match:
            result = [result[0]]

    return result


def get_item_details_short_by_training_id(training_id: str, item_design_data: dict = None, return_best_match: bool = False) -> list:
    if item_design_data is None:
        item_design_data = __item_designs_cache.get_data_dict3()

    item_design_ids = core.get_ids_from_property_value(item_design_data, 'TrainingDesignId', training_id, fix_data_delegate=_fix_item_name)
    result = [get_item_details_short_from_id_as_text(item_design_id) for item_design_id in item_design_ids]

    return result


def _get_item_design_ids_from_name(item_name: str, item_data: dict = None) -> list:
    if item_data is None:
        item_data = __item_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(item_data, ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, item_name, fix_data_delegate=_fix_item_name)
    return results


def _get_item_info_as_embed(item_name: str, item_infos: dict):
    return ''


def _get_item_info_as_text(item_name: str, item_infos: dict) -> list:
    lines = [f'**Item stats for \'{item_name}\'**']

    for item_info in item_infos:
        lines.extend(get_item_details_from_data_as_text(item_info))

    return lines


def _fix_item_name(item_name) -> str:
    result = item_name.lower()
    result = re.sub('[^a-z0-9]', '', result)
    result = re.sub("(darkmatterrifle|dmr)(mark|mk)?(ii|2)", "dmrmarkii", result)
    result = result.replace('anonmask', 'anonymousmask')
    result = result.replace('armour', 'armor')
    result = result.replace('bunny', 'rabbit')
    result = result.replace('golden', 'gold')
    return result





# ---------- Price info ----------

def get_item_price(item_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=__allowed_item_names)

    item_infos = _get_item_infos_by_name(item_name)

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        get_best_match = util.is_str_in_list(item_name, __allowed_item_names, case_sensitive=False) and len(item_name) < settings.MIN_ENTITY_NAME_LENGTH - 1
        if get_best_match:
            item_infos = [item_infos[0]]

        item_infos = util.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])

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

    lines.append(settings.EMPTY_LINE)
    lines.append('**Note:** 1st price is the market price. 2nd price is Savy\'s fair price. Market prices listed here may not always be accurate due to transfers between alts/friends or other reasons.')

    return lines





# ---------- Ingredients info ----------

def get_ingredients_for_item(item_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=__allowed_item_names)

    item_design_data = __item_designs_cache.get_data_dict3()
    item_infos = _get_item_infos_by_name(item_name, item_design_data, return_best_match=True)

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
                current_level_lines.append(f'> {item_amount} x {item_name} ({item_price} bux ea): {price_sum} bux')
            lines.extend(current_level_lines)
            lines.append(f'Crafting costs: {current_level_costs} bux')
            lines.append(settings.EMPTY_LINE)

        lines.append('**Note**: bux prices listed here may not always be accurate due to transfers between alts/friends or other reasons.')
    else:
        lines.append('This item can\'t be crafted')

    return lines


def _parse_ingredients_tree(ingredients_str: str, item_design_data: dict, parent_amount: int = 1) -> list:
    """returns a tree structure: [(item_id, item_amount, item_ingredients[])]"""
    if not ingredients_str:
        return []

    # Ingredients format is: [<id>x<amount>][|<id>x<amount>]*
    ingredients_dict = _get_ingredients_dict(ingredients_str)
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


def _get_ingredients_dict(ingredients: str) -> dict:
    result = {}
    if ingredients and ingredients != '0':
        result = dict([ingredient.split('x') for ingredient in ingredients.split('|')])
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






# ---------- Upgrade info ----------

def get_item_upgrades_from_name(item_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=__allowed_item_names)

    item_design_data = __item_designs_cache.get_data_dict3()
    item_ids = _get_item_design_ids_from_name(item_name)
    item_infos = _get_item_infos_by_name(item_name)

    if not item_ids:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        item_infos = []
        for item_id in item_ids:
            item_infos.extend(_get_upgrades_for(item_id, item_design_data))
        item_infos = util.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])

        if as_embed:
            return _get_item_upgrades_as_embed(item_name, item_infos, item_design_data), True
        else:
            return _get_item_upgrades_as_text(item_name, item_infos, item_design_data), True


def _get_upgrades_for(item_id: str, item_design_data: dict) -> list:
    # iterate through item_design_data and return every item_design containing the item id in question in property 'Ingredients'
    result = []
    for item_info in item_design_data.values():
        ingredient_item_ids = list(_get_ingredients_dict(item_info['Ingredients']).keys())
        if item_id in ingredient_item_ids:
            result.append(item_info)
    return result


def _get_item_upgrades_as_embed(item_name: str, item_infos: dict, item_design_data: dict):
    return ''


def _get_item_upgrades_as_text(item_name: str, item_infos: dict, item_design_data) -> list:
    lines = [f'**Crafting recipes requiring {item_name}**']

    if item_infos:
        for item_info in item_infos:
            lines.append(f'**{item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]}**')
            ingredients = _get_ingredients_dict(item_info['Ingredients'])
            for item_id, amount in ingredients.items():
                ingredient_info = item_design_data[item_id]
                lines.append(f'> {ingredient_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]} x{amount}')
    else:
        lines.append(f'This item cannot be upgraded.')

    return lines





# ---------- Best info -----------

_SLOTS_AVAILABLE = 'These are valid values for the _slot_ parameter: all/any (for all slots), {}'.format(', '.join(lookups.EQUIPMENT_SLOTS_LOOKUP.keys()))
_STATS_AVAILABLE = 'These are valid values for the _stat_ parameter: {}'.format(', '.join(lookups.STAT_TYPES_LOOKUP.keys()))

def get_best_items(slot: str, stat: str, as_embed: bool = settings.USE_EMBEDS):
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


def __get_key_for_best_items_sort(item_info: dict, consider_slots: bool) -> str:
    if item_info and item_info['EnhancementValue'] and item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]:
        if consider_slots:
            slot = item_info['ItemSubType']
        else:
            slot = ''
        rarity_num = lookups.RARITY_ORDER_LOOKUP[item_info['Rarity']]
        enhancement_value = int((1000.0 - float(item_info['EnhancementValue'])) * 10)
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        result = f'{enhancement_value}{slot}{rarity_num}{item_name}'
        return result


def _get_key_for_best_items_sort(item_info: dict) -> str:
    return __get_key_for_best_items_sort(item_info, True)


def _get_key_for_best_items_sort_all(item_info: dict) -> str:
    return __get_key_for_best_items_sort(item_info, False)


def _get_best_items_as_embed(slot: str, stat: str, any_slots: bool, item_designs: list):
    return []


def _get_best_items_as_text(slot: str, stat: str, item_designs: list) -> list:
    lines = [f'**Best {stat} bonus for {slot} slot**']

    for entry in item_designs:
        lines.append(_get_best_item_line(entry))

    lines.append(settings.EMPTY_LINE)
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

    lines.append(settings.EMPTY_LINE)
    lines.append('**Note:** bux prices listed here may not always be accurate due to transfers between alts/friends or other reasons.')

    return lines


def _get_best_item_line(item_info: dict):
    name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    market_price = item_info['MarketPrice']
    rarity = item_info['Rarity']
    enhancement_value = float(item_info['EnhancementValue'])
    result = f'> {name} ({rarity}) - {enhancement_value:.1f} ({market_price} bux)'
    return result










# --------- Testing ----------
if __name__ == '__main__':
    test_strings = ['scrap']
    for item_name in test_strings:
        os.system('clear')
        result = get_item_upgrades_from_name(item_name, as_embed=False)
        for line in result[0]:
            print(line)
        result = ''