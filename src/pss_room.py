#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import discord
import discord.ext.commands as commands
import inspect
import os
import random
from typing import Callable, Dict, Iterable, List, Tuple, Union

from cache import PssCache
import pss_assert
import pss_core as core
import pss_entity as entity
import pss_item as item
import pss_lookups as lookups
import pss_research as research
import settings
import utility as util










# ---------- Constants ----------

ROOM_DESIGN_BASE_PATH = 'RoomService/ListRoomDesigns2?languageKey=en'
ROOM_DESIGN_KEY_NAME = 'RoomDesignId'
ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'RoomName'
ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2 = 'RoomShortName'
ROOM_DESIGN_TYPE_PROPERTY_NAME = 'RoomType'


ROOM_DESIGN_PURCHASE_BASE_PATH = 'RoomService/ListRoomDesignPurchase?languageKey=en'
ROOM_DESIGN_PURCHASE_KEY_NAME = 'RoomDesignPurchaseId'
ROOM_DESIGN_PURCHASE_DESCRIPTION_PROPERTY_NAME = 'RoomName'


ROOM_DESIGN_SPRITES_BASE_PATH = 'RoomDesignSpriteService/ListRoomDesignSprites'
ROOM_DESIGN_SPRITES_KEY_NAME = 'RoomDesignSpriteId'


MISSILE_DESIGN_BASE_PATH = 'RoomService/ListMissileDesigns'
MISSILE_DESIGN_KEY_NAME = 'MissileDesignId'
MISSILE_DESIGN_DESCRIPTION_PROPERTY_NAME = 'MissileDesignName'


# RoomType: 'unit'
CAPACITY_PER_TICK_UNITS = {
    'Lift': ' pixel/s',
    'Radar': 's',
    'Stealth': 's'
}


# str: {str, str}
__DISPLAY_NAMES = {
    'ap_dmg': {
        'default': 'AP dmg'
    },
    'build_cost': {
        'default': 'Build cost'
    },
    'build_time': {
        'default': 'Build time'
    },
    'build_requirement': {
        'default': 'Build requirement'
    },
    'cap_per_tick': {
        'default': 'Cap per tick',
        'Lift': 'Speed',
        'Radar': 'Cloak reduction',
        'Stealth': 'Cloak duration'
    },
    'category': {
        'default': 'Category'
    },
    'cooldown': {
        'default': 'Cooldown'
    },
    'construction_type': {
        'default': 'Construction type',
        'Storage': 'Storage type'
    },
    'crew_dmg': {
        'default': 'Crew dmg'
    },
    'emp_duration': {
        'default': 'EMP duration'
    },
    'enhanced_by': {
        'default': 'Enhanced by'
    },
    'gas_per_crew': {
        'default': 'Gas per crew'
    },
    'grid_types': {
        'default': 'Grid types'
    },
    'hull_dmg': {
        'default': 'Hull dmg'
    },
    'innate_armor': {
        'default': 'Innate armor',
        'Corridor': None
    },
    'manufacture_speed': {
        'default': 'Manufacture speed',
        'Recycling': None
    },
    'max_crew_blend': {
        'default': 'Max crew blend'
    },
    'max_power_used': {
        'default': 'Max power used'
    },
    'max_storage': {
        'default': 'Max storage',
        'AntiCraft': None,
        'Bedroom': 'Crew slots',
        'Bridge': 'Escape modifier',
        'Command': 'Max AI lines',
        'Corridor': None,
        'Council': 'Borrow limit',
        'Engine': 'Dodge modifier',
        'Lift': None,
        'Medical': 'Crew HP healed',
        'Radar': None,
        'Reactor': None,
        'Shield': 'Shield points',
        'Stealth': None,
        'Training': None,
        'Trap': 'Crew dmg',
        'Wall': 'Armor value'
    },
    'min_hull_lvl': {
        'default': 'Min ship lvl'
    },
    'more_info': {
        'default': 'More info'
    },
    'power_generated': {
        'default': 'Power generated'
    },
    'queue_limit': {
        'default': 'Queue limit',
        'Council': 'Borrow limit',
        'Printer': None
    },
    'reload_speed': {
        'default': 'Reload speed'
    },
    'shield_dmg': {
        'default': 'Shield dmg'
    },
    'shots_fired': {
        'default': 'Shots fired'
    },
    'size': {
        'default': 'Size (WxH)'
    },
    'system_dmg': {
        'default': 'System dmg'
    },
    'type': {
        'default': 'Type'
    },
    'wikia': {
        'default': 'Wikia'
    },
}


