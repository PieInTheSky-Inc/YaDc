#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os

from cache import PssCache
import pss_assert
import pss_core as core
import pss_item as item
import pss_lookups as lookups
import settings
import utility as util


# ---------- Transformation functions ----------

def _convert_room_flags(flags: str) -> str:
    if flags:
        result = []
        flags = int(flags)
        if result:
            return ', '.join(result)
        else:
            return ''
    else:
        return ''


def _convert_room_grid_type_flags(flags: str) -> str:
    result = []
    flags = int(flags)
    for flag in lookups.GRID_TYPE_MASK_LOOKUP.keys():
        if (flags & flag) != 0:
            result.append(lookups.GRID_TYPE_MASK_LOOKUP[flag])
    if result:
        return ', '.join(result)
    else:
        return ''


def _get_build_cost(price_string: str) -> str:
    if price_string:
        resource_type, amount = price_string.split(':')
        cost = util.get_reduced_number_compact(amount)
        currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[resource_type.lower()]
        result = f'{cost} {currency_emoji}'
        return result
    else:
        return ''


def _get_build_requirement(requirement_string: str) -> str:
    if requirement_string:
        requirement_string = requirement_string.lower()
        required_type, required_id = requirement_string.split(':')

        if 'x' in required_id:
            required_id, required_amount = required_id.split('x')
        else:
            required_amount = '1'

        if required_type == 'item':
            item_info = item.get_item_info_from_id(required_id)
            result = f'{required_amount}x {item_info[item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]}'
            return result
        else:
            return requirement_string
    else:
        return ''


def _get_build_time(construction_time: str) -> str:
    if construction_time and construction_time != '0':
        construction_time = int(construction_time)
        result = util.get_formatted_duration(construction_time, include_relative_indicator=False)
        return result
    else:
        return ''


def _get_capacity_per_tick(capacity: str, room_type: str) -> str:
    if capacity:
        cap_per_tick = util.convert_ticks_to_seconds(int(capacity))
        result = f'{util.format_up_to_decimals(cap_per_tick, 3)}{CAPACITY_PER_TICK_UNITS[room_type]}'
        return result
    else:
        return ''


def _get_construction_type(construction_type: str) -> str:
    if construction_type:
        lower = construction_type.lower()
        if lower in lookups.CURRENCY_EMOJI_LOOKUP.keys():
            return lookups.CURRENCY_EMOJI_LOOKUP[lower]
        else:
            return construction_type
    else:
        return ''


def _get_cooldown(cooldown: str) -> str:
    if cooldown:
        cooldown_seconds = util.convert_ticks_to_seconds(int(cooldown))
        result = f'{util.format_up_to_decimals(cooldown_seconds, 3)}s'
        return result
    else:
        return ''


def _get_description(description: str) -> str:
    if description:
        result = f'_{_get_value(description)}_'
        return result
    else:
        return ''


def _get_dmg_for_dmg_type(dmg: str, reload_time: str, max_power: str, volley: str, volley_delay: str, print_percent: bool) -> str:
    """Returns base dps and dps per power"""
    if dmg:
        dmg = float(dmg)
        reload_time = int(reload_time)
        reload_seconds = util.convert_ticks_to_seconds(reload_time)
        max_power = int(max_power)
        volley = int(volley)
        volley_delay = int(volley_delay)
        volley_duration_seconds = util.convert_ticks_to_seconds((volley - 1) * volley_delay)
        reload_seconds += volley_duration_seconds
        full_volley_dmg = dmg * float(volley)
        dps = full_volley_dmg / reload_seconds
        dps_per_power = dps / max_power
        if print_percent:
            percent = '%'
        else:
            percent = ''
        if volley > 1:
            single_volley_dmg = f'per shot: {util.format_up_to_decimals(dmg, 2)}, '
        else:
            single_volley_dmg = ''
        full_volley_dmg = util.format_up_to_decimals(full_volley_dmg, 2)
        dps = util.format_up_to_decimals(dps, 3)
        dps_per_power = util.format_up_to_decimals(dps_per_power, 3)
        result = f'{full_volley_dmg}{percent} ({single_volley_dmg}dps: {dps}{percent}, per power: {dps_per_power}{percent})'
        return result
    else:
        return ''


def _get_innate_armor(default_defense_bonus: str) -> str:
    if default_defense_bonus and default_defense_bonus != '0':
        reduction = _calculate_innate_armor_percent(int(default_defense_bonus))
        result = f'{default_defense_bonus} ({util.format_up_to_decimals(reduction, 2)}% dmg reduction)'
        return result
    else:
        return ''


