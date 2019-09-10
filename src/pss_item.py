#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re

from cache import PssCache
import pss_core as core
import utility as util


# ---------- Constants ----------

ITEM_DESIGN_BASE_PATH = 'ItemService/ListItemDesigns2?languageKey=en'
ITEM_DESIGN_KEY_NAME = 'ItemDesignId'
ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ItemDesignName'



# ---------- Initilization ----------

__item_designs_cache = PssCache(
    ITEM_DESIGN_BASE_PATH,
    'ItemDesigns',
    ITEM_DESIGN_KEY_NAME)



# ---------- Item info ----------

def get_item_details(item_name, as_embed=False):
    item_infos = _get_item_infos(item_name)

    if not item_infos:
        return f'Could not find an item named **{item_name}**.', False
    else:
        if as_embed:
            return _get_item_info_as_embed(item_infos), True
        else:
            return _get_item_info_as_text(item_infos), True


def _get_item_infos(item_name, item_design_data=None, return_on_first=False):
    if item_design_data is None:
        item_design_data = __item_designs_cache.get_data_dict3()

    item_design_ids = _get_item_design_ids_from_name(item_name, item_data=item_design_data, return_on_first=return_on_first)
    result = [item_design_data[item_design_id] for item_design_id in item_design_ids if item_design_id in item_design_data.keys()]

    return result


def _get_item_design_ids_from_name(item_name, item_data=None, return_on_first=False):
    if item_data is None:
        item_data = __item_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(item_data, ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, item_name, fix_data_delegate=_fix_item_name, return_on_first=return_on_first)
    return results


def _get_item_info_as_embed(item_info):
    return ''


def _get_item_info_as_text(item_infos):
    lines = ['**Item stats**']

    for item_info in item_infos:
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
            bonus_txt = f'{bonus_type} {bonus_value}'

        lines.append(f'{item_name} ({rarity}) - {bonus_txt}{slot_txt}')

    return '\n'.join(lines)


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
    item_infos = _get_item_infos(item_name)

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
    lines.append(f'__**Item prices matching \'{item_name}\'**__')
    lines.append('')
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

    return '\n'.join(lines)





# ---------- Ingredients info ----------

def get_ingredients_for_item(item_name: str, as_embed: bool = False):
    util.dbg_prnt(f'+ get_ingredients_for_item({item_name}, {as_embed})')
    if not item_name:
        util.dbg_prnt(f'[get_ingredients_for_item] parameter \'item_name\' is either empty or None.')
        return [f'You must specify an item name!'], False
        
    item_design_data = __item_designs_cache.get_data_dict3()
    util.dbg_prnt(f'[get_ingredients_for_item] Retrieved item_design_data')
    item_infos = _get_item_infos(item_name, item_design_data, return_on_first=True)
    util.dbg_prnt(f'[get_ingredients_for_item] Retrieved item infos: {len(item_infos)} entries')

    if not item_infos:
        return [f'Could not find an item named **{item_name}**.'], False
    else:
        item_info = item_infos[0]
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        util.dbg_prnt(f'[get_ingredients_for_item] Retrieved item name: {item_name}')
        ingredients_tree = _parse_ingredients_tree(item_info['Ingredients'], item_design_data)
        util.dbg_prnt(f'[get_ingredients_for_item] Created ingredients tree')
        ingredients_dicts = _flatten_ingredients_tree(ingredients_tree)
        util.dbg_prnt(f'[get_ingredients_for_item] Parsed ingredients tree to list of dicts')
        if as_embed:
            return _get_item_ingredients_as_embed(item_name, ingredients_dicts, item_design_data), True
        else:
            return _get_item_ingredients_as_text(item_name, ingredients_dicts, item_design_data), True


def _get_item_ingredients_as_embed(item_name, ingredients_dicts, item_design_data):
    return ''


def _get_item_ingredients_as_text(item_name, ingredients_dicts, item_design_data):
    lines = [f'**Ingredients for {item_name}**']
    lines.append('')
    
    for ingredients_dict in ingredients_dicts:
        current_level_lines = []
        for item_id, ingredients_amount in ingredients_dict:
            item_info = item_design_data[item_id]
            item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            item_price = item_info['Price']
            combined_price = item_price * item_amount
            current_level_lines.append(f'{item_amount} x {item_name} ({item_price} bux ea): {combined_price} bux')
        lines.extend(current_level_lines)
        lines.append('')
    
    lines.append('Note: bux prices listed here may not always be accurate due to transfers between alts/friends or other reasons')
    
    return lines


def _parse_ingredients_tree(ingredients_str: str, item_design_data: dict, parent_amount: int = 1) -> list: # a nested list, basically a tree
    """returns a tree structure: [(item_id, item_amount, item_ingredients[])]"""
    if not ingredients_str:
        return []

    # Ingredients format is: [<id>x<amount>][|<id>x<amount>]*
    ingredients_tuples = dict([split_str.split('x') for split_str in ingredients_str.split('|')])
    result = []
    for item_id, item_amount in ingredients_tuples.keys():
        item_info = item_design_data[item_id]
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME].lower()
        # Filter out void particles and scrap
        if 'void particle' not in item_name and ' fragment' not in item_name:
            combined_amount = item_amount * parent_amount
            item_ingredients = _parse_ingredients_tree(item_info['Ingredients'], item_design_data, combined_amount)
            result.append((item_id, combined_amount, item_ingredients))
    # Result looks like this:
    #   (item 1, amount 1,
    #    - (item 1.1, amount 1.1 * amount 1, )
    #      ...
    #    - (item 1.n, amount 1.n * amount 1, 
    #       - (item 1.n.1, amount 1.n.1 * amount 1.n * amount 1, )
    #         ...
    #       - (item 1.n.1, amount 1.n.1 * amount 1.n * amount 1, )))
    #    item 2
    #     - item 2.1
    #     - item 2.n
    
    return result


def _flatten_ingredients_tree(ingredients_tree: list) -> list: # list of dicts
    ingredients = {}
    ingredients_without_subs = []
    sub_ingredients = []
    
    for item_id, item_amount, item_ingredients in ingredients_tree:
        # add all entries of current level to ingredients
        if item_id in ingredients.keys():
            ingredients[item_id] += item_amount
        else:
            ingredients[item_id] = item_amount
        
        if item_ingredients:
            # add all entries of sublevel to sub_ingredients 
            sub_ingredients.extend(item_ingredients)
        else:
            # add entries of current level without ingredients to ingredients_without_subs
            ingredients_without_subs.append((item_id, item_amount, item_ingredients))
    
    result = [ingredients]
    
    if len(ingredients_without_subs) != len(ingredients_tree):
        sub_ingredients.extend(ingredients_without_subs)
        flattened_subs = _flatten_ingredients_tree(sub_ingredients)
        result.extend(flattened_subs)
    
    return result
