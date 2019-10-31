#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from cache import PssCache
import pss_assert
import pss_core as core
import pss_item as item
import pss_lookups as lookups
import utility as util


# ---------- Transformation functions ----------

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


def _convert_room_flags(flags: str) -> str:
    result = []
    flags = int(flags)
    if result:
        return ', '.join(result)
    else:
        return ''


def _get_dmg_for_dmg_type(dmg: str, reload_time: str, max_power: str, volley: str, volley_delay: str, print_percent: bool) -> str:
    """Returns base dps and dps per power"""
    if dmg:
        dmg = float(dmg)
        reload_time = float(reload_time)
        reload_seconds = util.convert_ticks_to_seconds(int(reload_time))
        max_power = int(max_power)
        volley = int(volley)
        volley_duration_seconds = util.convert_ticks_to_seconds((volley - 1) * volley_delay)
        reload_seconds += volley_duration_seconds
        full_volley_dmg = dmg * volley
        dps = full_volley_dmg / reload_seconds
        dps_per_power = dps / max_power
        if print_percent:
            percent = '%'
        else:
            percent = ''
        if volley > 1:
            single_volley_dmg = f'per volley: {dmg:0.1f}, '
        else:
            single_volley_dmg = ''
        result = f'{full_volley_dmg:0.1f}{percent} ({single_volley_dmg}dps: {dps:0.2f}{percent}, per power: {dps_per_power:0.2f}{percent})'
        return result
    else:
        return ''


def _get_innate_armor(default_defense_bonus: str) -> str:
    if default_defense_bonus and default_defense_bonus != '0':
        reduction = _calculate_innate_armor_percent(int(default_defense_bonus))
        result = f'{default_defense_bonus} ({reduction:0.2f}%)'
        return result
    else:
        return ''


def _get_pretty_build_cost(price_string: str) -> str:
    if price_string:
        resource_type, amount = price_string.split(':')
        cost, cost_multiplier = util.get_reduced_number(amount)
        currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[resource_type.lower()]
        result = f'{cost}{cost_multiplier} {currency_emoji}'
        return result
    else:
        return ''


def _get_pretty_build_requirement(requirement_string: str) -> str:
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


def _get_pretty_build_time(construction_time: str) -> str:
    if construction_time and construction_time != '0':
        construction_time = int(construction_time)
        result = util.get_formatted_duration(construction_time, include_relative_indicator=False)
        return result
    else:
        return ''


def _get_emp_length(emp_length: str) -> str:
    emp_length_seconds = util.convert_ticks_to_seconds(int(emp_length))
    result = util.get_formatted_duration(emp_length_seconds, include_relative_indicator=False)
    return result


def _get_reload_time(room_reload_time: str, per_hour: bool = False) -> str:
    if room_reload_time:
        reload_ticks = int(room_reload_time)
        reload_seconds = reload_ticks / 40
        reload_speed = 60 / reload_seconds
        if per_hour:
            reload_speed *= 60
            reload_speed = f'{reload_speed}/hour'
        else:
            reload_speed = f'{reload_speed}/min'
        result = f'{reload_seconds}s ({reload_speed})'
        return result
    else:
        return ''


def _get_room_description(room_type: str, room_description: str) -> str:
    result = ''
    if room_type and room_type.lower() != 'none':
        result += f'[{room_type}] '
    result += room_description
    return result


def _get_room_name(room_name: str, room_short_name: str) -> str:
    result = f'**{room_name}**'
    if room_short_name:
        room_short_name = _get_pretty_short_name(room_short_name)
        result += f' **[{room_short_name}]**'
    return result


def _get_room_size(room_columns: str, room_rows: str) -> str:
    result = f'{room_columns}x{room_rows}'
    return result


def _get_shots_fired(volley: str, volley_delay: str) -> str:
    if volley and volley != '1':
        volley = int(volley)
        volley_delay = int(volley_delay)
        volley_delay_seconds = util.convert_ticks_to_seconds(volley_delay)
        result = f'{volley}, delay: {volley_delay_seconds}'
        return result
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


