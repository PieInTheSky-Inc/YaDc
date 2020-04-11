#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import discord
import os
import re
from typing import Callable, Dict, List, Optional, Tuple, Union

import pss_assert
from cache import PssCache
import pss_core as core
import pss_entity as entity
import pss_lookups as lookups
import resources
import settings
import utility as util


# TODO: Create allowed values dictionary upon start.
# Get all item designs, split each ones name on ' ' and add each combination of 2 characters found to ALLOWED_ITEM_NAMES


# ---------- Constants ----------

ITEM_DESIGN_BASE_PATH = 'ItemService/ListItemDesigns2?languageKey=en'
ITEM_DESIGN_KEY_NAME = 'ItemDesignId'
ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ItemDesignName'










# ---------- Classes ----------

class ItemDesignDetails(entity.EntityDesignDetails):
    def __init__(self, entity_design_info: entity.EntityDesignInfo, title: entity.EntityDesignDetailProperty, description: entity.EntityDesignDetailProperty, properties_long: List[entity.EntityDesignDetailProperty], properties_embed: List[entity.EntityDesignDetailProperty], entities_designs_data: Optional[entity.EntitiesDesignsData] = None, prefix: str = None):
        self.__prefix: str = prefix or ''
        super().__init__(entity_design_info, title, description, properties_long, None, properties_embed, entities_designs_data=entities_designs_data)


    def get_details_as_text_long(self) -> List[str]:
        details = []
        for display_name, display_value in self.details_long:
            if display_value:
                if display_name:
                    details.append(f'{display_name} = {display_value}')
                else:
                    details.append(display_value)
        details_short = ''.join(self.get_details_as_text_short())
        result = [f'{details_short} - {", ".join(details)}']
        return result


    def get_details_as_text_short(self) -> List[str]:
        result = [f'{self.__prefix}{self.title} ({self.description})']
        return result










# ---------- Helper functions ----------

def __get_item_bonus_type_and_value(item_info: entity.EntityDesignInfo, items_designs_data: entity.EntitiesDesignsData) -> str:
    bonus_type = item_info['EnhancementType']
    bonus_value = item_info['EnhancementValue']
    if bonus_type.lower() == 'none':
        result = bonus_type
    else:
        result = f'{bonus_type} +{bonus_value}'
    return result


def __get_item_slot(item_info: entity.EntityDesignInfo, items_designs_data: entity.EntitiesDesignsData) -> str:
    item_type = item_info['ItemType']
    item_sub_type = item_info['ItemSubType']
    if item_type == 'Equipment' and 'Equipment' in item_sub_type:
        result = item_sub_type.replace('Equipment', '')
    else:
        result = None
    return result


def __get_item_price(item_info: entity.EntityDesignInfo, items_designs_data: entity.EntitiesDesignsData) -> str:
    flags = int(item_info['Flags'])
    if flags & 1 == 0:
        result = 'This item cannot be sold'
    else:
        fair_price = item_info['FairPrice']
        market_price = item_info['MarketPrice']
        result = f'{market_price} ({fair_price})'
    return result


def __get_enhancement_value(item_info: entity.EntityDesignInfo, items_designs_data: entity.EntitiesDesignsData) -> str:
    enhancement_value = float(item_info['EnhancementValue'])
    result = f'{enhancement_value:.1f}'
    return result


def __get_pretty_market_price(item_info: entity.EntityDesignInfo, items_designs_data: entity.EntitiesDesignsData) -> str:
    market_price = item_info['MarketPrice']
    result = f'{market_price} bux'
    return result


def __get_rarity(item_info: entity.EntityDesignInfo, items_designs_data: entity.EntitiesDesignsData) -> str:
    return item_info['Rarity']


def __create_base_design_data_from_info(item_design_info: entity.EntityDesignInfo) -> ItemDesignDetails:
    return ItemDesignDetails(item_design_info, __title_property, __description_property, __item_base_properties, __item_base_properties)


def __create_price_design_data_from_info(item_design_info: entity.EntityDesignInfo) -> ItemDesignDetails:
    return ItemDesignDetails(item_design_info, __title_property, __description_property, __item_price_properties, __item_price_properties)


def __create_best_design_data_from_info(item_design_info: entity.EntityDesignInfo) -> ItemDesignDetails:
    return ItemDesignDetails(item_design_info, __title_property, __description_property, __item_best_properties, __item_best_properties, prefix='> ')


def __create_best_design_data_list_from_infos(items_designs_infos: List[entity.EntityDesignInfo]) -> List[ItemDesignDetails]:
    return [__create_best_design_data_from_info(item_design_info) for item_design_info in items_designs_infos]