def _get_is_allowed_in_extension_grids(flags: str) -> str:
    is_allowed = lookups.GRID_TYPE_MASK_LOOKUP[2] in _convert_room_grid_type_flags(flags)
    if is_allowed:
        return 'Allowed in extension grids'
    else:
        return ''


def _get_emp_length(emp_length: str) -> str:
    if emp_length:
        emp_length_seconds = util.convert_ticks_to_seconds(int(emp_length))
        result = util.get_formatted_duration(emp_length_seconds, include_relative_indicator=False)
        return result
    else:
        return ''


def _get_manufacture_rate(manufacture_rate: str) -> str:
    if manufacture_rate:
        manufacture_rate = float(manufacture_rate)
        manufacture_speed = 1.0 / manufacture_rate
        manufacture_rate_per_hour = manufacture_rate * 3600
        result = f'{util.format_up_to_decimals(manufacture_speed)}s ({util.format_up_to_decimals(manufacture_rate_per_hour)}/hour)'
        return result
    else:
        return ''


def _get_max_storage_and_type(capacity: str, manufacture_capacity: str, manufacture_rate: str, manufacture_type: str, room_type: str) -> str:
    if capacity and ((not manufacture_capacity or not manufacture_rate) or (room_type and room_type == 'Recycling')):
        value = _get_value(capacity)
    elif manufacture_capacity and manufacture_rate:
        value = _get_value(manufacture_capacity)
    else:
        value = ''

    if value:
        print_type = (capacity and not manufacture_rate) or (manufacture_capacity and manufacture_rate)
        if print_type:
            manufacture_type = _get_construction_type(manufacture_type)
            return f'{value} {manufacture_type}'
        else:
            return value
    else:
        return ''


def _get_queue_limit(capacity: str, manufacture_capacity: str, manufacture_rate: str) -> str:
    if manufacture_capacity and not manufacture_rate:
        return _get_value(manufacture_capacity)
    else:
        return ''


def _get_reload_time(room_reload_time: str) -> str:
    if room_reload_time:
        reload_ticks = float(room_reload_time)
        reload_seconds = reload_ticks / 40.0
        reload_speed = 60.0 / reload_seconds
        result = f'{reload_seconds:0.{settings.DEFAULT_FLOAT_PRECISION}f}s (~ {util.format_up_to_decimals(reload_speed)}/min)'
        return result
    else:
        return ''


def _get_room_name(room_name: str, room_short_name: str, room_type: str) -> str:
    result = ''
    if room_short_name:
        room_short_name = _get_pretty_short_name(room_short_name)
        result += f'[{room_short_name}] '
    result += room_name
    if room_type:
        result += f' ({room_type})'
    return f'**{result}**'


def _get_room_size(room_columns: str, room_rows: str) -> str:
    result = f'{room_columns}x{room_rows}'
    return result


def _get_shots_fired(volley: str, volley_delay: str) -> str:
    if volley and volley != '1':
        volley = int(volley)
        volley_delay = int(volley_delay)
        volley_delay_seconds = util.format_up_to_decimals(util.convert_ticks_to_seconds(volley_delay), 3)
        result = f'{volley:d} (Delay: {volley_delay_seconds}s)'
        return result
    else:
        return ''


def _get_value(value: str, max_decimal_count: int = settings.DEFAULT_FLOAT_PRECISION) -> str:
    if value and value.lower() != 'none':
        try:
            i = float(value)
            if i:
                return util.get_reduced_number_compact(i, max_decimal_count=max_decimal_count)
            else:
                return ''
        except:
            pass

        return value
    else:
        return ''


def _get_wikia_link(room_name: str) -> str:
    if room_name:
        room_name = room_name.split(' Lv')[0]
        room_name = '_'.join([part.lower().capitalize() for part in room_name.split(' ')])
        result = util.get_wikia_link(room_name)
        if util.check_hyperlink(result):
            return f'<{result}>'
        else:
            return ''
    else:
        return ''


# ---------- Constants ----------

ROOM_DESIGN_BASE_PATH = 'RoomService/ListRoomDesigns2?languageKey=en'
ROOM_DESIGN_KEY_NAME = 'RoomDesignId'
ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'RoomName'
ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2 = 'RoomShortName'


