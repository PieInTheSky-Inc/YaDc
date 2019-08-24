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

def get_item_info(item_name, as_embed=False):
    item_infos = _get_item_infos(item_name)

    if not item_infos:
        return f'Could not find an item named **{item_name}**.', False
    else:
        if as_embed:
            return _get_item_info_as_embed(item_name, item_infos), True
        else:
            return _get_item_info_as_text(item_name, item_infos), True


def _get_item_infos(item_name):
    item_design_data = __item_designs_cache.get_data_dict3()
    item_design_ids = _get_item_design_ids_from_name(item_name, item_design_data)
    result = [item_design_data[item_design_id] for item_design_id in item_design_ids if item_design_id in item_design_data.keys()]

    return result


def _get_item_design_ids_from_name(item_name, item_data=None):
    if item_data is None:
        item_data = __item_designs_cache.get_data_dict3()

    # There's a bug somewhere here that prevents stuff from being printed

    results = core.get_ids_from_property_value(item_data, ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, item_name, fix_data_delegate=_fix_item_name, return_on_first=False)
    return results


def _get_item_info_as_embed(item_name, item_info):
    return ''


def _get_item_info_as_text(item_name, item_infos):
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