def __create_price_design_data_list_from_infos(items_designs_infos: List[entity.EntityDesignInfo]) -> List[ItemDesignDetails]:
    return [__create_price_design_data_from_info(item_design_info) for item_design_info in items_designs_infos]


def __create_base_design_data_list_from_infos(items_designs_infos: List[entity.EntityDesignInfo]) -> List[ItemDesignDetails]:
    return [__create_base_design_data_from_info(item_design_info) for item_design_info in items_designs_infos]


def __get_key_for_best_items_sort(item_info: dict) -> str:
    if item_info and item_info['EnhancementValue'] and item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]:
        slot = item_info['ItemSubType']
        rarity_num = lookups.RARITY_ORDER_LOOKUP[item_info['Rarity']]
        enhancement_value = int((1000.0 - float(item_info['EnhancementValue'])) * 10)
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        result = f'{enhancement_value}{slot}{rarity_num}{item_name}'
        return result


def _get_stat_filter(stat: str) -> str:
    stat = stat.lower()
    return lookups.STAT_TYPES_LOOKUP[stat]


def _get_slot_filter(slot: str, any_slot: bool) -> List[str]:
    slot = slot.lower()
    if any_slot:
        result = list(lookups.EQUIPMENT_SLOTS_LOOKUP.values())
    else:
        result = [lookups.EQUIPMENT_SLOTS_LOOKUP[slot]]
    return result










def get_item_details_short_from_id_as_text(item_id: str, items_designs_data: dict) -> list:
    item_info = items_designs_data[item_id]
    return get_item_details_short_from_data_as_text(item_info)


def get_item_details_short_from_data_as_text(item_info: dict) -> list:
    name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    rarity = item_info['Rarity']
    bonus_type = item_info['EnhancementType']  # if not 'None' then print bonus_value
    bonus_value = item_info['EnhancementValue']

    slot = __get_item_slot(item_info, None)
    details = [rarity]
    if slot:
        details.append(slot)
    if bonus_type != 'None':
        details.append(f'+{bonus_value} {bonus_type}')
    details_txt = ', '.join(details)
    return [f'{name} ({details_txt})']


async def get_item_info_from_id(item_id: str) -> dict:
    item_data = await items_designs_retriever.get_data_dict3()
    return item_data[item_id]


def get_item_design_details_by_id(item_design_id: str, items_designs_data: dict) -> ItemDesignDetails:
    if item_design_id and item_design_id in items_designs_data.keys():
        return __create_base_design_data_from_info(items_designs_data[item_design_id])
    else:
        return None


def _get_item_design_ids_from_name(item_name: str, items_designs_data: dict) -> list:
    results = core.get_ids_from_property_value(items_designs_data, ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, item_name, fix_data_delegate=_fix_item_name)
    return results


def _get_item_infos_by_name(item_name: str, items_designs_data: dict, return_best_match: bool = False) -> list:
    item_design_ids = _get_item_design_ids_from_name(item_name, items_designs_data)
    result = [items_designs_data[item_design_id] for item_design_id in item_design_ids if item_design_id in items_designs_data.keys()]

    if result:
        get_best_match = return_best_match or util.is_str_in_list(item_name, ALLOWED_ITEM_NAMES, case_sensitive=False) and len(item_name) < settings.MIN_ENTITY_NAME_LENGTH - 1
        if get_best_match:
            result = [result[0]]

    return result


def get_item_details_short_by_training_id(training_id: str, item_design_data: dict, return_best_match: bool = False) -> list:
    item_design_ids = core.get_ids_from_property_value(item_design_data, 'TrainingDesignId', training_id, fix_data_delegate=_fix_item_name, match_exact=True)
    result = [' '.join(get_item_design_details_by_id(item_design_id, item_design_data).get_details_as_text_long()) for item_design_id in item_design_ids]

    return result


def _fix_item_name(item_name) -> str:
    result = item_name.lower()
    result = re.sub('[^a-z0-9]', '', result)
    result = re.sub("(darkmatterrifle|dmr)(mark|mk)?(ii|2)", "dmrmarkii", result)
    result = result.replace('anonmask', 'anonymousmask')
    result = result.replace('armour', 'armor')
    result = result.replace('bunny', 'rabbit')
    result = result.replace('golden', 'gold')
    return result










# ---------- Item info ----------