ROOM_DESIGN_PURCHASE_BASE_PATH = 'RoomService/ListRoomDesigns2?languageKey=en'
ROOM_DESIGN_PURCHASE_KEY_NAME = 'RoomDesignPurchaseId'
ROOM_DESIGN_PURCHASE_DESCRIPTION_PROPERTY_NAME = 'RoomName'
ROOM_DESIGN_TYPE_PROPERTY_NAME = 'RoomType'

# RoomType: 'unit'
CAPACITY_PER_TICK_UNITS = {
    'Lift': ' pixel/s',
    'Radar': 's',
    'Stealth': 's'
}

# <RoomType>: { <Original display name>: (<New display name>, <Should display>)}
# Defaults:
# - Should display: True (if None)
ROOM_DETAILS_PROPERTY_OVERLOADS = {
    'AntiCraft': {
        'Max storage': ('', False)
    },
    'Bedroom': {
        'Max storage': ('Crew slots', None)
    },
    'Bridge': {
        'Max storage': ('Escape Modifier', None)
    },
    'Command': {
        'Max storage': ('Max AI lines', None)
    },
    'Corridor': {
        'Innate armor': ('', False),
        'Max storage': ('', False)
    },
    'Council': {
        'Max storage': ('Borrow limit', None),
        'Queue limit': ('Donation limit', None)
    },
    'Engine': {
        'Max storage': ('Dodge Modifier', None)
    },
    'Lift': {
        'Cap per tick': ('Speed', None),
        'Max storage': ('', False)
    },
    'Medical': {
        'Max storage': ('Crew HP healed', None)
    },
    'Printer': {
        'Queue limit': ('', False)
    },
    'Radar': {
        'Cap per tick': ('Cloak reduction', None),
        'Max storage': ('', False)
    },
    'Recycling': {
        'Manufacture speed': ('', False)
    },
    'Shield': {
        'Max storage': ('Shield points', None)
    },
    'Stealth': {
        'Cap per tick': ('Cloak duration', None),
        'Max storage': ('', False)
    },
    'Storage': {
        'Construction type': ('Storage type', None)
    },
    'Training': {
        'Max storage': ('', False)
    },
    'Trap': {
        'Max storage': ('Damage', None)
    },
    'Wall': {
        'Max storage': ('Armor value', None)
    }
}






# ---------- Helper functions ----------

def _calculate_innate_armor_percent(default_defense_bonus: int) -> float:
    if default_defense_bonus:
        result = (1.0 - 1.0 / (1.0 + (float(default_defense_bonus) / 100.0))) * 100
        return result
    else:
        return .0


def get_room_details_from_id_as_text(room_id: str, room_designs_data: dict = None) -> list:
    if not room_designs_data:
        room_designs_data = __room_designs_cache.get_data_dict3()

    room_info = room_designs_data[room_id]
    return get_room_details_from_data_as_text(room_info)


def _get_overload_info(room_type: str, display_name: str) -> str:
    if room_type in ROOM_DETAILS_PROPERTY_OVERLOADS.keys():
        if display_name in ROOM_DETAILS_PROPERTY_OVERLOADS[room_type].keys():
            return ROOM_DETAILS_PROPERTY_OVERLOADS[room_type][display_name]
    return display_name, None


def _get_parameter_from_room_info(room_info: dict, parameter: object) -> object:
    if isinstance(parameter, str):
        while '.' in parameter:
            split_parameter = parameter.split('.')
            property_name = split_parameter[0]
            parameter = '.'.join(split_parameter[1:])
            if property_name not in room_info.keys():
                continue
            room_info = room_info[property_name]

        if parameter in room_info.keys():
            result = room_info[parameter]
            result_lower = result.lower()
            if not result or result_lower == '0' or result_lower == 'none':
                return ''
            else:
                return result
        else:
            return ''
    else:
        return parameter


def _get_room_detail_from_data(room_info: dict, display_property_name: str, include_display_name: bool, parameter_definitions: list, transform_function: object) -> str:
    params = []
    room_type = room_info[ROOM_DESIGN_TYPE_PROPERTY_NAME]
    for parameter_definition in parameter_definitions:
        parameter = _get_parameter_from_room_info(room_info, parameter_definition)
        params.append(parameter)

    if transform_function:
        value = transform_function(*tuple(params))
    else:
        value = ', '.join(params)

    if value:
        display_property_name, include_value = _get_overload_info(room_type, display_property_name)
        if include_value is not False:
            if include_display_name:
                display_property_name = f'{display_property_name} = '
            else:
                display_property_name = ''
            return f'{display_property_name}{value}'
        else:
            return ''
    else:
        return ''


