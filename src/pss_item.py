#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import discord
import discord.ext.commands as commands
import os
import re
from typing import Callable, Dict, List, Optional, Tuple, Union

import pss_assert
from cache import PssCache
import pss_core as core
import pss_entity as entity
import pss_lookups as lookups
import pss_sprites as sprites
import pss_training as training
import resources
import settings
import utility as util


# TODO: Create allowed values dictionary upon start.
# Get all item designs, split each ones name on ' ' and add each combination of 2 characters found to ALLOWED_ITEM_NAMES










# ---------- Constants ----------

ITEM_DESIGN_BASE_PATH = 'ItemService/ListItemDesigns2?languageKey=en'
ITEM_DESIGN_KEY_NAME = 'ItemDesignId'
ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ItemDesignName'

CANNOT_BE_SOLD = 'Can\'t be sold'










# ---------- Item info ----------

async def get_item_details_by_name(item_name: str, ctx: commands.Context = None, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_data = await items_designs_retriever.get_data_dict3()
    item_infos = _get_item_infos_by_name(item_name, items_data)

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        trainings_data = await training.trainings_designs_retriever.get_data_dict3()
        items_data_for_sort = {item_info.get(ITEM_DESIGN_KEY_NAME): item_info for item_info in item_infos}
        item_infos = sorted(item_infos, key=lambda item_info: (
            _get_key_for_base_items_sort(item_info, items_data_for_sort)
        ))
        items_details_collection = __create_base_details_collection_from_infos(item_infos, items_data, trainings_data)

        if as_embed:
            return (await items_details_collection.get_entity_details_as_embed(ctx)), True
        else:
            return (await items_details_collection.get_entity_details_as_text()), True


def _get_key_for_base_items_sort(item_info: dict, items_data: entity.EntitiesData) -> str:
    result = item_info.get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
    item_sub_type = item_info.get('ItemSubType')
    if entity.has_value(item_sub_type) and item_sub_type in lookups.ITEM_SUB_TYPES_TO_GET_PARENTS_FOR:
        parents = __get_parents(item_info, items_data)
        if parents:
            result = parents[0].get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
            result += ''.join([item_info.get(ITEM_DESIGN_KEY_NAME).zfill(4) for item_info in parents])
    return result










# ---------- Best info -----------

_SLOTS_AVAILABLE = 'These are valid values for the _slot_ parameter: all/any (for all slots), {}'.format(', '.join(lookups.EQUIPMENT_SLOTS_LOOKUP.keys()))
_STATS_AVAILABLE = 'These are valid values for the _stat_ parameter: {}'.format(', '.join(lookups.STAT_TYPES_LOOKUP.keys()))

async def get_best_items(slot: str, stat: str, ctx: commands.Context = None, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_parameter_value(slot, 'slot', allowed_values=lookups.EQUIPMENT_SLOTS_LOOKUP.keys(), allow_none_or_empty=True)
    pss_assert.valid_parameter_value(stat, 'stat', allowed_values=lookups.STAT_TYPES_LOOKUP.keys())

    items_details = await items_designs_retriever.get_data_dict3()
    error = _get_best_items_error(slot, stat)
    if error:
        return error, False

    any_slot = not slot or slot == 'all' or slot == 'any'
    slot_filter = _get_slot_filter(slot, any_slot)
    stat_filter = _get_stat_filter(stat)
    best_items = _get_best_items_designs(slot_filter, stat_filter, items_details)

    if not best_items:
        return [f'Could not find an item for slot **{slot}** providing bonus **{stat}**.'], False
    else:
        groups = await __get_collection_groups(best_items, ctx, stat_filter, as_embed)

        result = []
        if as_embed:
            for title, best_items_collection in groups.items():
                embeds = await best_items_collection.get_entity_details_as_embed(ctx, custom_title=title, custom_footer_text=resources.get_resource('PRICE_NOTE_EMBED'))
                result.extend(embeds)
            return result, True
        else:
            for title, best_items_collection in groups.items():
                texts = await best_items_collection.get_entity_details_as_text(custom_title=title)
                result.extend(texts)
                result.append(settings.EMPTY_LINE)
            result.append(resources.get_resource('PRICE_NOTE'))
            return result, True


async def __get_collection_groups(best_items: Dict[str, List[entity.EntityDetails]], ctx: commands.Context, stat: str, as_embed: bool) -> Dict[str, entity.EntityDetailsCollection]:
    result = {}
    group_names_sorted = sorted(best_items.keys(), key=lambda x: lookups.EQUIPMENT_SLOTS_ORDER_LOOKUP.index(x))

    for group_name in group_names_sorted:
        group = best_items[group_name]
        title = _get_best_title(stat, *_get_pretty_slot(group_name), use_markdown=(not as_embed))

        items_details_collection = __create_best_details_collection_from_details(group)
        result[title] = items_details_collection
    return result


def _get_best_items_designs(slot_filter: List[str], stat_filter: str, items_data: dict) -> Dict[str, List[entity.EntityDetails]]:
    filters = {
        'ItemType': 'Equipment',
        'ItemSubType': slot_filter,
        'EnhancementType': stat_filter
    }
    result = {}

    filtered_data = core.filter_data_dict(items_data, filters, ignore_case=True)

    if filtered_data:
        items_infos = sorted(filtered_data.values(), key=_get_key_for_best_items_sort)
        # Filter out destroyed modules
        items_infos = [item_info for item_info in items_infos if item_info.get('ItemSubType') != 'Module' or entity.has_value(item_info.get('ModuleArgument'))]
        items_details = __create_best_details_list_from_infos(items_infos, items_data)
        result = entity.group_entities_details(items_details, 'ItemSubType')
    return result


def _get_best_items_error(slot: str, stat: str) -> list:
    if not stat:
        return [f'You must specify a stat!', _STATS_AVAILABLE]
    if slot:
        slot = slot.lower()
        if slot not in lookups.EQUIPMENT_SLOTS_LOOKUP.keys() and slot not in ['all', 'any']:
            return [f'The specified equipment slot is not valid!', _SLOTS_AVAILABLE]
    if stat.lower() not in lookups.STAT_TYPES_LOOKUP.keys():
        return [f'The specified stat is not valid!', _STATS_AVAILABLE]

    return []


def _get_best_title(stat: str, slot: str, is_equipment_slot: bool, use_markdown: bool = True) -> str:
    bold_marker = '**' if use_markdown else ''
    slot_text = ' slot' if is_equipment_slot else 's'
    return f'Best {bold_marker}{stat}{bold_marker} bonus for {bold_marker}{slot}{bold_marker}{slot_text}'


def _get_key_for_best_items_sort(item_info: dict) -> str:
    if item_info.get('EnhancementValue') and item_info.get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME):
        slot = item_info['ItemSubType']
        rarity_num = lookups.RARITY_ORDER_LOOKUP[item_info['Rarity']]
        enhancement_value = int((1000.0 - float(item_info['EnhancementValue'])) * 10)
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        result = f'{enhancement_value}{slot}{rarity_num}{item_name}'
        return result


def _get_pretty_slot(slot: str) -> Tuple[str, bool]:
    """
    Returns: (slot name, is equipment)
    """
    if 'Equipment' in slot:
        return slot.replace('Equipment', ''), True
    else:
        return slot, False










# ---------- Price info ----------

async def get_item_price(item_name: str, ctx: commands.Context = None, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_data = await items_designs_retriever.get_data_dict3()
    item_infos = _get_item_infos_by_name(item_name, items_data)

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        get_best_match = util.is_str_in_list(item_name, ALLOWED_ITEM_NAMES, case_sensitive=False) and len(item_name) < settings.MIN_ENTITY_NAME_LENGTH - 1
        if get_best_match:
            item_infos = [item_infos[0]]

        item_infos = util.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])
        items_details_collection = __create_price_details_collection_from_infos(item_infos, items_data)

        if as_embed:
            custom_footer = '\n'.join([resources.get_resource('MARKET_FAIR_PRICE_NOTE_EMBED'), resources.get_resource('PRICE_NOTE_EMBED')])
            return (await items_details_collection.get_entity_details_as_embed(ctx, custom_footer_text=custom_footer)), True
        else:
            custom_footer = '\n'.join([resources.get_resource('MARKET_FAIR_PRICE_NOTE'), resources.get_resource('PRICE_NOTE')])
            return (await items_details_collection.get_entity_details_as_text()), True










