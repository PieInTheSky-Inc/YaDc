#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from cache import PssCache
import pss_assert
import pss_core as core
import pss_lookups as lookups


# ---------- Constants ----------

ROOM_DESIGN_BASE_PATH = 'RoomService/ListRoomDesigns2?languageKey=en'
ROOM_DESIGN_KEY_NAME = 'RoomDesignId'
ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'RoomName'
ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2 = 'RoomShortName'





# ---------- Initilization ----------

__room_designs_cache = PssCache(
    ROOM_DESIGN_BASE_PATH,
    'RoomDesigns',
    ROOM_DESIGN_KEY_NAME)


def __get_allowed_room_short_names():
    result = []
    room_designs_data = __room_designs_cache.get_data_dict3()
    for room_design_data in room_designs_data.values():
        if room_design_data[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2]:
            room_short_name = room_design_data[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2].split(':')[0]
            if room_short_name not in result:
                result.append(room_short_name)
    return result


__allowed_room_names = sorted(__get_allowed_room_short_names())






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
    for flag in lookups.GRID_TYPE_MASK_LOOKUP.keys():
        if (flags & flag) != 0:
            result.append(lookups.GRID_TYPE_MASK_LOOKUP[flag])
    if result:
        return ', '.join(result)
    else:
        return ''


def _get_parents(room_info: dict, room_designs_data: dict) -> list:
    parent_room_design_id = room_info['UpgradeFromRoomDesignId']
    if parent_room_design_id == '0':
        parent_room_design_id = None

    if parent_room_design_id is not None:
        parent_info = room_designs_data[parent_room_design_id]
        result = _get_parents(parent_info, room_designs_data)
        result.append(parent_info)
        return result
    else:
        return []





# ---------- Room info ----------

def get_room_details_from_name(room_name: str, as_embed: bool = False):
    pss_assert.valid_entity_name(room_name, allowed_values=__allowed_room_names)

    room_designs_data = __room_designs_cache.get_data_dict3()
    room_infos = _get_room_infos(room_name, room_designs_data=room_designs_data)

    if not room_infos:
        return [f'Could not find a room named **{room_name}**.'], False
    else:
        if as_embed:
            return _get_room_info_as_embed(room_name, room_infos, room_designs_data), True
        else:
            return _get_room_info_as_text(room_name, room_infos, room_designs_data), True


def _get_room_infos(room_name: str, room_designs_data: dict = None, return_on_first: bool = False):
    if room_designs_data is None:
        room_designs_data = __room_designs_cache.get_data_dict3()

    room_design_ids = _get_room_design_ids_from_name(room_name, room_designs_data=room_designs_data, return_on_first=return_on_first)
    if not room_design_ids:
        room_design_ids = _get_room_design_ids_from_room_shortname(room_name, room_designs_data=room_designs_data, return_on_first=return_on_first)

    result = [room_designs_data[room_design_id] for room_design_id in room_design_ids if room_design_id in room_designs_data.keys()]
    return result


def _get_room_design_ids_from_name(room_name: str, room_designs_data: dict = None, return_on_first: bool = False):
    if room_designs_data is None:
        room_designs_data = __room_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(room_designs_data, ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME, room_name, return_on_first=return_on_first)
    return results


def _get_room_design_ids_from_room_shortname(room_short_name: str, room_designs_data: dict = None, return_on_first: bool = False):
    if room_designs_data is None:
        room_designs_data = __room_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(room_designs_data, 'RoomShortName', room_short_name, return_on_first=return_on_first)
    return results


def _get_room_info_as_embed(room_name: str, room_infos: dict, room_designs_data: dict):
    return ''


def _get_room_info_as_text(room_name: str, room_infos: dict, room_designs_data: dict):
    lines = [f'**Room stats for \'{room_name}\'**']
    room_infos = sorted(room_infos, key=lambda room_info: (
        _get_key_for_room_sort(room_info, room_designs_data)
    ))
    room_infos_count = len(room_infos)
    big_set = room_infos_count > 3

    for i, room_info in enumerate(room_infos):
        if big_set:
            lines.extend(get_room_details_short_from_data_as_text(room_info))
        else:
            lines.extend(get_room_details_from_data_as_text(room_info))
            if i < room_infos_count - 1:
                lines.append(core.EMPTY_LINE)

    return lines


def _get_key_for_room_sort(room_info: dict, room_designs_data: dict) -> str:
    result = ''
    parent_infos = _get_parents(room_info, room_designs_data)
    if parent_infos:
        for parent_info in parent_infos:
            result += parent_info[ROOM_DESIGN_KEY_NAME].zfill(4)
    result += room_info[ROOM_DESIGN_KEY_NAME].zfill(4)
    return result


if __name__ == '__main__':
    result = get_room_details_from_name('visiri')
    result = get_room_details_from_name('VS')