async def get_item_details_by_name(item_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_designs_data = await items_designs_retriever.get_data_dict3()
    item_infos = _get_item_infos_by_name(item_name, items_designs_data)

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        item_infos = util.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])
        items_designs_details = __create_base_design_data_list_from_infos(item_infos)

        if as_embed:
            return _get_item_info_as_embed(item_name, items_designs_details), True
        else:
            return _get_item_info_as_text(item_name, items_designs_details), True


def _get_item_info_as_embed(item_name: str, items_designs_details: List[ItemDesignDetails]) -> List[discord.Embed]:
    result = [item_design_details.get_details_as_embed() for item_design_details in items_designs_details]
    return result


def _get_item_info_as_text(item_name: str, items_designs_details: List[ItemDesignDetails]) -> list:
    lines = [f'Item stats for **{item_name}**']

    for item_design_details in items_designs_details:
        lines.extend(item_design_details.get_details_as_text_long())

    return lines










# ---------- Price info ----------

async def get_item_price(item_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_designs_data = await items_designs_retriever.get_data_dict3()
    item_infos = _get_item_infos_by_name(item_name, items_designs_data)

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        get_best_match = util.is_str_in_list(item_name, ALLOWED_ITEM_NAMES, case_sensitive=False) and len(item_name) < settings.MIN_ENTITY_NAME_LENGTH - 1
        if get_best_match:
            item_infos = [item_infos[0]]

        item_infos = util.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])
        items_designs_details = __create_price_design_data_list_from_infos(item_infos)

        if as_embed:
            return _get_item_price_as_embed(item_name, items_designs_details), True
        else:
            return _get_item_price_as_text(item_name, items_designs_details), True


def _get_item_price_as_embed(item_name: str, items_designs_details: List[ItemDesignDetails]):
    result = [item_design_details.get_details_as_embed() for item_design_details in items_designs_details]
    return result


def _get_item_price_as_text(item_name: str, items_designs_details) -> str:
    lines = []
    lines.append(f'**Item prices matching \'{item_name}\'**')
    for item_design_details in items_designs_details:
        lines.extend(item_design_details.get_details_as_text_long())

    lines.append(settings.EMPTY_LINE)
    lines.append(' '.join([resources.get_resource('MARKET_FAIR_PRICE_NOTE'), resources.get_resource('PRICE_NOTE')]))

    return lines





# ---------- Ingredients info ----------

async def get_ingredients_for_item(item_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_designs_data = await items_designs_retriever.get_data_dict3()
    item_infos = _get_item_infos_by_name(item_name, items_designs_data, return_best_match=True)

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        item_info = item_infos[0]
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        ingredients_tree = _parse_ingredients_tree(item_info['Ingredients'], items_designs_data)
        ingredients_dicts = _flatten_ingredients_tree(ingredients_tree)
        if as_embed:
            return _get_item_ingredients_as_embed(item_name, ingredients_dicts, items_designs_data), True
        else:
            return _get_item_ingredients_as_text(item_name, ingredients_dicts, items_designs_data), True


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

        lines.append(resources.get_resource('PRICE_NOTE'))
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

async def get_item_upgrades_from_name(item_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_designs_data = await items_designs_retriever.get_data_dict3()
    item_ids = _get_item_design_ids_from_name(item_name, items_designs_data)

    if not item_ids:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        item_infos = []
        for item_id in item_ids:
            item_infos.extend(_get_upgrades_for(item_id, items_designs_data))
        item_infos = list(dict([(item_info[ITEM_DESIGN_KEY_NAME], item_info) for item_info in item_infos]).values())
        item_infos = util.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])

        if as_embed:
            return _get_item_upgrades_as_embed(item_name, item_infos, items_designs_data), True
        else:
            return _get_item_upgrades_as_text(item_name, item_infos, items_designs_data), True


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

