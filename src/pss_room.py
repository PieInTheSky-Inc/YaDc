#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from cache import PssCache
import pss_core as core
import pss_lookups as lookups


# ---------- Constants ----------

ROOM_DESIGN_BASE_PATH = 'RoomService/ListRoomDesigns2?languageKey=en'
ROOM_DESIGN_KEY_NAME = 'RoomDesignId'
ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'RoomName'



# ---------- Initilization ----------

__room_designs_cache = PssCache(
    ROOM_DESIGN_BASE_PATH,
    'RoomDesigns',
    ROOM_DESIGN_KEY_NAME)





# ---------- Helper functions ----------


def get_room_details_from_id_as_text(room_id: str, room_designs_data: dict = None) -> list:
    if not room_designs_data:
        room_designs_data = __room_designs_cache.get_data_dict3()

    room_info = room_designs_data[room_id]
    return get_room_details_from_data_as_text(room_info)


def get_room_details_from_data_as_text(room_info: dict) -> list:
    room_name, room_lvl = room_info[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME].split(' Lv')
    room_description = room_info['RoomDescription']
    room_flags = int(room_info['Flags'])
    room_consumes_power = (room_flags & 1) > 0
    #room_is_weapon = (room_flags & 2) > 0
    #room_is_manufactoring = (room_flags & 4) > 0
    room_type = room_info['RoomType']
    room_rows = room_info['Rows']
    room_columns = room_info['Columns']
    room_size = f'{room_columns}x{room_rows}'
    room_grid_type_flags = int(room_info['SupportedGridTypes'])
    room_enhancement_type = room_info['EnhancementType']
    max_power_consumed = room_info['MaxSystemPower']

    result = [f'**{room_name}** (lvl {room_lvl})']
    result.append(room_description)
    result.append(f'Type: {room_type}')
    result.append(f'Size (WxH): {room_size}')
    if room_consumes_power:
        result.append(f'Max power consumed: {max_power_consumed}')
    if room_enhancement_type != 'None':
        result.append(f'Enhanced by: {room_enhancement_type} stat')
    result.append(f'Allowed grid types: {_convert_room_grid_type_flags(room_grid_type_flags)}')
    return result


def get_room_details_short_from_id_as_text(room_id: str, room_designs_data: dict = None) -> list:
    if not room_designs_data:
        room_designs_data = __room_designs_cache.get_data_dict3()

    room_info = room_designs_data[room_id]
    return get_room_details_short_from_data_as_text(room_info)


def get_room_details_short_from_data_as_text(room_info: dict) -> list:
    room_name = room_info[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    room_type = room_info['RoomType']
    room_enhancement_type = room_info['EnhancementType']
    return [f'{room_name} (Type: {room_type}, Enhanced by: {room_enhancement_type})']


def _convert_room_grid_type_flags(flags: int) -> str:
    result = []
    for flag in lookups.SALE_ITEM_MASK_LOOKUP.keys():
        if (flags & flag) != 0:
            result.append(lookups.SALE_ITEM_MASK_LOOKUP[flag])
    if result:
        return ', '.join(result)
    else:
        return ''





# ---------- Room info ----------