__AMMO_TYPE_OVERWRITES = {
    'ION': 'Ion Core(s)'
}










# ---------- Room info ----------

def get_room_design_details_by_id(room_design_id: str, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData) -> entity.EntityDesignDetails:
    if room_design_id and room_design_id in rooms_designs_data:
        result = __create_room_design_details_from_info(rooms_designs_data[room_design_id], rooms_designs_data, items_designs_data, researches_designs_data, rooms_designs_sprites_designs_data)
    else:
        result = None
    return result


async def get_room_details_by_name(room_name: str, ctx: commands.Context = None, as_embed: bool = settings.USE_EMBEDS) -> Union[List[str], discord.Embed]:
    pss_assert.valid_entity_name(room_name, allowed_values=__allowed_room_names)

    rooms_designs_data = await rooms_designs_retriever.get_data_dict3()
    rooms_designs_infos = _get_room_infos(room_name, rooms_designs_data)

    if not rooms_designs_infos:
        return [f'Could not find a room named **{room_name}**.'], False
    else:
        items_designs_data = await item.items_designs_retriever.get_data_dict3()
        researches_designs_data = await research.researches_designs_retriever.get_data_dict3()
        rooms_designs_sprites_designs_data = await rooms_designs_sprites_retriever.get_data_dict3()
        rooms_designs_details_collection = __create_rooms_designs_details_collection_from_infos(rooms_designs_infos, rooms_designs_data, items_designs_data, researches_designs_data, rooms_designs_sprites_designs_data)
        if as_embed:
            return (await rooms_designs_details_collection.get_entity_details_as_embed(ctx)), True
        else:
            return (await rooms_designs_details_collection.get_entity_details_as_text()), True


def _get_room_infos(room_name: str, rooms_designs_data: entity.EntitiesDesignsData) -> List[entity.EntityDesignInfo]:
    room_design_ids = _get_room_design_ids_from_name(room_name, rooms_designs_data)
    if not room_design_ids:
        room_design_ids = _get_room_design_ids_from_room_shortname(room_name, rooms_designs_data)

    result = [rooms_designs_data[room_design_id] for room_design_id in room_design_ids if room_design_id in rooms_designs_data.keys()]
    result = sorted(result, key=lambda entity_info: _get_key_for_room_sort(entity_info, rooms_designs_data))
    return result


def _get_room_design_ids_from_name(room_name: str, rooms_designs_data: entity.EntitiesDesignsData) -> List[str]:
    results = core.get_ids_from_property_value(rooms_designs_data, ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME, room_name)
    return results


def _get_room_design_ids_from_room_shortname(room_short_name: str, rooms_designs_data: entity.EntitiesDesignsData):
    return_best_match = any(char.isdigit() for char in room_short_name)
    results = core.get_ids_from_property_value(rooms_designs_data, ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2, room_short_name)
    if results and return_best_match:
        results = [results[0]]
    return results


def _get_key_for_room_sort(room_info: dict, rooms_designs_data: dict) -> str:
    parent_infos = __get_parents(room_info, rooms_designs_data)
    result = room_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2)
    if result:
        result = result.split(':')[0]
    else:
        result = room_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME)[0:3]
    result.ljust(3)
    result += ''.join([parent_info[ROOM_DESIGN_KEY_NAME].zfill(4) for parent_info in parent_infos])
    return result