# ---------- Ingredients info ----------

async def get_ingredients_for_item(item_name: str, ctx: commands.Context = None, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_data = await items_designs_retriever.get_data_dict3()
    item_infos = _get_item_infos_by_name(item_name, items_data, return_best_match=True)

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        ingredients_details_collection = __create_ingredients_details_collection_from_infos([item_infos[0]], items_data)
        if as_embed:
            return (await ingredients_details_collection.get_entity_details_as_embed(ctx, custom_footer_text=resources.get_resource('PRICE_NOTE_EMBED'))), True
        else:
            return (await ingredients_details_collection.get_entity_details_as_text(custom_footer_text=resources.get_resource('PRICE_NOTE'))), True

        item_info = item_infos[0]
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        ingredients_tree = _parse_ingredients_tree(item_info['Ingredients'], items_data)
        ingredients_dicts = _flatten_ingredients_tree(ingredients_tree)
        if as_embed:
            return (await _get_item_ingredients_as_embed(item_info, ingredients_dicts, items_data, ctx)), True
        else:
            return _get_item_ingredients_as_text(item_info, ingredients_dicts, items_data), True


async def _get_item_ingredients_as_embed(item_info, ingredients_dicts, item_design_data, ctx) -> List[discord.Embed]:
    item_name = item_info.get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
    ingredients_dicts = [d for d in ingredients_dicts if d]

    lines = []
    if ingredients_dicts:
        for ingredients_dict in ingredients_dicts:
            current_level_lines = []
            current_level_costs = 0
            for ingredient_item_id, ingredient_amount in ingredients_dict.items():
                ingredient_item_info = item_design_data[ingredient_item_id]
                ingredient_name = ingredient_item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
                ingredient_price = int(ingredient_item_info['MarketPrice'])
                price_sum = ingredient_price * ingredient_amount
                current_level_costs += price_sum
                current_level_lines.append(f'> {ingredient_amount} x {ingredient_name} ({ingredient_price} bux ea): {price_sum} bux')
            lines.extend(current_level_lines)
            lines.append(f'Crafting costs: {current_level_costs} bux')
            lines.append(settings.EMPTY_LINE)
    else:
        lines.append('This item can\'t be crafted')

    title = f'Ingredients for: {item_name}'
    description = '\n'.join(lines)
    thumbnail_url = await sprites.get_download_sprite_link(item_info.get('ImageSpriteId'))
    colour = util.get_bot_member_colour(ctx.bot, ctx.guild)
    result = util.create_embed(title, description=description, colour=colour, thumbnail_url=thumbnail_url, footer=resources.get_resource('PRICE_NOTE_EMBED'))
    return [result]


def _get_item_ingredients_as_text(item_info, ingredients_dicts, item_design_data):
    item_name = item_info.get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
    lines = [f'**Ingredients for {item_name}**']
    ingredients_dicts = [d for d in ingredients_dicts if d]

    if ingredients_dicts:
        for ingredients_dict in ingredients_dicts:
            current_level_lines = []
            current_level_costs = 0
            for ingredient_item_id, ingredient_amount in ingredients_dict.items():
                ingredient_item_info = item_design_data[ingredient_item_id]
                ingredient_name = ingredient_item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
                ingredient_price = int(ingredient_item_info['MarketPrice'])
                price_sum = ingredient_price * ingredient_amount
                current_level_costs += price_sum
                current_level_lines.append(f'> {ingredient_amount} x {ingredient_name} ({ingredient_price} bux ea): {price_sum} bux')
            lines.extend(current_level_lines)
            lines.append(f'Crafting costs: {current_level_costs} bux')
            lines.append(settings.EMPTY_LINE)

        lines.append(resources.get_resource('PRICE_NOTE'))
    else:
        lines.append('This item can\'t be crafted')

    return lines


def _parse_ingredients_tree(ingredients_str: str, item_design_data: dict, parent_amount: int = 1) -> List[Tuple[str, str, list]]:
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
        # Filter out void particles and fragments
        if 'void particle' not in item_name and ' fragment' not in item_name:
            combined_amount = item_amount * parent_amount
            item_ingredients = _parse_ingredients_tree(item_info['Ingredients'], item_design_data, combined_amount)
            result.append((item_id, combined_amount, item_ingredients))

    return result


def _get_ingredients_dict(ingredients: str) -> dict:
    result = {}
    if entity.has_value(ingredients):
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

async def get_item_upgrades_from_name(item_name: str, ctx: commands.Context, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_data = await items_designs_retriever.get_data_dict3()
    item_ids = _get_item_design_ids_from_name(item_name, items_data)

    if not item_ids:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        item_infos = []
        for item_id in item_ids:
            item_infos.extend(_get_upgrades_for(item_id, items_data))
        item_infos = list(dict([(item_info[ITEM_DESIGN_KEY_NAME], item_info) for item_info in item_infos]).values())
        item_infos = util.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])
        upgrade_details_collection = __create_upgrade_details_collection_from_infos(item_infos, items_data)

        if as_embed:
            custom_title = f'{len(item_infos)} crafting recipes requiring: {item_name}'
            return (await upgrade_details_collection.get_entity_details_as_embed(ctx, custom_title=custom_title)), True
        else:
            custom_title = f'{len(item_infos)} crafting recipes requiring: **{item_name}**'
            return (await upgrade_details_collection.get_entity_details_as_text(custom_title=custom_title, big_set_details_type=entity.EntityDetailsType.LONG)), True