# Format: PropertyName: (DisplayName, TransformFunction, Required)
# Optional meaning, if the value is 0 or empty, don't print.
ROOM_PROPERTY_PROPERTIES = {
    #'Capacity': ('Storage', None, True),
    #'CategoryType': ('Category', None, True),
    #'CharacterDamage': ('Crew dmg', None, True),
    #'Columns': ('Width', None, False),
    #'ConstructionTime': ('Construction time', None, True),
    #'DefaultDefenceBonus': ('Innate armor', None, True),
    #'DirectSystemDamage': ('Direct system dmg', None, True),
    #'EMPLength': ('EMP length', None, True),
    #'EnhancementType': ('Enhanced by', None, True),
    #'Flags': ('Additional info', _convert_room_flags, False),
    #'HullDamage': ('Hull dmg', None, True),
    #'Level': ('Level', None, False),
    #'ManufactureCapacity': ('Max queue', None, True),
    #'ManufactureRate': ('Construction rate', None, True),
    #'ManufactureType': ('Construction type', None, True),
    #'MaxPowerGenerated': ('Power produced', None, True),
    #'MaxSystemPower': ('Max power used/HP', None, True),
    #'MinShipLevel': ('Min ship level', None, True),
    #'MissileDesignName': ('Projectile name', None, True),
    #'PriceString': ('Construction cost', None, False),
    #'ReloadTime': ('Reload time', None, True),
    #'RequirementString': ('Requires', None, True),
    #'RoomDescription': (None, None, False),
    #'Rows': ('Height', None, False),
    #'ShieldDamage': ('Shield dmg', None, True),
    #'SupportedGridTypes': ('Allowed grid types', _convert_room_grid_type_flags, False),
    #'SystemDamage': ('System dmg', None, True),
    #'Volley': ('Shots fired', None, True),
    #'VolleyDelay': ('Delay between shots', None, True)
}
ROOM_EXTENDED_PROPERTIES = {
    """Dict keys: Display names
       Dict values schema:
       - Print display name
       - Arguments to use / properties to print
       - Custom property function"""
    'Name': (False, (ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME, ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2, ), _get_room_name),
    'Description': (False, ['RoomType', 'Description'], _get_room_description),
    'Size (WxH)': (True, ['Columns', 'Rows'], _get_room_size),
    'Max power used': (True, ['MaxSystemPower'], None),
    'Power generated': (True, ['MaxPowerGenerated'], None),
    'Innate armor': (True, ['DefaultDefenceBonus'], _get_innate_armor),
    'Enhanced By': (True, ['EnhancementType'], None),
    'Min hull lvl': (True, ['MinShipLevel'], None),
    'System dmg': (True, ['SystemDamage', 'ReloadTime', 'MaxPower', 'Volley', 'VolleyDelay', False], _get_dmg_for_dmg_type),
    'Shield dmg': (True, ['SystemDamage', 'ReloadTime', 'MaxPower', 'Volley', 'VolleyDelay', False], _get_dmg_for_dmg_type),
    'Crew dmg': (True, ['SystemDamage', 'ReloadTime', 'MaxPower', 'Volley', 'VolleyDelay', False], _get_dmg_for_dmg_type),
    'Hull dmg': (True, ['SystemDamage', 'ReloadTime', 'MaxPower', 'Volley', 'VolleyDelay', False], _get_dmg_for_dmg_type),
    'Direct System dmg': (True, ['SystemDamage', 'ReloadTime', 'MaxPower', 'Volley', 'VolleyDelay', True], _get_dmg_for_dmg_type),
    'EMP duration': (True, ['EMPLength'], _get_emp_length),
    'Reload/Speed': (True, ['ReloadTime'], _get_reload_time),
    'Shots fired': (True, ['Volley', 'VolleyDelay'], _get_shots_fired),
    'Max storage': (True, ['Capacity'], util.get_reduced_number_compact),
    'Max construction queue': (True, ['ManufactureCapacity'], None),
    'Construction type': (True, ['ManufactureType'], None),
    'Construction rate': (True, ['ManufactureRate'], _get_reload_time),
    'Build time': (True, ['ConstructionTime'], _get_pretty_build_time),
    'Build cost': (True, ['PriceString'], _get_pretty_build_cost),
    'Build requirement': (True, ['RequirementString'], _get_pretty_build_requirement),
    'Allowed grid types': (True, ['SupportedGridTypes'], _convert_room_grid_type_flags),
    'More info': (True, ['Flags'], _convert_room_flags)
}





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






# ---------- Helper functions ----------

def _calculate_innate_armor_percent(default_defense_bonus: int) -> float:
    if default_defense_bonus:
        result = 1.0 / (1.0 + (float(default_defense_bonus) / 100.0))
        return result
    else:
        return .0