async def get_best_items(slot: str, stat: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_parameter_value(slot, 'slot', allowed_values=lookups.EQUIPMENT_SLOTS_LOOKUP.keys())
    pss_assert.valid_parameter_value(stat, 'stat', allowed_values=lookups.STAT_TYPES_LOOKUP.keys())

    items_designs_details = await items_designs_retriever.get_data_dict3()
    error = _get_best_items_error(slot, stat)
    if error:
        return error, False

    any_slot = slot == 'all' or slot == 'any'
    slot_filter = _get_slot_filter(slot, any_slot)
    stat_filter = _get_stat_filter(stat)
    best_items = _get_best_items_designs(slot_filter, stat_filter, items_designs_details)

    if not best_items:
        return [f'Could not find an item for slot **{slot}** providing bonus **{stat}**.'], False
    else:
        if as_embed:
            return _get_best_items_as_embed(stat_filter, best_items), True
        else:
            return _get_best_items_as_text_all(stat_filter, best_items), True


def _get_best_items_designs(slot_filter: List[str], stat_filter: str, items_designs_data: dict) -> Dict[str, List[ItemDesignDetails]]:
    filters = {
        'ItemType': 'Equipment',
        'ItemSubType': slot_filter,
        'EnhancementType': stat_filter
    }
    result = {}

    filtered_data = core.filter_data_dict(items_designs_data, filters, ignore_case=True)
    if filtered_data:
        items_infos = sorted(filtered_data.values(), key=__get_key_for_best_items_sort)
        items_designs_details = __create_best_design_data_list_from_infos(items_infos)
        result = entity.group_entities_designs_details(items_designs_details, 'ItemSubType')
    return result


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


def _get_best_items_as_embed(stat: str, items_designs_details_groups: Dict[str, List[ItemDesignDetails]]) -> List[discord.Embed]:
    result = []

    for group_name in sorted(items_designs_details_groups.keys()):
        group = items_designs_details_groups[group_name]
        slot = _get_pretty_slot(group_name)
        result.append(discord.Embed(title=_get_best_title(stat, slot)))
        for item_design_details in group:
            result.extend(item_design_details.get_details_as_embed())
    return result


def _get_best_items_as_text_all(stat: str, items_designs_details_groups: Dict[str, List[ItemDesignDetails]]) -> List[str]:
    result = []

    for group_name, group in items_designs_details_groups.items():
        slot = _get_pretty_slot(group_name)
        result.append(settings.EMPTY_LINE)
        result.append(_get_best_title(stat, slot))
        for item_design_details in group:
            result.extend(item_design_details.get_details_as_text_long())

    result.append(settings.EMPTY_LINE)
    result.append(resources.get_resource('PRICE_NOTE'))

    return result


def _get_best_title(stat: str, slot: str) -> str:
    return f'Best **{stat}** bonus for **{slot}** slot'


def _get_pretty_slot(slot: str) -> str:
    return slot.replace('Equipment', '')










# ---------- Initilization ----------

NOT_ALLOWED_ITEM_NAMES: List[str] = None
ALLOWED_ITEM_NAMES: List[str] = None
__title_property: entity.EntityDesignDetailProperty = None
__description_property: entity.EntityDesignDetailProperty = None
__item_base_properties: List[entity.EntityDesignDetailProperty] = None
__item_price_properties: List[entity.EntityDesignDetailProperty] = None
__item_best_properties: List[entity.EntityDesignDetailProperty] = None
items_designs_retriever: entity.LegacyEntityDesignsRetriever = None


def __get_allowed_item_names(items_designs_data: dict):
    result = []
    for item_design_data in items_designs_data.values():
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


async def init():
    global items_designs_retriever
    global ALLOWED_ITEM_NAMES
    global NOT_ALLOWED_ITEM_NAMES
    items_designs_retriever = entity.LegacyEntityDesignsRetriever(
        ITEM_DESIGN_BASE_PATH,
        ITEM_DESIGN_KEY_NAME,
        ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME,
        'ItemsDesigns'
    )
    items_designs_data = await items_designs_retriever.get_data_dict3()
    NOT_ALLOWED_ITEM_NAMES = [
        'AI',
        'I',
        'II',
        'III',
        'IV',
        'V',
        'VI'
    ]
    ALLOWED_ITEM_NAMES = sorted(__get_allowed_item_names(items_designs_data))

    global __title_property
    global __description_property
    global __item_base_properties
    global __item_price_properties
    global __item_best_properties
    __title_property = entity.EntityDesignDetailProperty('Title', False, entity_property_name=ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
    __description_property = entity.EntityDesignDetailProperty('Description', False, transform_function=__get_rarity)
    __item_base_properties = [
        entity.EntityDesignDetailProperty('Bonus', False, transform_function=__get_item_bonus_type_and_value),
        entity.EntityDesignDetailProperty('Slot', False, transform_function=__get_item_slot)
    ]
    __item_price_properties = [
        entity.EntityDesignDetailProperty('Prices', False, transform_function=__get_item_price)
    ]
    __item_best_properties = [
        entity.EntityDesignDetailProperty('EnhancementValue', False, transform_function=__get_enhancement_value),
        entity.EntityDesignDetailProperty('MarketPrice', False, transform_function=__get_pretty_market_price)
    ]










# --------- Testing ----------
#if __name__ == '__main__':
#    test_strings = ['scrap']
#    for item_name in test_strings:
#        os.system('clear')
#        result = get_item_upgrades_from_name(item_name, as_embed=False)
#        for line in result[0]:
#            print(line)
#        result = ''