def _get_upgrades_for(item_id: str, item_design_data: dict) -> list:
    # iterate through item_design_data and return every item_design containing the item id in question in property 'Ingredients'
    result = []
    for item_info in item_design_data.values():
        ingredient_item_ids = list(_get_ingredients_dict(item_info['Ingredients']).keys())
        if item_id in ingredient_item_ids:
            result.append(item_info)
    return result


def _get_item_upgrades_as_embed(item_name: str, item_infos: dict, item_design_data: dict, ctx: commands.Context) -> List[discord.Embed]:
    if item_infos:
        description = None
        fields = []
        for item_info in item_infos:
            field_title = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            field_content = []
            ingredients = _get_ingredients_dict(item_info['Ingredients'])
            for item_id, amount in ingredients.items():
                ingredient_info = item_design_data[item_id]
                field_content.append(f'{ingredient_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]} x{amount}')
            fields.append((field_title, field_content, True))
    else:
        description = f'No item with the a name like {item_name} can be upgraded.'
        fields = None

    title = f'Crafting recipes requiring: {item_name}'
    colour = util.get_bot_member_colour(ctx.bot, ctx.guild)
    result = util.create_embed(title, description=description, colour=colour, fields=fields)
    return [result]


def _get_item_upgrades_as_text(item_name: str, item_infos: dict, item_design_data) -> list:
    lines = [f'Crafting recipes requiring: {item_name}']
    if item_infos:
        for item_info in item_infos:
            lines.append(f'**{item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]}**')
            ingredients = _get_ingredients_dict(item_info['Ingredients'])
            for item_id, amount in ingredients.items():
                ingredient_info = item_design_data[item_id]
                lines.append(f'> {ingredient_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]} x{amount}')
    else:
        lines.append(f'No item with the a name like {item_name} can be upgraded.')

    return lines