def get_room_details_from_data_as_text(room_info: dict) -> list:
    result = []
    room_type = room_info[ROOM_DESIGN_TYPE_PROPERTY_NAME]
    for display_property_name, include_display_name, parameter_definitions, transform_function, allowed_room_types in __room_details_properties:
        if not allowed_room_types or room_type in allowed_room_types:
            line = _get_room_detail_from_data(room_info, display_property_name, include_display_name, parameter_definitions, transform_function)
            if line:
                result.append(line)
    return result


def get_room_details_long_from_id_as_text(room_id: str, room_designs_data: dict = None) -> list:
    if not room_designs_data:
        room_designs_data = __room_designs_cache.get_data_dict3()

    room_info = room_designs_data[room_id]
    return get_room_details_long_from_data_as_text(room_info)


def get_room_details_long_from_data_as_text(room_info: dict) -> list:
    return get_room_details_from_data_as_text(room_info)


def get_room_details_short_from_id_as_text(room_id: str, room_designs_data: dict = None) -> list:
    if not room_designs_data:
        room_designs_data = __room_designs_cache.get_data_dict3()

    room_info = room_designs_data[room_id]
    return get_room_details_short_from_data_as_text(room_info)


def get_room_details_short_from_data_as_text(room_info: dict) -> list:
    room_name = room_info[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    room_short_name = get_room_short_name(room_info)
    if room_short_name:
        room_name += f' [{room_short_name}]'
    room_enhancement_type = room_info['EnhancementType']
    min_ship_level = room_info['MinShipLevel']
    return [f'{room_name} (Enhanced by: {room_enhancement_type}, Ship lvl: {min_ship_level})']


def get_room_short_name(room_info: dict) -> str:
    short_name = room_info[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2]
    if short_name:
        result = short_name.split(':')[0]
        return result
    else:
        return None


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


def _get_pretty_short_name(short_name: str) -> str:
    if short_name:
        result = short_name.split(':')[0]
        return result
    else:
        return None





# ---------- Room info ----------

def get_room_details_from_name(room_name: str, as_embed: bool = settings.USE_EMBEDS):
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


def _get_room_infos(room_name: str, room_designs_data: dict = None):
    if room_designs_data is None:
        room_designs_data = __room_designs_cache.get_data_dict3()

    room_design_ids = _get_room_design_ids_from_name(room_name, room_designs_data=room_designs_data)
    if not room_design_ids:
        room_design_ids = _get_room_design_ids_from_room_shortname(room_name, room_designs_data=room_designs_data)

    result = [room_designs_data[room_design_id] for room_design_id in room_design_ids if room_design_id in room_designs_data.keys()]
    return result


def _get_room_design_ids_from_name(room_name: str, room_designs_data: dict = None):
    if room_designs_data is None:
        room_designs_data = __room_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(room_designs_data, ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME, room_name)
    return results


def _get_room_design_ids_from_room_shortname(room_short_name: str, room_designs_data: dict = None):
    if room_designs_data is None:
        room_designs_data = __room_designs_cache.get_data_dict3()

    return_best_match = any(char.isdigit() for char in room_short_name)
    results = core.get_ids_from_property_value(room_designs_data, ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2, room_short_name)
    if results and return_best_match:
        results = [results[0]]
    return results


def _get_room_info_as_embed(room_name: str, room_infos: dict, room_designs_data: dict):
    return ''


def _get_room_info_as_text(room_name: str, room_infos: dict, room_designs_data: dict):
    lines = [f'**Room stats for \'{room_name}\'**']
    room_infos_count = len(room_infos)

    if room_infos_count == 1:
        lines.extend(get_room_details_from_data_as_text(room_infos[0]))
    else:
        big_set = room_infos_count > 3

        for i, room_info in enumerate(room_infos):
            if big_set:
                lines.extend(get_room_details_short_from_data_as_text(room_info))
            else:
                lines.extend(get_room_details_from_data_as_text(room_info))
                if i < room_infos_count - 1:
                    lines.append(settings.EMPTY_LINE)

    return lines


def _get_key_for_room_sort(room_info: dict, room_designs_data: dict) -> str:
    result = ''
    parent_infos = _get_parents(room_info, room_designs_data)
    if parent_infos:
        for parent_info in parent_infos:
            result += parent_info[ROOM_DESIGN_KEY_NAME].zfill(4)
    result += room_info[ROOM_DESIGN_KEY_NAME].zfill(4)
    return result





# ---------- Initilization ----------

__room_designs_cache = PssCache(
    ROOM_DESIGN_BASE_PATH,
    'RoomDesigns',
    ROOM_DESIGN_KEY_NAME)


__room_design_purchases_cache = PssCache(
    ROOM_DESIGN_BASE_PATH,
    'RoomDesignPurchases',
    ROOM_DESIGN_KEY_NAME,
    update_interval=60)


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
#List items schema:
# - Display name
# - Print display name
# - Arguments to use / properties to print
# - Transformation function
# - List of allowed room types (empty if allowed for all)
__room_details_properties = [
    ('Name', False, [ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME, ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2, ROOM_DESIGN_TYPE_PROPERTY_NAME], _get_room_name, []),
    ('Description', False, ['RoomDescription'], _get_description, []),
    ('Size (WxH)', True, ['Columns', 'Rows'], _get_room_size, []),
    ('Max power used', True, ['MaxSystemPower'], _get_value, []),
    ('Power generated', True, ['MaxPowerGenerated'], _get_value, []),
    ('Innate armor', True, ['DefaultDefenceBonus'], _get_innate_armor, []),
    ('Enhanced By', True, ['EnhancementType'], _get_value, []),
    ('Min hull lvl', True, ['MinShipLevel'], _get_value, []),
    ('Reload (Speed)', True, ['ReloadTime'], _get_reload_time, []),
    ('Shots fired', True, ['MissileDesign.Volley', 'MissileDesign.VolleyDelay'], _get_shots_fired, []),
    ('System dmg', True, ['MissileDesign.SystemDamage', 'ReloadTime', 'MaxSystemPower', 'MissileDesign.Volley', 'MissileDesign.VolleyDelay', False], _get_dmg_for_dmg_type, []),
    ('Shield dmg', True, ['MissileDesign.ShieldDamage', 'ReloadTime', 'MaxSystemPower', 'MissileDesign.Volley', 'MissileDesign.VolleyDelay', False], _get_dmg_for_dmg_type, []),
    ('Crew dmg', True, ['MissileDesign.CharacterDamage', 'ReloadTime', 'MaxSystemPower', 'MissileDesign.Volley', 'MissileDesign.VolleyDelay', False], _get_dmg_for_dmg_type, []),
    ('Hull dmg', True, ['MissileDesign.HullDamage', 'ReloadTime', 'MaxSystemPower', 'MissileDesign.Volley', 'MissileDesign.VolleyDelay', False], _get_dmg_for_dmg_type, []),
    ('Direct System dmg', True, ['MissileDesign.DirectSystemDamage', 'ReloadTime', 'MaxSystemPower', 'MissileDesign.Volley', 'MissileDesign.VolleyDelay', True], _get_dmg_for_dmg_type, []),
    ('EMP duration', True, ['MissileDesign.EMPLength'], _get_emp_length, []),
    ('Max storage', True, ['Capacity', 'ManufactureCapacity', 'ManufactureRate', 'ManufactureType', ROOM_DESIGN_TYPE_PROPERTY_NAME], _get_max_storage_and_type, []),
    ('Cap per tick', True, ['Capacity', ROOM_DESIGN_TYPE_PROPERTY_NAME], _get_capacity_per_tick, CAPACITY_PER_TICK_UNITS.keys()),
    ('Cooldown', True, ['CooldownTime'], _get_cooldown, []),
    ('Queue limit', True, ['Capacity', 'ManufactureCapacity', 'ManufactureRate'], _get_queue_limit, []),
    ('Manufacture speed', True, ['ManufactureRate'], _get_manufacture_rate, []),
    ('Gas per crew', True, ['ManufactureRate'], _get_value, ['Recycling']),
    ('Max crew blend', True, ['ManufactureCapacity'], _get_value, ['Recycling']),
    ('Build time', True, ['ConstructionTime'], _get_build_time, []),
    ('Build cost', True, ['PriceString'], _get_build_cost, []),
    ('Build requirement', True, ['RequirementString'], _get_build_requirement, []),
    ('Grid types', True, ['SupportedGridTypes'], _get_is_allowed_in_extension_grids, []),
    ('More info', True, ['Flags'], _convert_room_flags, []),
    ('Wikia link', True, [ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME], _get_wikia_link, [])
]











# ---------- Testing ----------

if __name__ == '__main__':
    test_rooms = ['ion']
    for room_name in test_rooms:
        os.system('clear')
        result = get_room_details_from_name(room_name, as_embed=False)
        for line in result[0]:
            print(line)
        result = ''