def get_room_details_from_id_as_text(room_id: str, room_designs_data: dict = None) -> list:
    if not room_designs_data:
        room_designs_data = __room_designs_cache.get_data_dict3()

    room_info = room_designs_data[room_id]
    return get_room_details_from_data_as_text(room_info)


def get_room_details_from_data_as_text(room_info: dict) -> list:
    room_name = room_info[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    room_short_name = get_room_short_name(room_info)
    room_description = room_info['RoomDescription']
    room_flags = int(room_info['Flags'])
    room_consumes_power = (room_flags & 1) > 0
    #room_is_weapon = (room_flags & 2) > 0
    #room_is_manufactoring = (room_flags & 4) > 0
    room_type = room_info['RoomType']
    room_rows = room_info['Rows']
    room_columns = room_info['Columns']
    room_size = f'{room_columns}x{room_rows}'
    room_grid_types = _convert_room_grid_type_flags(room_info['SupportedGridTypes'])
    room_enhancement_type = room_info['EnhancementType']
    max_power_consumed = room_info['MaxSystemPower']
    min_ship_level = room_info['MinShipLevel']

    first_line = f'**{room_name}**'
    if room_short_name:
        first_line += f' **[{room_short_name}]**'
    result = [first_line]
    result.append(room_description)
    result.append(f'Type: {room_type}')
    result.append(f'Size (WxH): {room_size}')
    if room_consumes_power:
        result.append(f'Max power consumed: {max_power_consumed}')
    if room_enhancement_type != 'None':
        result.append(f'Enhanced by: {room_enhancement_type} stat')
    result.append(f'Minimum ship lvl: {min_ship_level}')
    result.append(f'Allowed grid types: {room_grid_types}')
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
    room_type = room_info['RoomType']
    room_enhancement_type = room_info['EnhancementType']
    min_ship_level = room_info['MinShipLevel']
    return [f'{room_name} (Type: {room_type}, Enhanced by: {room_enhancement_type}, Min ship lvl: {min_ship_level})']


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


def _get_room_property_display(room_info: dict, property_name: str) -> str:
    display_name, transform_function, required = ROOM_PROPERTY_PROPERTIES[property_name]
    if transform_function:
        value = transform_function(room_info[property_name])
    else:
        value = room_info[property_name]

    if value or required:
        if display_name:
            result = f'{display_name}: {value}'
        else:
            result = value
    else:
        result = None

    return result




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

    results = core.get_ids_from_property_value(room_designs_data, ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2, room_short_name, return_on_first=return_on_first)
    return results


def _get_room_info_as_embed(room_name: str, room_infos: dict, room_designs_data: dict):
    return ''


def _get_room_info_as_text(room_name: str, room_infos: dict, room_designs_data: dict):
    lines = [f'**Room stats for \'{room_name}\'**']
    room_infos = sorted(room_infos, key=lambda room_info: (
        _get_key_for_room_sort(room_info, room_designs_data)
    ))
    room_infos_count = len(room_infos)

    if room_infos_count == 1:
        lines.extend(__get_room_details_for_type(room_infos[0]))
    else:
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
    result = get_room_details_from_name('VM')





# ---------- Room details ----------

def __get_room_details_for_type(room_info: dict) -> list:
    room_type = room_info['RoomType']
    func_name = f'__get_room_details_for_type_{room_type}'
    if func_name in globals().keys():
        func_by_type = globals()[func_name]
    else:
        func_by_type = get_room_details_long_from_data_as_text
    result = func_by_type(room_info)
    return result


def __get_room_details_for_type_Android(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_AntiCraft(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Bedroom(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Bridge(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Cannon(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Carrier(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Command(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Corridor(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Council(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Engine(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Gas(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Laser(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Lift(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Medical(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Mineral(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Missile(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_None(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Printer(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Radar(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Reactor(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Recycling(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Research(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Shield(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_StationMissile(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Stealth(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Storage(room_info: dict) -> list:
    """Fields: Capacity, DefaultDefenceBonus, PriceString"""
    result = get_room_details_from_data_as_text(room_info)
    capacity = room_info['Capacity']
    innate_armor = room_info['DefaultDefenceBonus']
    price = room_info['PriceString']
    result.append(f'Capacity: {capacity}')
    return result


def __get_room_details_for_type_Supply(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Teleport(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Training(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Trap(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)


def __get_room_details_for_type_Wall(room_info: dict) -> list:
	return get_room_details_long_from_data_as_text(room_info)