# ---------- Create EntityDesignDetails ----------

def __create_room_design_details_from_info(room_design_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData) -> entity.EntityDesignDetails:
    return entity.EntityDesignDetails(room_design_info, __properties['title'], __properties['description'], __properties['long'], __properties['short'], __properties['embed'], rooms_designs_data, items_designs_data, researches_designs_data, rooms_designs_sprites_designs_data)


def __create_room_design_details_list_from_infos(rooms_designs_infos: List[entity.EntityDesignInfo], rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData) -> List[entity.EntityDesignDetails]:
    return [__create_room_design_details_from_info(room_design_info, rooms_designs_data, items_designs_data, researches_designs_data, rooms_designs_sprites_designs_data) for room_design_info in rooms_designs_infos]


def __create_rooms_designs_details_collection_from_infos(rooms_designs_infos: List[entity.EntityDesignInfo], rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData) -> entity.EntityDesignDetailsCollection:
    rooms_designs_details = __create_room_design_details_list_from_infos(rooms_designs_infos, rooms_designs_data, items_designs_data, researches_designs_data, rooms_designs_sprites_designs_data)
    result = entity.EntityDesignDetailsCollection(rooms_designs_details, big_set_threshold=3)
    return result










# ---------- Transformation functions ----------

def __convert_room_flags(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        flags = room_info.get('Flags')
        if entity.has_value(flags):
            result = []
            flags = int(flags)
            if result:
                return ', '.join(result)
            else:
                return None
        else:
            return None
    else:
        return None


def __get_build_cost(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        price_string = room_info.get('PriceString')
        if price_string:
            resource_type, amount = price_string.split(':')
            cost = util.get_reduced_number_compact(amount)
            currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[resource_type.lower()]
            result = f'{cost} {currency_emoji}'
            return result
        else:
            return None
    else:
        return None


async def __get_build_requirement(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        requirement_string = room_info.get('RequirementString')
        if requirement_string:
            requirement_string = requirement_string.lower()
            required_type, required_id = requirement_string.split(':')

            if 'x' in required_id:
                required_id, required_amount = required_id.split('x')
            else:
                required_amount = '1'

            if required_type == 'item':
                item_design_details = item.get_item_design_details_by_id(required_id, items_designs_data)
                result = f'{required_amount}x ' + ''.join((await item_design_details.get_details_as_text_short()))
                return result
            elif required_type == 'research':
                research_design_details = research.get_research_design_details_by_id(required_id, researches_designs_data)
                result = ''.join(await research_design_details.get_details_as_text_short())
                return result
            else:
                return requirement_string
        else:
            return None
    else:
        return None


def __get_capacity_per_tick(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        room_type = room_info.get(ROOM_DESIGN_TYPE_PROPERTY_NAME)
        capacity = room_info.get('Capacity')
        if entity.has_value(capacity) and room_type:
            cap_per_tick = util.convert_ticks_to_seconds(int(capacity))
            result = f'{util.format_up_to_decimals(cap_per_tick, 3)}{CAPACITY_PER_TICK_UNITS[room_type]}'
            return result
        else:
            return None
    else:
        return None


def __get_damage(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        dmg = kwargs.get('entity_property')
        print_percent = kwargs.get('print_percent')
        reload_time = room_info.get('ReloadTime')
        max_power = room_info.get('MaxSystemPower')
        volley = entity.get_property_from_entity_info(room_info, 'MissileDesign.Volley')
        volley_delay = entity.get_property_from_entity_info(room_info, 'MissileDesign.VolleyDelay')
        result = __get_dmg_for_dmg_type(dmg, reload_time, max_power, volley, volley_delay, print_percent)
        return result
    else:
        return None


def __get_innate_armor(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        default_defense_bonus = room_info.get('DefaultDefenceBonus')
        if entity.has_value(default_defense_bonus):
            reduction = (1.0 - 1.0 / (1.0 + (float(default_defense_bonus) / 100.0))) * 100
            result = f'{default_defense_bonus} ({util.format_up_to_decimals(reduction, 2)}% dmg reduction)'
            return result
        else:
            return None
    else:
        return None


async def __get_interior_sprite_url(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    room_design_id = room_info.get(ROOM_DESIGN_KEY_NAME)
    if entity.has_value(room_design_id):
        sprites_infos = [room_design_sprite_design for room_design_sprite_design in rooms_designs_sprites_designs_data.values() if room_design_sprite_design.get(ROOM_DESIGN_KEY_NAME) == room_design_id]
        # if found, get a random SpriteId from a row with:
        #  - RoomSpriteType == 'Exterior'
        exterior_sprites_infos = [room_design_sprite_design for room_design_sprite_design in sprites_infos if room_design_sprite_design.get('RoomSpriteType').strip().lower() == 'interior']
        if exterior_sprites_infos:
            # Create an url with the SpriteId
            result = await entity.get_download_sprite_link(exterior_sprites_infos[0].get('SpriteId'))
            return result
        else:
            return None
    else:
        return None


def __get_is_allowed_in_extension_grids(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        supported_grid_types = int(room_info.get('SupportedGridTypes', '0'))
        if (supported_grid_types & 2) != 0:
            return 'Allowed in extension grids'
        else:
            return None
    else:
        return None


def __get_manufacture_rate(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        manufacture_rate = room_info.get('ManufactureRate')
        if entity.has_value(manufacture_rate):
            manufacture_rate = float(manufacture_rate)
            manufacture_speed = 1.0 / manufacture_rate
            manufacture_rate_per_hour = manufacture_rate * 3600
            result = f'{util.format_up_to_decimals(manufacture_speed)}s ({util.format_up_to_decimals(manufacture_rate_per_hour)}/hour)'
            return result
        else:
            return None
    else:
        return None


def __get_max_storage_and_type(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        capacity = room_info.get('Capacity')
        manufacture_capacity = room_info.get('ManufactureCapacity')
        manufacture_rate = room_info.get('ManufactureRate')
        manufacture_type = room_info.get('ManufactureType')
        room_type = room_info.get(ROOM_DESIGN_TYPE_PROPERTY_NAME)
        if entity.has_value(capacity) and ((not entity.has_value(manufacture_capacity) or not entity.has_value(manufacture_rate)) or (room_type and room_type == 'Recycling')):
            value = __parse_value(capacity)
        elif entity.has_value(manufacture_capacity) and entity.has_value(manufacture_rate):
            value = __parse_value(manufacture_capacity)
        else:
            value = None

        if value:
            print_type = (entity.has_value(capacity) and not entity.has_value(manufacture_rate)) or (entity.has_value(manufacture_capacity) and entity.has_value(manufacture_rate))
            if print_type:
                construction_type = ''
                if entity.has_value(manufacture_type):
                    lower = manufacture_type.lower()
                    if lower in lookups.CURRENCY_EMOJI_LOOKUP.keys():
                        construction_type = lookups.CURRENCY_EMOJI_LOOKUP[lower]
                    else:
                        construction_type = __get_manufacture_type(room_info)
                if construction_type:
                    return f'{value} {construction_type}'
                else:
                    return value
            else:
                return value
        else:
            return None
    else:
        return None


def __get_property_display_name(room_design_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    display_name_key = kwargs.get('display_name_key')
    display_names = kwargs.get('display_names')
    room_type = room_design_info.get(ROOM_DESIGN_TYPE_PROPERTY_NAME)
    result = None
    if display_name_key and room_type:
        display_name = display_names.get(display_name_key, {})
        if display_name:
            result = display_name.get(room_type, display_name.get('default'))
        else:
            raise Exception(f'Get room property display name: Could not find a display name with the key \'{display_name_key}\'! Please contact the author about this.')
    return result


def __get_queue_limit(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        manufacture_capacity = room_info.get('ManufactureCapacity')
        manufacture_rate = room_info.get('ManufactureRate')
        if entity.has_value(manufacture_capacity) and not entity.has_value(manufacture_rate):
            return __parse_value(manufacture_capacity)
        else:
            return None
    else:
        return None


async def __get_random_exterior_sprite_url(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    room_design_id = room_info.get(ROOM_DESIGN_KEY_NAME)
    if entity.has_value(room_design_id):
        sprites_infos = [room_design_sprite_design for room_design_sprite_design in rooms_designs_sprites_designs_data.values() if room_design_sprite_design.get(ROOM_DESIGN_KEY_NAME) == room_design_id]
        exterior_sprites_infos = [room_design_sprite_design for room_design_sprite_design in sprites_infos if room_design_sprite_design.get('RoomSpriteType').strip().lower() == 'exterior']
        if exterior_sprites_infos:
            room_design_sprite_design_info = exterior_sprites_infos[random.randint(0, len(exterior_sprites_infos) - 1)]
            result = await entity.get_download_sprite_link(room_design_sprite_design_info.get('SpriteId'))
            return result
        else:
            return None
    else:
        return None


def __get_reload_time(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        reload_time = room_info.get('ReloadTime')
        if entity.has_value(reload_time):
            reload_ticks = float(reload_time)
            reload_seconds = reload_ticks / 40.0
            reload_speed = 60.0 / reload_seconds
            result = f'{reload_seconds:0.{settings.DEFAULT_FLOAT_PRECISION}f}s (~ {util.format_up_to_decimals(reload_speed)}/min)'
            return result
        else:
            return None
    else:
        return None


def __get_room_name(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    room_name = room_info[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    room_short_name = room_info[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2]
    if room_short_name:
        short_name = room_short_name.split(':')[0]
    else:
        short_name = None
    result = room_name
    if short_name:
        result += f' [{short_name}]'
    return result


def __get_room_name(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    room_name = room_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME)
    result = room_name

    room_short_name = room_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2)
    if room_short_name:
        short_name = room_short_name.split(':')[0]
    else:
        short_name = None
    if short_name:
        result += f' [{short_name}]'
    return result


def __get_shots_fired(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        volley = entity.get_property_from_entity_info(room_info, 'MissileDesign.Volley')
        volley_delay = entity.get_property_from_entity_info(room_info, 'MissileDesign.VolleyDelay')
        if entity.has_value(volley) and volley != '1':
            volley = int(volley)
            volley_delay = int(volley_delay)
            volley_delay_seconds = util.format_up_to_decimals(util.convert_ticks_to_seconds(volley_delay), 3)
            result = f'{volley:d} (Delay: {volley_delay_seconds}s)'
            return result
        else:
            return None
    else:
        return None


def __get_size(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        columns = room_info.get('Columns')
        rows = room_info.get('Rows')
        if columns and rows:
            result = f'{columns}x{rows}'
            return result
        else:
            return None
    else:
        return None


def __get_value(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        value = kwargs.get('entity_property')
        if value:
            max_decimal_count = kwargs.get('max_decimal_count', settings.DEFAULT_FLOAT_PRECISION)
            result = __parse_value(value, max_decimal_count)
            return result
        else:
            return None
    else:
        return None


def __get_value_as_duration(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        value = kwargs.get('entity_property')
        if value:
            result = util.get_formatted_duration(int(value), include_relative_indicator=False, exclude_zeros=True)
            return result
        else:
            return None
    else:
        return None


def __get_value_as_seconds(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        value = kwargs.get('entity_property')
        if value:
            value_seconds = util.convert_ticks_to_seconds(int(value))
            result = f'{util.format_up_to_decimals(value_seconds, 3)}s'
            return result
        else:
            return None
    else:
        return None


async def __get_wikia_link(room_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, rooms_designs_sprites_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types')):
        return_plain = kwargs.get('return_plain')
        room_name = room_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME)
        if room_name:
            room_name = room_name.split(' Lv')[0]
            room_name = '_'.join([part.lower().capitalize() for part in room_name.split(' ')])
            result = await util.get_wikia_link(room_name)
            if await util.check_hyperlink(result):
                if return_plain:
                    return result
                else:
                    return f'<{result}>'
            else:
                return None
        else:
            return None
    else:
        return None


def __is_allowed_room_type(room_info: entity.EntityDesignInfo, allowed_room_types: Iterable) -> bool:
    room_type = room_info.get(ROOM_DESIGN_TYPE_PROPERTY_NAME)
    return (not allowed_room_types) or (room_type in allowed_room_types)










# ---------- Helper functions ----------

def __get_dmg_for_dmg_type(dmg: str, reload_time: str, max_power: str, volley: str, volley_delay: str, print_percent: bool) -> str:
    """Returns base dps and dps per power"""
    if dmg:
        dmg = float(dmg)
        reload_time = int(reload_time)
        reload_seconds = util.convert_ticks_to_seconds(reload_time)
        max_power = int(max_power)
        volley = int(volley)
        if volley_delay:
            volley_delay = int(volley_delay)
        else:
            volley_delay = 0
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
        return None


def __get_parents(room_info: dict, rooms_designs_data: dict) -> list:
    parent_room_design_id = room_info['UpgradeFromRoomDesignId']
    if parent_room_design_id == '0':
        parent_room_design_id = None

    if parent_room_design_id is not None:
        parent_info = rooms_designs_data[parent_room_design_id]
        result = __get_parents(parent_info, rooms_designs_data)
        result.append(parent_info)
        return result
    else:
        return []


def __get_manufacture_type(room_design_info: entity.EntityDesignInfo) -> str:
    short_name = __get_short_name(room_design_info)
    result = __AMMO_TYPE_OVERWRITES.get(short_name.upper(), room_design_info.get('ManufactureType'))
    return result


def __get_min_ship_lvl_display_name(room_design_info: entity.EntityDesignInfo, rooms_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    display_name_key = kwargs.get('display_name_key')
    display_names = kwargs.get('entity_property')
    room_type = room_design_info.get(ROOM_DESIGN_TYPE_PROPERTY_NAME)
    result = None
    if display_name_key and room_type:
        display_name = display_names.get(display_name_key, {})
        if display_name:
            result = display_names.get(room_type, display_name.get('default'))
        else:
            raise Exception(f'Get room property display name: Could not find a display name with the key \'{display_name_key}\'! Please contact the author about this.')
    return result


def __get_short_name(room_design_info: entity.EntityDesignInfo) -> str:
    room_short_name = room_design_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2)
    if room_short_name:
        result = room_short_name.split(':')[0]
        return result
    else:
        return ''


def __parse_value(value: str, max_decimal_count: int = settings.DEFAULT_FLOAT_PRECISION) -> str:
    if value and value.lower() != 'none':
        try:
            i = float(value)
            if i:
                return util.get_reduced_number_compact(i, max_decimal_count=max_decimal_count)
            else:
                return None
        except:
            pass

        return value
    else:
        return None










# ---------- Initilization ----------

rooms_designs_retriever: entity.EntityDesignsRetriever
rooms_designs_purchases_retriever: entity.EntityDesignsRetriever
rooms_designs_sprites_retriever: entity.EntityDesignsRetriever
__allowed_room_names: List[str]
__display_name_properties: Dict[str, entity.EntityDesignDetailProperty]
__properties: Dict[str, entity.EntityDesignDetailProperty]


async def init():
    global rooms_designs_retriever
    global rooms_designs_purchases_retriever
    global rooms_designs_sprites_retriever
    rooms_designs_retriever = entity.EntityDesignsRetriever(
        ROOM_DESIGN_BASE_PATH,
        ROOM_DESIGN_KEY_NAME,
        ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME,
        cache_name='RoomDesigns',
        sorted_key_function=_get_key_for_room_sort
    )
    rooms_designs_purchases_retriever = entity.EntityDesignsRetriever(
        ROOM_DESIGN_PURCHASE_BASE_PATH,
        ROOM_DESIGN_PURCHASE_KEY_NAME,
        ROOM_DESIGN_PURCHASE_DESCRIPTION_PROPERTY_NAME,
        cache_name='RoomDesignPurchases'
    )
    rooms_designs_sprites_retriever = entity.EntityDesignsRetriever(
        ROOM_DESIGN_SPRITES_BASE_PATH,
        ROOM_DESIGN_SPRITES_KEY_NAME,
        None,
        cache_name='RoomDesignSprites'
    )

    global __allowed_room_names
    rooms_designs_data = await rooms_designs_retriever.get_data_dict3()
    __allowed_room_names = sorted(__get_allowed_room_short_names(rooms_designs_data))

    global __display_name_properties
    __display_name_properties = __create_display_name_properties(__DISPLAY_NAMES)

    global __properties
    __properties = {
        'title': entity.EntityDesignDetailProperty('Room name', False, omit_if_none=False, transform_function=__get_room_name),
        'description': entity.EntityDesignDetailProperty('Description', False, omit_if_none=False, entity_property_name='RoomDescription'),
        'long': [
            entity.EntityDesignDetailProperty(__display_name_properties['category'], True, entity_property_name='CategoryType', transform_function=__get_value),
            entity.EntityDesignDetailProperty(__display_name_properties['type'], True, entity_property_name=ROOM_DESIGN_TYPE_PROPERTY_NAME, transform_function=__get_value),
            entity.EntityDesignDetailProperty(__display_name_properties['size'], True, transform_function=__get_size),
            entity.EntityDesignDetailProperty(__display_name_properties['max_power_used'], True, entity_property_name='MaxSystemPower', transform_function=__get_value),
            entity.EntityDesignDetailProperty(__display_name_properties['power_generated'], True, entity_property_name='MaxPowerGenerated', transform_function=__get_value),
            entity.EntityDesignDetailProperty(__display_name_properties['innate_armor'], True, transform_function=__get_innate_armor),
            entity.EntityDesignDetailProperty(__display_name_properties['enhanced_by'], True, entity_property_name='EnhancementType', transform_function=__get_value),
            entity.EntityDesignDetailProperty(__display_name_properties['min_hull_lvl'], True, entity_property_name='MinShipLevel', transform_function=__get_value),
            entity.EntityDesignDetailProperty(__display_name_properties['reload_speed'], True, transform_function=__get_reload_time),
            entity.EntityDesignDetailProperty(__display_name_properties['shots_fired'], True, transform_function=__get_shots_fired),
            entity.EntityDesignDetailProperty(__display_name_properties['system_dmg'], True, entity_property_name='MissileDesign.SystemDamage', transform_function=__get_damage, print_percent=False),
            entity.EntityDesignDetailProperty(__display_name_properties['shield_dmg'], True, entity_property_name='MissileDesign.ShieldDamage', transform_function=__get_damage, print_percent=False),
            entity.EntityDesignDetailProperty(__display_name_properties['crew_dmg'], True, entity_property_name='MissileDesign.CharacterDamage', transform_function=__get_damage, print_percent=False),
            entity.EntityDesignDetailProperty(__display_name_properties['hull_dmg'], True, entity_property_name='MissileDesign.HullDamage', transform_function=__get_damage, print_percent=False),
            entity.EntityDesignDetailProperty(__display_name_properties['ap_dmg'], True, entity_property_name='MissileDesign.DirectSystemDamage', transform_function=__get_damage, print_percent=False),
            entity.EntityDesignDetailProperty(__display_name_properties['emp_duration'], True, entity_property_name='MissileDesign.EMPLength', transform_function=__get_value_as_seconds),
            entity.EntityDesignDetailProperty(__display_name_properties['max_storage'], True, transform_function=__get_max_storage_and_type),
            entity.EntityDesignDetailProperty(__display_name_properties['cap_per_tick'], True, transform_function=__get_capacity_per_tick, allowed_room_types=CAPACITY_PER_TICK_UNITS.keys()),
            entity.EntityDesignDetailProperty(__display_name_properties['cooldown'], True, entity_property_name='CooldownTime', transform_function=__get_value_as_seconds),
            entity.EntityDesignDetailProperty(__display_name_properties['queue_limit'], True, transform_function=__get_queue_limit),
            entity.EntityDesignDetailProperty(__display_name_properties['manufacture_speed'], True, transform_function=__get_manufacture_rate),
            entity.EntityDesignDetailProperty(__display_name_properties['gas_per_crew'], True, entity_property_name='ManufactureRate', transform_function=__get_value, allowed_room_types=['Recycling']),
            entity.EntityDesignDetailProperty(__display_name_properties['max_crew_blend'], True, entity_property_name='ManufactureCapacity', transform_function=__get_value, allowed_room_types=['Recycling']),
            entity.EntityDesignDetailProperty(__display_name_properties['build_time'], True, entity_property_name='ConstructionTime', transform_function=__get_value_as_duration),
            entity.EntityDesignDetailProperty(__display_name_properties['build_cost'], True, transform_function=__get_build_cost),
            entity.EntityDesignDetailProperty(__display_name_properties['build_requirement'], True, transform_function=__get_build_requirement),
            entity.EntityDesignDetailProperty(__display_name_properties['grid_types'], True, transform_function=__get_is_allowed_in_extension_grids),
            entity.EntityDesignDetailProperty(__display_name_properties['more_info'], True, transform_function=__convert_room_flags),
            entity.EntityDesignDetailProperty(__display_name_properties['wikia'], True, transform_function=__get_wikia_link),
        ],
        'short': [
            entity.EntityDesignDetailProperty('Room Type', False, entity_property_name=ROOM_DESIGN_TYPE_PROPERTY_NAME, transform_function=__get_value),
            entity.EntityDesignDetailProperty('Enhanced by', True, entity_property_name='EnhancementType', transform_function=__get_value),
            entity.EntityDesignDetailProperty('Ship lvl', True, entity_property_name='MinShipLevel', transform_function=__get_value),
        ],
        'embed': {
            'icon_url': entity.EntityDesignDetailProperty('icon_url', False, entity_property_name='LogoSpriteId', transform_function=entity.get_download_sprite_link_by_property),
            'image_url': entity.EntityDesignDetailProperty('image_url', False, transform_function=__get_interior_sprite_url),
            'thumbnail_url': entity.EntityDesignDetailProperty('thumbnail_url', False, transform_function=__get_random_exterior_sprite_url)
        }
    }


def __create_display_name_properties(display_names: List[str]) -> Dict[str, entity.EntityDesignDetailProperty]:
    result = {key: __create_display_name_property(key, display_names) for key in display_names.keys()}
    return result


def __create_display_name_property(display_name_key: str, display_names: Dict[str, Dict[str, str]]) -> entity.EntityDesignDetailProperty:
    result = entity.EntityDesignDetailProperty(display_name_key, False, transform_function=__get_property_display_name, display_name_key=display_name_key, display_names=display_names)
    return result


def __get_allowed_room_short_names(rooms_designs_data: dict):
    result = []
    for room_design_data in rooms_designs_data.values():
        if room_design_data[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2]:
            room_short_name = room_design_data[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2].split(':')[0]
            if room_short_name not in result:
                result.append(room_short_name)
    return result