# ---------- Create EntityDetails ----------

def __create_base_design_data_from_info(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(item_info, __properties['title'], __properties['description'], __properties['base'], __properties['embed_settings'], items_data, trainings_data)


def __create_base_details_list_from_infos(items_designs_infos: List[entity.EntityInfo], items_data: entity.EntitiesData, trainings_data: entity.EntitiesData) -> List[entity.EntityDetails]:
    return [__create_base_design_data_from_info(item_info, items_data, trainings_data) for item_info in items_designs_infos]


def __create_base_details_collection_from_infos(items_designs_infos: List[entity.EntityInfo], items_data: entity.EntitiesData, trainings_data: entity.EntitiesData) -> entity.EntityDetailsCollection:
    base_details = __create_base_details_list_from_infos(items_designs_infos, items_data, trainings_data)
    result = entity.EntityDetailsCollection(base_details, big_set_threshold=2)
    return result


def __create_best_design_data_from_info(item_info: entity.EntityInfo, items_data: entity.EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(item_info, __properties['title'], __properties['description'], __properties['best'], __properties['embed_settings'], items_data, prefix='> ')


def __create_best_details_list_from_infos(items_designs_infos: List[entity.EntityInfo], items_data: entity.EntitiesData) -> List[entity.EntityDetails]:
    return [__create_best_design_data_from_info(item_info, items_data) for item_info in items_designs_infos]


def __create_best_details_collection_from_details(best_details: List[entity.EntityDetails]) -> entity.EntityDetailsCollection:
    result = entity.EntityDetailsCollection(best_details, big_set_threshold=1)
    return result


def __create_ingredients_design_data_from_info(item_info: entity.EntityInfo, items_data: entity.EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(item_info, __properties['title_ingredients'], entity.NO_PROPERTY, __properties['ingredients'], __properties['embed_settings'], items_data)


def __create_ingredients_details_list_from_infos(items_designs_infos: List[entity.EntityInfo], items_data: entity.EntitiesData) -> List[entity.EntityDetails]:
    return [__create_ingredients_design_data_from_info(item_info, items_data) for item_info in items_designs_infos]


def __create_ingredients_details_collection_from_infos(items_designs_infos: List[entity.EntityInfo], items_data: entity.EntitiesData) -> entity.EntityDetailsCollection:
    price_details = __create_ingredients_details_list_from_infos(items_designs_infos, items_data)
    result = entity.EntityDetailsCollection(price_details, big_set_threshold=0)
    return result


def __create_price_design_data_from_info(item_info: entity.EntityInfo, items_data: entity.EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(item_info, __properties['title'], __properties['description'], __properties['price'], __properties['embed_settings'], items_data)


def __create_price_details_list_from_infos(items_designs_infos: List[entity.EntityInfo], items_data: entity.EntitiesData) -> List[entity.EntityDetails]:
    return [__create_price_design_data_from_info(item_info, items_data) for item_info in items_designs_infos]


def __create_price_details_collection_from_infos(items_designs_infos: List[entity.EntityInfo], items_data: entity.EntitiesData) -> entity.EntityDetailsCollection:
    price_details = __create_price_details_list_from_infos(items_designs_infos, items_data)
    result = entity.EntityDetailsCollection(price_details, big_set_threshold=1)
    return result


def __create_upgrade_design_data_from_info(item_info: entity.EntityInfo, items_data: entity.EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(item_info, __properties['title'], entity.NO_PROPERTY, __properties['upgrade'], __properties['embed_settings'], items_data)


def __create_upgrade_details_list_from_infos(items_designs_infos: List[entity.EntityInfo], items_data: entity.EntitiesData) -> List[entity.EntityDetails]:
    return [__create_upgrade_design_data_from_info(item_info, items_data) for item_info in items_designs_infos]


def __create_upgrade_details_collection_from_infos(items_designs_infos: List[entity.EntityInfo], items_data: entity.EntitiesData) -> entity.EntityDetailsCollection:
    price_details = __create_upgrade_details_list_from_infos(items_designs_infos, items_data)
    result = entity.EntityDetailsCollection(price_details, big_set_threshold=1)
    return result










# ---------- Transformation functions ----------

def __get_all_ingredients(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    ingredients_tree = _parse_ingredients_tree(item_info['Ingredients'], items_data)
    ingredients_dicts = _flatten_ingredients_tree(ingredients_tree)
    ingredients_dicts = [d for d in ingredients_dicts if d]
    lines = []
    if ingredients_dicts:
        for ingredients_dict in ingredients_dicts:
            current_level_lines = []
            current_level_costs = 0
            for ingredient_item_id, ingredient_amount in ingredients_dict.items():
                ingredient_item_info = items_data[ingredient_item_id]
                ingredient_name = ingredient_item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
                ingredient_price = int(ingredient_item_info['MarketPrice'])
                price_sum = ingredient_price * ingredient_amount
                current_level_costs += price_sum
                current_level_lines.append(f'> {ingredient_amount} x {ingredient_name} ({ingredient_price} bux ea): {price_sum} bux')
            lines.extend(current_level_lines)
            lines.append(f'Crafting costs: {current_level_costs} bux')
            lines.append(settings.EMPTY_LINE)
        if lines:
            lines = lines[:-1]
    else:
        lines.append('This item can\'t be crafted')
    return '\n'.join(lines)


def __get_can_sell(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    flags = int(item_info['Flags'])
    if flags & 1 == 0:
        result = CANNOT_BE_SOLD
    else:
        result = None
    return result


def __get_enhancement_value(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    enhancement_value = float(item_info['EnhancementValue'])
    result = f'{enhancement_value:.1f}'
    return result


async def __get_image_url(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    logo_sprite_id = item_info.get('LogoSpriteId')
    image_sprite_id = item_info.get('ImageSpriteId')
    if entity.has_value(logo_sprite_id) and logo_sprite_id != image_sprite_id:
        return await sprites.get_download_sprite_link(logo_sprite_id)
    else:
        return None


def __get_ingredients(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    ingredients = _get_ingredients_dict(item_info.get('Ingredients'))
    result = []
    for item_id, amount in ingredients.items():
        item_name = items_data[item_id].get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
        result.append(f'> {item_name} x{amount}')
    if result:
        return '\n'.join(result)
    else:
        return None


def __get_item_bonus_type_and_value(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    bonus_type = item_info['EnhancementType']
    bonus_value = item_info['EnhancementValue']
    if bonus_type.lower() == 'none':
        result = None
    else:
        result = f'{bonus_type} +{bonus_value}'
    return result


def __get_item_price(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    flags = int(item_info['Flags'])
    if flags & 1 == 0:
        result = CANNOT_BE_SOLD
    else:
        fair_price = item_info['FairPrice']
        market_price = item_info['MarketPrice']
        result = f'{market_price} ({fair_price})'
    return result


def __get_item_slot(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    item_type = item_info['ItemType']
    item_sub_type = item_info['ItemSubType']
    if item_type == 'Equipment' and 'Equipment' in item_sub_type:
        result = item_sub_type.replace('Equipment', '')
    else:
        result = None
    return result


def __get_pretty_market_price(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    flags = int(item_info['Flags'])
    if flags & 1 == 0:
        result = CANNOT_BE_SOLD
    else:
        market_price = item_info['MarketPrice']
        result = f'{market_price} bux'
    return result


def __get_price(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    flags = int(item_info['Flags'])
    if flags & 1 == 0:
        result = None
    else:
        price = kwargs.get('entity_property')
        result = f'{price} bux'
    return result


def __get_title_ingredients(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    value = kwargs.get('entity_property')
    if value:
        result = f'Ingredients for: {value}'
    else:
        result = None
    return result


async def __get_training_mini_details(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    for_embed = kwargs.get('for_embed', False)
    training_design_id = item_info.get(training.TRAINING_DESIGN_KEY_NAME)
    if entity.has_value(training_design_id):
        training_design_details: entity.EntityDetails = await training.get_training_details_from_id(training_design_id, trainings_data, items_data)
        result = await training_design_details.get_details_as_text(entity.EntityDetailsType.MINI, for_embed=for_embed)
        return ''.join(result)
    else:
        return None


def __get_type(item_info: entity.EntityInfo, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData, **kwargs) -> str:
    item_sub_type = item_info.get('ItemSubType')
    if entity.has_value(item_sub_type) and 'Equipment' not in item_sub_type:
        result = item_sub_type.replace('Equipment', '')
    else:
        item_type = item_info.get('ItemType')
        if entity.has_value(item_type):
            result = item_type
        else:
            result = None
    return result










# ---------- Helper functions ----------


def filter_items_details_for_equipment(items_details: List[entity.EntityDetails]) -> List[entity.EntityDetails]:
    result = [item_details for item_details in items_details if __get_item_slot(item_details.entity_info, None, None) is not None]
    if result:
        stat = items_details[0].entity_info.get('EnhancementType')
        slot = __get_item_slot(items_details[0].entity_info, None, None)
        if all(item_details.entity_info.get('EnhancementType') == stat and __get_item_slot(item_details.entity_info, None, None) == slot for item_details in items_details):
            return [items_details[0]]
    return result


def fix_slot_and_stat(slot: str, stat: str) -> Tuple[str, str]:
    if not slot and not stat:
        pass
    elif slot and not stat:
        stat = slot.lower()
        slot = None
    else:
        slot = slot.lower()
        stat = stat.lower()
        temp_stat = f'{slot} {stat}'.strip()
        if temp_stat in lookups.STAT_TYPES_LOOKUP:
            slot = None
            stat = temp_stat
        else:
            if slot in lookups.STAT_TYPES_LOOKUP and stat in lookups.EQUIPMENT_SLOTS_LOOKUP:
                slot, stat = (stat, slot)
            elif ' ' in stat:
                split_stat = stat.split(' ')
                temp_slot = f'{slot} {split_stat[0]}'
                temp_stat = ' '.join(split_stat[1:])
                if temp_slot in lookups.STAT_TYPES_LOOKUP and temp_stat in lookups.EQUIPMENT_SLOTS_LOOKUP:
                    slot, stat = temp_stat, temp_slot
    return slot, stat


def get_item_details_by_id(item_design_id: str, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData) -> entity.EntityDetails:
    if item_design_id and item_design_id in items_data.keys():
        return __create_base_design_data_from_info(items_data[item_design_id], items_data, trainings_data)
    else:
        return None


async def get_items_details_by_name(item_name: str, sorted: bool = True) -> List[entity.EntityDetails]:
    items_data = await items_designs_retriever.get_data_dict3()
    trainings_data = await training.trainings_designs_retriever.get_data_dict3()
    item_infos = _get_item_infos_by_name(item_name, items_data)
    if sorted:
        item_infos = util.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])
    result = __create_base_details_list_from_infos(item_infos, items_data, trainings_data)
    return result


def get_item_details_by_training_id(training_id: str, items_data: entity.EntitiesData, trainings_data: entity.EntitiesData) -> List[entity.EntityDetails]:
    items_designs_ids = core.get_ids_from_property_value(items_data, training.TRAINING_DESIGN_KEY_NAME, training_id, fix_data_delegate=_fix_item_name, match_exact=True)
    result = [get_item_details_by_id(item_design_id, items_data, trainings_data) for item_design_id in items_designs_ids]
    return result


async def get_item_search_details(item_details: entity.EntityDetails) -> List[str]:
    result = await item_details.get_details_as_text(entity.EntityDetailsType.MINI)
    return ''.join(result)


def __get_parents(item_info: entity.EntityInfo, items_data: entity.EntitiesData) -> List[entity.EntityInfo]:
    item_design_id = item_info.get(ITEM_DESIGN_KEY_NAME)
    root_item_design_id = item_info.get('RootItemDesignId')
    result = []
    if entity.has_value(root_item_design_id) and item_design_id != root_item_design_id:
        parent_info = items_data.get(root_item_design_id)
        if parent_info:
            result = __get_parents(parent_info, items_data)
            result.append(parent_info)
    return result


def get_slot_and_stat_type(item_details: entity.EntityDetails) -> Tuple[str, str]:
    slot = __get_item_slot(item_details.entity_info, None, None)
    stat = item_details.entity_info['EnhancementType']
    return slot, stat


def _fix_item_name(item_name) -> str:
    result = item_name.lower()
    result = re.sub('[^a-z0-9]', '', result)
    result = re.sub("(darkmatterrifle|dmr)(mark|mk)?(ii|2)", "dmrmarkii", result)
    result = result.replace('anonmask', 'anonymousmask')
    result = result.replace('armour', 'armor')
    result = result.replace('bunny', 'rabbit')
    result = result.replace('golden', 'gold')
    return result


def _get_item_design_ids_from_name(item_name: str, items_data: dict) -> list:
    results = core.get_ids_from_property_value(items_data, ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, item_name, fix_data_delegate=_fix_item_name)
    return results


def _get_item_infos_by_name(item_name: str, items_data: dict, return_best_match: bool = False) -> list:
    item_design_ids = _get_item_design_ids_from_name(item_name, items_data)
    result = [items_data[item_design_id] for item_design_id in item_design_ids if item_design_id in items_data.keys()]

    if result:
        get_best_match = return_best_match or util.is_str_in_list(item_name, ALLOWED_ITEM_NAMES, case_sensitive=False) and len(item_name) < settings.MIN_ENTITY_NAME_LENGTH - 1
        if get_best_match:
            result = [result[0]]

    return result


def _get_stat_filter(stat: str) -> str:
    stat = stat.lower()
    return lookups.STAT_TYPES_LOOKUP[stat]


def _get_slot_filter(slot: str, any_slot: bool) -> List[str]:
    if any_slot:
        result = list(lookups.EQUIPMENT_SLOTS_LOOKUP.values())
    else:
        slot = slot.lower()
        result = [lookups.EQUIPMENT_SLOTS_LOOKUP[slot]]
    return result


def __get_allowed_item_names(items_data: dict, not_allowed_item_names: List[str]):
    result = []
    for item_design_data in items_data.values():
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
                                if item_name_part not in not_allowed_item_names:
                                    result.append(item_name_part)
    if result:
        result = list(set(result))
    return result










# ---------- Initilization ----------

NOT_ALLOWED_ITEM_NAMES: List[str] = [
    'AI',
    'I',
    'II',
    'III',
    'IV',
    'V',
    'VI'
]
ALLOWED_ITEM_NAMES: List[str] = []
items_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    ITEM_DESIGN_BASE_PATH,
    ITEM_DESIGN_KEY_NAME,
    ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'ItemsDesigns',
    fix_data_delegate=_fix_item_name
)
__properties: Dict[str, Union[entity.EntityDetailProperty, entity.EntityDetailPropertyCollection, entity.EntityDetailPropertyListCollection]] = {
    'title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
    ),
    'title_ingredients': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, transform_function=__get_title_ingredients, text_only=True),
        property_embed=entity.NO_PROPERTY
    ),
    'description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, entity_property_name='ItemDesignDescription'),
        property_short=entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='Rarity')
    ),
    'base': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Rarity', True, entity_property_name='Rarity'),
            entity.EntityDetailProperty('Type', True, transform_function=__get_type),
            entity.EntityDetailProperty('Bonus', True, transform_function=__get_item_bonus_type_and_value),
            entity.EntityDetailProperty('Slot', True, transform_function=__get_item_slot),
            entity.EntityDetailProperty('Stat gain chances', True, transform_function=__get_training_mini_details, embed_only=True, for_embed=True),
            entity.EntityDetailProperty('Stat gain chances', True, transform_function=__get_training_mini_details, text_only=True),
            entity.EntityDetailProperty('Market price', True, transform_function=__get_pretty_market_price)
        ],
        properties_short=[
            entity.EntityDetailProperty('Rarity', False, entity_property_name='Rarity', embed_only=True),
            entity.EntityDetailProperty('Bonus', False, transform_function=__get_item_bonus_type_and_value),
            entity.EntityDetailProperty('Slot', False, transform_function=__get_item_slot),
            entity.EntityDetailProperty('Can sell', False, transform_function=__get_can_sell, text_only=True),
            entity.EntityDetailProperty('Market price', False, transform_function=__get_pretty_market_price, embed_only=True)
        ],
        properties_mini=[]
    ),
    'best': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Rarity', False, entity_property_name='Rarity', embed_only=True),
            entity.EntityDetailProperty('Enhancement value', False, transform_function=__get_enhancement_value),
            entity.EntityDetailProperty('Market price', False, transform_function=__get_pretty_market_price)
        ]
    ),
    'ingredients': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty(entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, transform_function=__get_title_ingredients), False, transform_function=__get_all_ingredients)
        ]
    ),
    'price': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Rarity', False, entity_property_name='Rarity', embed_only=True),
            entity.EntityDetailProperty('Market price', True, entity_property_name='MarketPrice', transform_function=__get_price),
            entity.EntityDetailProperty('Savy\'s Fair price', True, entity_property_name='FairPrice', transform_function=__get_price),
            entity.EntityDetailProperty('Can sell', False, transform_function=__get_can_sell)
        ],
        properties_short=[
            entity.EntityDetailProperty('Rarity', False, entity_property_name='Rarity', embed_only=True),
            entity.EntityDetailProperty('Market price (Fair price)', False, transform_function=__get_item_price)
        ]
    ),
    'upgrade': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Ingredients', False, transform_function=__get_ingredients)
        ]
    ),
    'embed_settings': {
        'image_url': entity.EntityDetailProperty('image_url', False, transform_function=__get_image_url),
        'thumbnail_url': entity.EntityDetailProperty('thumbnail_url', False, entity_property_name='ImageSpriteId', transform_function=sprites.get_download_sprite_link_by_property)
    }
}





async def init():
    global ALLOWED_ITEM_NAMES
    items_data = await items_designs_retriever.get_data_dict3()
    ALLOWED_ITEM_NAMES = sorted(__get_allowed_item_names(items_data, NOT_ALLOWED_ITEM_NAMES))
