import random
import re
from typing import Dict, Iterable, List, Optional, Tuple, Union

from discord import Embed
from discord.ext.commands import Context
from PIL import Image, ImageDraw

from . import pss_assert
from . import pss_core as core
from . import pss_entity as entity
from .pss_exception import NotFound
from . import pss_item as item
from . import pss_lookups as lookups
from . import pss_research as research
from . import pss_sprites as sprites
from . import settings
from .typehints import EntitiesData, EntityInfo
from . import utils


# ---------- Constants ----------

BIG_SET_THRESHOLD: int = 4

# RoomType: 'unit'
CAPACITY_PER_TICK_UNITS: Dict[str, str] = {
    'Lift': ' pixel/s',
    'Radar': 's',
    'Stealth': 's'
}

MISSILE_DESIGN_BASE_PATH: str = 'RoomService/ListMissileDesigns'
MISSILE_DESIGN_KEY_NAME: str = 'MissileDesignId'
MISSILE_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'MissileDesignName'

ROOM_DESIGN_BASE_PATH: str = 'RoomService/ListRoomDesigns2?languageKey=en'
ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'RoomName'
ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2: str = 'RoomShortName'
ROOM_DESIGN_KEY_NAME: str = 'RoomDesignId'
ROOM_DESIGN_TYPE_PROPERTY_NAME: str = 'RoomType'

ROOM_DESIGN_PURCHASE_BASE_PATH: str = 'RoomService/ListRoomDesignPurchase?languageKey=en'
ROOM_DESIGN_PURCHASE_DESCRIPTION_PROPERTY_NAME: str = 'RoomName'
ROOM_DESIGN_PURCHASE_KEY_NAME: str = 'RoomDesignPurchaseId'

ROOM_DESIGN_SPRITES_BASE_PATH: str = 'RoomDesignSpriteService/ListRoomDesignSprites'
ROOM_DESIGN_SPRITES_KEY_NAME: str = 'RoomDesignSpriteId'

RX_FIX_ROOM_NAME: re.Pattern = re.compile(r' [lL][vV][lL]?')
RX_NUMBER: re.Pattern = re.compile(r'\d+')


__AMMO_TYPE_OVERWRITES: Dict[str, str] = {
    'ION': 'Ion Cores',
}

__DISPLAY_NAMES: Dict[str, Dict[str, str]] = {
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
        'default': 'Innate armor'
    },
    'manufacture_speed': {
        'default': 'Manufacture speed'
    },
    'max_crew_blend': {
        'default': 'Max crew blend'
    },
    'max_power_used': {
        'default': 'Max power used'
    },
    'max_storage': {
        'default': 'Max storage',
        'Bedroom': 'Crew slots',
        'Bridge': 'Escape modifier',
        'Command': 'Max AI lines',
        'Council': 'Borrow limit',
        'Engine': 'Dodge modifier',
        'Medical': 'Crew HP healed',
        'Shield': 'Shield points',
        'Training': 'Training lvl',
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
        'Council': 'Donation limit',
        'Printer': 'Bux per day',
        'Shield': 'Restore on reload'
    },
    'reload_speed': {
        'default': 'Reload speed'
    },
    'required_item': {
        'default': 'Required item'
    },
    'required_research': {
        'default': 'Required research'
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
        'default': 'Wiki'
    },
}





# ---------- Room info ----------

def get_room_details_by_id(room_design_id: str, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData) -> entity.EntityDetails:
    if room_design_id and room_design_id in rooms_data:
        result = __create_room_details_from_info(rooms_data[room_design_id], rooms_data, items_data, researches_data, rooms_designs_sprites_data)
    else:
        result = None
    return result


async def get_room_details_by_name(room_name: str, ctx: Context = None, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(room_name, allowed_values=ALLOWED_ROOM_NAMES)

    rooms_data = await rooms_designs_retriever.get_data_dict3()
    rooms_designs_infos = get_room_infos_by_name(room_name, rooms_data)

    if not rooms_designs_infos:
        raise NotFound(f'Could not find a room named **{room_name}**.')
    else:
        items_data = await item.items_designs_retriever.get_data_dict3()
        researches_data = await research.researches_designs_retriever.get_data_dict3()
        rooms_designs_sprites_data = await rooms_designs_sprites_retriever.get_data_dict3()

        exact_match_details = None
        exact_room_info = None
        big_set_threshold = BIG_SET_THRESHOLD
        if len(rooms_designs_infos) >= big_set_threshold:
            lower_room_name = room_name.strip().lower()
            for room_design_info in rooms_designs_infos:
                if room_design_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME, '').lower() == lower_room_name:
                    exact_room_info = exact_room_info
                    break

        if exact_room_info:
            rooms_designs_infos = [room_design_info for room_design_info in rooms_designs_infos if room_design_info[ROOM_DESIGN_KEY_NAME] != exact_room_info[ROOM_DESIGN_KEY_NAME]]
            exact_match_details = __create_room_details_from_info(exact_room_info, rooms_data, items_data, researches_data, rooms_designs_sprites_data)
            big_set_threshold -= 1
        rooms_details_collection = __create_rooms_details_collection_from_infos(rooms_designs_infos, rooms_data, items_data, researches_data, rooms_designs_sprites_data)

        result = []
        if as_embed:
            if exact_match_details:
                result.append(await exact_match_details.get_details_as_embed(ctx))
            result.extend(await rooms_details_collection.get_entities_details_as_embed(ctx, big_set_threshold=big_set_threshold))
        else:
            if exact_match_details:
                result.extend(await exact_match_details.get_details_as_text(details_type=entity.EntityDetailsType.LONG))
                result.append(utils.discord.ZERO_WIDTH_SPACE)
            result.extend(await rooms_details_collection.get_entities_details_as_text(big_set_threshold=big_set_threshold))
        return result


def get_room_infos_by_name(room_name: str, rooms_data: EntitiesData) -> List[EntityInfo]:
    room_name_reverse = room_name[::-1]
    numbers_in_room_name = RX_NUMBER.findall(room_name_reverse)
    if numbers_in_room_name:
        level_in_room_name = numbers_in_room_name[0][::-1]
        room_level = int(level_in_room_name)
        room_name = re.sub(level_in_room_name, '', room_name, count=1)
    else:
        room_level = None

    room_design_ids = _get_room_design_ids_from_room_shortname(room_name, rooms_data, room_level)

    if not room_design_ids:
        room_design_ids = _get_room_design_ids_from_name(room_name, rooms_data)

    result = [rooms_data[room_design_id] for room_design_id in room_design_ids if room_design_id in rooms_data.keys()]
    if result and room_level and room_level > 0:
        result = [room_info for room_info in result if int(room_info.get('Level', '-1')) == room_level]
    result = sorted(result, key=lambda info: _get_key_for_room_sort(info, rooms_data))
    return result


def _get_room_design_ids_from_name(room_name: str, rooms_data: EntitiesData) -> List[str]:
    results = core.get_ids_from_property_value(rooms_data, ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME, room_name)
    return results


def _get_room_design_ids_from_room_shortname(room_short_name: str, rooms_data: EntitiesData, room_level: int = None) -> List[str]:
    match_exact = False
    if room_level and room_level > 0:
        room_short_name = f'{room_short_name}{room_level}'
        match_exact = True
    results = core.get_ids_from_property_value(rooms_data, ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2, room_short_name, match_exact=match_exact)
    return results


def _get_key_for_room_sort(room_info: EntityInfo, rooms_data: EntitiesData) -> str:
    parent_infos = __get_parents(room_info, rooms_data)
    result = room_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2)
    if result:
        result = result.split(':')[0]
    else:
        result = room_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME)[0:3]
    result.ljust(3)
    result += ''.join([parent_info[ROOM_DESIGN_KEY_NAME].zfill(4) for parent_info in parent_infos])
    return result





# ---------- Create entity.EntityDetails ----------

def __create_room_details_from_info(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(room_info, __properties['title'], __properties['description'], __properties['properties'], __properties['embed_settings'], rooms_data, items_data, researches_data, rooms_designs_sprites_data)


def __create_room_details_list_from_infos(rooms_designs_infos: List[EntityInfo], rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData) -> List[entity.EntityDetails]:
    return [__create_room_details_from_info(room_info, rooms_data, items_data, researches_data, rooms_designs_sprites_data) for room_info in rooms_designs_infos]


def __create_rooms_details_collection_from_infos(rooms_designs_infos: List[EntityInfo], rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData) -> entity.EntityDetailsCollection:
    rooms_details = __create_room_details_list_from_infos(rooms_designs_infos, rooms_data, items_data, researches_data, rooms_designs_sprites_data)
    result = entity.EntityDetailsCollection(rooms_details, big_set_threshold=4)
    return result





# ---------- Transformation functions ----------

def __convert_room_flags(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        flags = room_info.get('Flags')
        if entity.entity_property_has_value(flags):
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


def __get_build_cost(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        price_string = room_info.get('PriceString')
        if price_string:
            resource_type, amount = price_string.split(':')
            cost = utils.format.get_reduced_number_compact(amount)
            currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[resource_type.lower()]
            result = f'{cost} {currency_emoji}'
            return result
        else:
            return None
    else:
        return None


def __get_capacity_per_tick(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        room_type = room_info.get(ROOM_DESIGN_TYPE_PROPERTY_NAME)
        capacity = room_info.get('Capacity')
        if entity.entity_property_has_value(capacity) and room_type:
            cap_per_tick = utils.convert.ticks_to_seconds(int(capacity))
            result = f'{utils.format.number_up_to_decimals(cap_per_tick, 3)}{CAPACITY_PER_TICK_UNITS[room_type]}'
            return result
        else:
            return None
    else:
        return None


def __get_damage(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        dmg = kwargs.get('entity_property')
        print_percent = kwargs.get('print_percent')
        reload_time = room_info.get('ReloadTime')
        max_power = room_info.get('MaxSystemPower')
        volley = entity.get_property_from_entity_info(room_info, 'MissileDesign.Volley')
        volley_delay = entity.get_property_from_entity_info(room_info, 'MissileDesign.VolleyDelay')
        cooldown_time = room_info.get('CooldownTime')
        result = __get_dmg_for_dmg_type(dmg, reload_time, max_power, volley, volley_delay, cooldown_time, print_percent)
        return result
    else:
        return None


def __get_innate_armor(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        default_defense_bonus = room_info.get('DefaultDefenceBonus')
        if entity.entity_property_has_value(default_defense_bonus):
            reduction = (1.0 - 1.0 / (1.0 + (float(default_defense_bonus) / 100.0))) * 100
            result = f'{default_defense_bonus} ({utils.format.number_up_to_decimals(reduction, 2)}% dmg reduction)'
            return result
        else:
            return None
    else:
        return None


async def __get_interior_sprite_url(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    room_design_id = room_info.get(ROOM_DESIGN_KEY_NAME)
    if entity.entity_property_has_value(room_design_id):
        sprites_infos = [room_design_sprite_design for room_design_sprite_design in rooms_designs_sprites_data.values() if room_design_sprite_design.get(ROOM_DESIGN_KEY_NAME) == room_design_id]
        # if found, get a random SpriteId from a row with:
        #  - RoomSpriteType == 'Exterior'
        exterior_sprites_infos = [room_design_sprite_design for room_design_sprite_design in sprites_infos if room_design_sprite_design.get('RoomSpriteType').strip().lower() == 'interior']
        if exterior_sprites_infos:
            # Create an url with the SpriteId
            result = await sprites.get_download_sprite_link(exterior_sprites_infos[0].get('SpriteId'))
            return result
        else:
            return None
    else:
        return None


def __get_is_allowed_in_extension_grids(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        supported_grid_types = int(room_info.get('SupportedGridTypes', '0'))
        if (supported_grid_types & 2) != 0:
            return 'Allowed in extension grids'
        else:
            return None
    else:
        return None


def __get_manufacture_rate(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        manufacture_rate = room_info.get('ManufactureRate')
        if entity.entity_property_has_value(manufacture_rate):
            manufacture_rate = float(manufacture_rate)
            manufacture_speed = 1.0 / manufacture_rate
            manufacture_rate_per_hour = manufacture_rate * 3600
            result = f'{utils.format.number_up_to_decimals(manufacture_speed)}s ({utils.format.number_up_to_decimals(manufacture_rate_per_hour)}/hour)'
            return result
        else:
            return None
    else:
        return None


def __get_max_storage_and_type(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        capacity = room_info.get('Capacity')
        manufacture_capacity = room_info.get('ManufactureCapacity')
        manufacture_rate = room_info.get('ManufactureRate')
        manufacture_type = room_info.get('ManufactureType')
        room_type = room_info.get(ROOM_DESIGN_TYPE_PROPERTY_NAME)
        if entity.entity_property_has_value(capacity) and ((not entity.entity_property_has_value(manufacture_capacity) or not entity.entity_property_has_value(manufacture_rate)) or (room_type and room_type == 'Recycling')):
            value = __parse_value(capacity)
            if value and room_type and room_type == 'Medical':
                value = str(int(value) / 100)
        elif entity.entity_property_has_value(manufacture_capacity) and entity.entity_property_has_value(manufacture_rate):
            value = __parse_value(manufacture_capacity)
        else:
            value = None

        if value:
            print_type = (entity.entity_property_has_value(capacity) and not entity.entity_property_has_value(manufacture_rate)) or (entity.entity_property_has_value(manufacture_capacity) and entity.entity_property_has_value(manufacture_rate))
            if print_type:
                construction_type = ''
                if entity.entity_property_has_value(manufacture_type):
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


def __get_property_display_name(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    display_name_key = kwargs.get('display_name_key')
    display_names = kwargs.get('display_names')
    room_type = room_info.get(ROOM_DESIGN_TYPE_PROPERTY_NAME)
    result = None
    if display_name_key and room_type:
        display_name = display_names.get(display_name_key, {})
        if display_name:
            result = display_name.get(room_type, display_name.get('default'))
        else:
            raise Exception(f'Get room property display name: Could not find a display name with the key \'{display_name_key}\'! Please contact the author about this.')
    return result


def __get_queue_limit(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        manufacture_capacity = room_info.get('ManufactureCapacity')
        manufacture_rate = room_info.get('ManufactureRate')
        if entity.entity_property_has_value(manufacture_capacity) and not entity.entity_property_has_value(manufacture_rate):
            return __parse_value(manufacture_capacity)
        else:
            return None
    else:
        return None


def __get_queue_limit_float(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        manufacture_capacity = room_info.get('ManufactureCapacity')
        manufacture_rate = room_info.get('ManufactureRate')
        if entity.entity_property_has_value(manufacture_capacity) and not entity.entity_property_has_value(manufacture_rate):
            return __parse_value(str(float(manufacture_capacity) / 100.0))
        else:
            return None
    else:
        return None


async def __get_random_exterior_sprite_url(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    room_design_id = room_info.get(ROOM_DESIGN_KEY_NAME)
    if entity.entity_property_has_value(room_design_id):
        sprites_infos = [room_design_sprite_design for room_design_sprite_design in rooms_designs_sprites_data.values() if room_design_sprite_design.get(ROOM_DESIGN_KEY_NAME) == room_design_id]
        exterior_sprites_infos = [room_design_sprite_design for room_design_sprite_design in sprites_infos if room_design_sprite_design.get('RoomSpriteType').strip().lower() == 'exterior']
        if exterior_sprites_infos:
            room_design_sprite_info = exterior_sprites_infos[random.randint(0, len(exterior_sprites_infos) - 1)]
            result = await sprites.get_download_sprite_link(room_design_sprite_info.get('SpriteId'))
            return result
        else:
            return None
    else:
        return None


def __get_reload_time(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        reload_time = room_info.get('ReloadTime')
        if entity.entity_property_has_value(reload_time):
            reload_ticks = float(reload_time)
            reload_seconds = reload_ticks / 40.0
            cooldown_time = room_info.get('CooldownTime')
            cooldown_seconds = utils.convert.ticks_to_seconds(cooldown_time) if cooldown_time else 0
            reload_speed = 60.0 / (reload_seconds + cooldown_seconds)
            result = f'{utils.format.number_up_to_decimals(reload_seconds, 3)}s (~ {utils.format.number_up_to_decimals(reload_speed)}/min)'
            return result
        else:
            return None
    else:
        return None


async def __get_required_item(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        requirement_string = room_info.get('RequirementString')
        if requirement_string:
            required_type, required_id, required_amount = __get_required_details(requirement_string)

            if required_type == 'item':
                item_details = item.get_item_details_by_id(required_id, items_data, None)
                result = f'{required_amount}x ' + ''.join((await item_details.get_details_as_text(entity.EntityDetailsType.MINI)))
                return result
            elif required_type == 'research':
                return None
            else:
                return requirement_string
        else:
            return None
    else:
        return None


async def __get_required_research(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        requirement_string = room_info.get('RequirementString')
        if requirement_string:
            required_type, required_id, _ = __get_required_details(requirement_string)

            if required_type == 'item':
                return None
            elif required_type == 'research':
                research_details = research.get_research_details_by_id(required_id, researches_data, rooms_data)
                result = ''.join(await research_details.get_details_as_text(entity.EntityDetailsType.MINI))
                return result
            else:
                return requirement_string
        else:
            return None
    else:
        return None


def __get_room_name(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
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


def __get_room_name(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
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


def __get_shots_fired(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        volley = entity.get_property_from_entity_info(room_info, 'MissileDesign.Volley')
        volley_delay = entity.get_property_from_entity_info(room_info, 'MissileDesign.VolleyDelay')
        if entity.entity_property_has_value(volley) and volley != '1':
            volley = int(volley)
            volley_delay = int(volley_delay)
            volley_delay_seconds = utils.format.number_up_to_decimals(utils.convert.ticks_to_seconds(volley_delay), 3)
            result = f'{volley:d} (Delay: {volley_delay_seconds}s)'
            return result
        else:
            return None
    else:
        return None


def __get_size(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        columns = room_info.get('Columns')
        rows = room_info.get('Rows')
        if columns and rows:
            result = f'{columns}x{rows}'
            return result
        else:
            return None
    else:
        return None


def __get_value(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        value = kwargs.get('entity_property')
        if value:
            max_decimal_count = kwargs.get('max_decimal_count', utils.DEFAULT_FLOAT_PRECISION)
            result = __parse_value(value, max_decimal_count)
            return result
        else:
            return None
    else:
        return None


def __get_value_as_duration(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        value = kwargs.get('entity_property')
        if value:
            result = utils.format.duration(int(value), include_relative_indicator=False, exclude_zeros=True)
            return result
        else:
            return None
    else:
        return None


def __get_value_as_seconds(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        value = kwargs.get('entity_property')
        if value:
            value_seconds = utils.convert.ticks_to_seconds(int(value))
            result = f'{utils.format.number_up_to_decimals(value_seconds, 3)}s'
            return result
        else:
            return None
    else:
        return None


async def __get_wikia_link(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, researches_data: EntitiesData, rooms_designs_sprites_data: EntitiesData, **kwargs) -> Optional[str]:
    if __is_allowed_room_type(room_info, kwargs.get('allowed_room_types'), kwargs.get('forbidden_room_types')):
        return_plain = kwargs.get('return_plain')
        room_name = room_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME)
        if room_name:
            room_name = room_name.split(' Lv')[0]
            room_name = '_'.join([part.lower().capitalize() for part in room_name.split(' ')])
            result = await utils.get_wikia_link(room_name)
            if result:
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


def __is_allowed_room_type(room_info: EntityInfo, allowed_room_types: Iterable, forbidden_room_types) -> bool:
    room_type = room_info.get(ROOM_DESIGN_TYPE_PROPERTY_NAME)
    is_allowed = not allowed_room_types or room_type in allowed_room_types
    is_forbidden = forbidden_room_types and room_type in forbidden_room_types
    return is_allowed and not is_forbidden





# ---------- Helper functions ----------

def get_room_info_progression(room_info: EntityInfo, rooms_data: EntitiesData) -> List[EntityInfo]:
    root_room_info = get_root_room_info(room_info, rooms_data)
    result = sorted([room_info for room_info in rooms_data.values() if room_info['RootRoomDesignId'] == root_room_info[ROOM_DESIGN_KEY_NAME] and not entity.entity_property_has_value(room_info['RequirementString'])], key=lambda x: x[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME])
    return result


def get_room_search_details(room_info: EntityInfo) -> str:
    result = room_info[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME]
    return result


def get_rooms_per_level(room_design_id: str, rooms_purchases_data: EntitiesData, max_level: int = 12) -> Dict[int, int]:
    result = {i: 0 for i in range(1, max_level + 1)}
    new_rooms_per_level = {int(value['Level']): int(value['Quantity']) for value in rooms_purchases_data.values() if value.get('RoomDesignId') == room_design_id}
    total_room_count = 0
    for level in result.keys():
        total_room_count += new_rooms_per_level.get(level, 0)
        result[level] = total_room_count
    return result


def get_root_room_info(room_info: EntityInfo, rooms_data: EntitiesData) -> EntityInfo:
    result = rooms_data[room_info['RootRoomDesignId']]
    return result


def __create_display_name_properties(display_names: List[str]) -> Dict[str, entity.EntityDetailProperty]:
    result = {key: __create_display_name_property(key, display_names) for key in display_names.keys()}
    return result


def __create_display_name_property(display_name_key: str, display_names: Dict[str, Dict[str, str]]) -> entity.EntityDetailProperty:
    result = entity.EntityDetailProperty(display_name_key, False, transform_function=__get_property_display_name, display_name_key=display_name_key, display_names=display_names)
    return result


def __get_allowed_room_short_names(rooms_data: EntitiesData) -> List:
    result = []
    for room_design_data in rooms_data.values():
        if room_design_data[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2]:
            room_short_name = room_design_data[ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2].split(':')[0]
            if room_short_name not in result:
                result.append(room_short_name)
    return result


def __get_dmg_for_dmg_type(dmg: str, reload_time: str, max_power: str, volley: str, volley_delay: str, cooldown_time: str, print_percent: bool) -> Optional[str]:
    """Returns base dps and dps per power"""
    if dmg:
        dmg = float(dmg)
        reload_time = int(reload_time)
        reload_seconds = utils.convert.ticks_to_seconds(reload_time)
        cooldown_time = int(cooldown_time) if cooldown_time else 0
        reload_seconds += utils.convert.ticks_to_seconds(cooldown_time)
        max_power = int(max_power)
        volley = int(volley)
        if volley_delay:
            volley_delay = int(volley_delay)
        else:
            volley_delay = 0
        volley_duration_seconds = utils.convert.ticks_to_seconds((volley - 1) * volley_delay)
        reload_seconds += volley_duration_seconds
        full_volley_dmg = dmg * float(volley)
        dps = full_volley_dmg / reload_seconds
        dps_per_power = dps / max_power
        if print_percent:
            percent = '%'
        else:
            percent = ''
        if volley > 1:
            single_volley_dmg = f'per shot: {utils.format.number_up_to_decimals(dmg, 2)}, '
        else:
            single_volley_dmg = ''
        full_volley_dmg = utils.format.number_up_to_decimals(full_volley_dmg, 2)
        dps = utils.format.number_up_to_decimals(dps, 3)
        dps_per_power = utils.format.number_up_to_decimals(dps_per_power, 3)
        result = f'{full_volley_dmg}{percent} ({single_volley_dmg}dps: {dps}{percent})'
        return result
    else:
        return None


def __get_parents(room_info: EntityInfo, rooms_data: EntitiesData) -> List[EntityInfo]:
    parent_room_design_id = room_info['UpgradeFromRoomDesignId']
    if parent_room_design_id == '0':
        parent_room_design_id = None

    if parent_room_design_id is not None:
        parent_info = rooms_data[parent_room_design_id]
        result = __get_parents(parent_info, rooms_data)
        result.append(parent_info)
        return result
    else:
        return []


def __get_manufacture_type(room_info: EntityInfo) -> Optional[str]:
    short_name = __get_short_name(room_info)
    result = __AMMO_TYPE_OVERWRITES.get(short_name.upper(), room_info.get('ManufactureType'))
    return result


def __get_min_ship_lvl_display_name(room_info: EntityInfo, rooms_data: EntitiesData, items_data: EntitiesData, **kwargs) -> Optional[str]:
    display_name_key = kwargs.get('display_name_key')
    display_names = kwargs.get('entity_property')
    room_type = room_info.get(ROOM_DESIGN_TYPE_PROPERTY_NAME)
    result = None
    if display_name_key and room_type:
        display_name = display_names.get(display_name_key, {})
        if display_name:
            result = display_names.get(room_type, display_name.get('default'))
        else:
            raise Exception(f'Get room property display name: Could not find a display name with the key \'{display_name_key}\'! Please contact the author about this.')
    return result


def __get_required_details(requirement_string: str) -> Tuple[str, str, str]:
    required_type, required_id, required_amount, required_modifier = utils.parse.entity_string(requirement_string)
    return required_type, required_id, required_amount


def __get_short_name(room_info: EntityInfo) -> str:
    room_short_name = room_info.get(ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME_2)
    if room_short_name:
        result = room_short_name.split(':')[0]
        return result
    else:
        return ''


def __parse_value(value: str, max_decimal_count: int = utils.DEFAULT_FLOAT_PRECISION) -> Optional[str]:
    if value and value.lower() != 'none':
        try:
            f = float(value)
            if f:
                return utils.format.get_reduced_number_compact(f, max_decimal_count=max_decimal_count)
            else:
                return None
        except:
            pass

        return value
    else:
        return None




# ---------- Sprite Helper Functions ----------


async def create_room_sprite(room_sprite_id: str, room_decoration_sprite: Image.Image, room_design_info: entity.EntityInfo, brightness_value: float, hue_value: float, saturation_value: float) -> Image.Image:
    result = await sprites.load_sprite(room_sprite_id)
    room_sprite_draw: ImageDraw.ImageDraw = ImageDraw.Draw(result)
    if not room_decoration_sprite:
        result = sprites.enhance_sprite(result, brightness=brightness_value, hue=hue_value, saturation=saturation_value)
    else:
        room_decoration_sprite = sprites.enhance_sprite(room_decoration_sprite, brightness=brightness_value, hue=hue_value, saturation=saturation_value)
        result.paste(room_decoration_sprite, (0, 0), room_decoration_sprite)
        logo_sprite_id = room_design_info.get('LogoSpriteId')
        if entity.entity_property_has_value(logo_sprite_id):
            logo_sprite = await sprites.load_sprite(logo_sprite_id)
            result.paste(logo_sprite, (1, 2), logo_sprite)
        power_bars_count = None
        max_system_power = room_design_info.get('MaxSystemPower')
        if entity.entity_property_has_value(max_system_power):
            power_bars_count = int(max_system_power) or None
        else:
            max_power_generated = room_design_info.get('MaxPowerGenerated')
            if entity.entity_property_has_value(max_power_generated):
                power_bars_count = int(max_power_generated) or None
        if power_bars_count:
            draw_power_bars_on_room_sprite(result, power_bars_count)

        room_short_name = room_design_info.get('RoomShortName')
        if entity.entity_property_has_value(room_short_name):
            short_name_x = 12
            short_name_y = 0
            room_sprite_draw.text((short_name_x, short_name_y), room_short_name, fill=(255, 255, 255), font=sprites.PIXELATED_FONT)
    return result


def draw_power_bars_on_room_sprite(room_sprite: Image.Image, power_count: int) -> None:
    room_sprite_draw = ImageDraw.Draw(room_sprite)
    power_bar_x_start = room_sprite.width - sprites.POWER_BAR_WIDTH - 1
    power_bar_y_end = sprites.POWER_BAR_Y_START + sprites.POWER_BAR_HEIGHT - 1
    for _ in range(power_count):
        power_bar_x_end = power_bar_x_start + sprites.POWER_BAR_WIDTH - 2
        coordinates = [power_bar_x_start, sprites.POWER_BAR_Y_START, power_bar_x_end, power_bar_y_end]
        room_sprite_draw.rectangle(coordinates, sprites.POWER_BAR_COLOR, sprites.POWER_BAR_COLOR)
        power_bar_x_start -= sprites.POWER_BAR_WIDTH + sprites.POWER_BAR_SPACING - 1


def fit_door_frame_to_room_height(door_frame_sprite: Image.Image, room_height: int) -> Image.Image:
    first_row = door_frame_sprite.crop((0, 0, door_frame_sprite.width, 1))
    top_part = first_row.resize((door_frame_sprite.width, (room_height - 2) * sprites.TILE_SIZE))

    result = sprites.create_empty_sprite(door_frame_sprite.width, door_frame_sprite.height + top_part.height)
    result.paste(top_part, (0, 0))
    result.paste(door_frame_sprite, (0, top_part.height), door_frame_sprite)
    return result


async def get_room_decoration_sprite(room_frame_sprite_id: str, door_frame_left_sprite_id: str, door_frame_right_sprite_id: str, room_width: int, room_height: int) -> Image.Image:
    result = await sprites.load_sprite_from_disk(room_frame_sprite_id, suffix=f'{door_frame_left_sprite_id}_{door_frame_right_sprite_id}_{room_width}x{room_height}')
    if not result:
        result = await make_room_decoration_sprite(room_frame_sprite_id, door_frame_left_sprite_id, door_frame_right_sprite_id, room_width, room_height)
    return result


def get_room_sprite_id(room_design_info: entity.EntityInfo, under_construction: bool, has_decoration_sprite: bool, rooms_designs_sprites_ids: Dict[str, str]) -> str:
    if under_construction:
        result = room_design_info['ConstructionSpriteId']
    else:
        if has_decoration_sprite:
            result = room_design_info['ImageSpriteId']
        else:
            result = rooms_designs_sprites_ids.get(room_design_info[ROOM_DESIGN_KEY_NAME], room_design_info['ImageSpriteId'])
    return result


async def make_door_frame_sprite(door_frame_left_sprite_id: str, door_frame_right_sprite_id: str, room_height: int) -> Image.Image:
    door_frame_left_sprite = await sprites.load_sprite(door_frame_left_sprite_id)
    door_frame_right_sprite = await sprites.load_sprite(door_frame_right_sprite_id)
    width = door_frame_left_sprite.width + door_frame_right_sprite.width - 2

    result = sprites.create_empty_sprite(width, door_frame_left_sprite.height)
    result.paste(door_frame_right_sprite, (2, 0), door_frame_right_sprite)
    result.paste(door_frame_left_sprite, (0, 0), door_frame_left_sprite)

    if room_height > 2:
        result = fit_door_frame_to_room_height(result, room_height)
    sprites.save_sprite(result, f'door_frame_{door_frame_left_sprite_id}_{door_frame_right_sprite_id}_{room_height}')
    return result


async def make_room_decoration_sprite(room_frame_sprite_id: str, door_frame_left_sprite_id: str, door_frame_right_sprite_id: str, room_width: int, room_height: int) -> Image.Image:
    if room_width == 3 and room_height == 2:
        room_frame_sprite = await sprites.load_sprite(room_frame_sprite_id)
    else: # edit frame sprite
        room_frame_sprite = await sprites.load_sprite_from_disk(room_frame_sprite_id, suffix=f'{room_width}x{room_height}')
        if not room_frame_sprite:
            room_frame_sprite = await make_room_frame_sprite(room_frame_sprite_id, room_width, room_height)

    door_frame_sprite = await sprites.load_sprite_from_disk(door_frame_left_sprite_id, prefix='door_frame', suffix=f'{door_frame_right_sprite_id}_{room_height}')
    if not door_frame_sprite:
        door_frame_sprite = await make_door_frame_sprite(door_frame_left_sprite_id, door_frame_right_sprite_id, room_height)

    room_decoration_sprite = room_frame_sprite.copy()
    door_frame_y = room_frame_sprite.height - door_frame_sprite.height - 1
    room_decoration_sprite.paste(door_frame_sprite, (1, door_frame_y), door_frame_sprite)
    room_decoration_sprite.paste(room_frame_sprite, (0, 0), room_frame_sprite)

    sprites.save_sprite(room_decoration_sprite, f'{room_frame_sprite_id}_{door_frame_left_sprite_id}_{door_frame_right_sprite_id}_{room_width}x{room_height}')
    return room_decoration_sprite


async def make_room_frame_sprite(room_frame_sprite_id: str, room_width: int, room_height: int) -> Image.Image:
    room_frame_sprite = await sprites.load_sprite(room_frame_sprite_id)
    result = sprites.create_empty_room_sprite(room_width, room_height)
    from_left = sprites.TILE_SIZE // 2 # 12
    from_right = sprites.TILE_SIZE - from_left # 13

    upper_left_region_sprite = room_frame_sprite.crop((
        0,
        0,
        from_left,
        from_left
    ))
    upper_right_region_sprite = room_frame_sprite.crop((
        room_frame_sprite.width - from_right,
        0,
        room_frame_sprite.width,
        from_left
    ))
    bottom_left_region_sprite = room_frame_sprite.crop((
        0,
        room_frame_sprite.height - from_right,
        from_left,
        room_frame_sprite.height
    ))
    bottom_right_region_sprite = room_frame_sprite.crop((
        room_frame_sprite.width - from_right,
        room_frame_sprite.height - from_right,
        room_frame_sprite.width,
        room_frame_sprite.height
    ))

    top_center_region_sprite = room_frame_sprite.crop((
        from_left + 1,
        0,
        from_left + 1 + sprites.TILE_SIZE,
        from_left
    ))
    bottom_center_region_sprite = room_frame_sprite.crop((
        from_left + 1,
        room_frame_sprite.height - from_right,
        from_left + 1 + sprites.TILE_SIZE,
        room_frame_sprite.height
    ))
    left_center_region_sprite = room_frame_sprite.crop((
        0,
        from_left + 1,
        from_left,
        from_left + 1 + sprites.TILE_SIZE
    ))
    right_center_region_sprite = room_frame_sprite.crop((
        room_frame_sprite.width - from_right,
        from_left + 1,
        room_frame_sprite.width,
        from_left + 1 + sprites.TILE_SIZE
    ))

    result.paste(upper_left_region_sprite, (0, 0), upper_left_region_sprite)
    result.paste(upper_right_region_sprite, (result.width - from_left - 1, 0), upper_right_region_sprite)
    result.paste(bottom_left_region_sprite, (0, result.height - from_left - 1), bottom_left_region_sprite)
    result.paste(bottom_right_region_sprite, (result.width - from_left - 1, result.height - from_left - 1), bottom_right_region_sprite)
    for x in range(1, room_width):
        result.paste(top_center_region_sprite, (
            from_left + (x - 1) * sprites.TILE_SIZE,
            0
        ), top_center_region_sprite)
        result.paste(bottom_center_region_sprite, (
            from_left + (x - 1) * sprites.TILE_SIZE,
            result.height - from_right
        ), bottom_center_region_sprite)
    for y in range(1, room_height):
        result.paste(left_center_region_sprite, (
            0,
            from_left + (y - 1) * sprites.TILE_SIZE
        ))
        result.paste(right_center_region_sprite, (
            result.width - from_right,
            from_left + (y - 1) * sprites.TILE_SIZE
        ))
    return result





# ---------- Initilization ----------

missiles_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    MISSILE_DESIGN_BASE_PATH,
    MISSILE_DESIGN_KEY_NAME,
    MISSILE_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='MissileDesignSprites'
)
rooms_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    ROOM_DESIGN_BASE_PATH,
    ROOM_DESIGN_KEY_NAME,
    ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='RoomDesigns',
    sorted_key_function=_get_key_for_room_sort
)
rooms_designs_purchases_retriever: entity.EntityRetriever = entity.EntityRetriever(
    ROOM_DESIGN_PURCHASE_BASE_PATH,
    ROOM_DESIGN_PURCHASE_KEY_NAME,
    ROOM_DESIGN_PURCHASE_DESCRIPTION_PROPERTY_NAME,
    cache_name='RoomDesignPurchases'
)
rooms_designs_sprites_retriever: entity.EntityRetriever = entity.EntityRetriever(
    ROOM_DESIGN_SPRITES_BASE_PATH,
    ROOM_DESIGN_SPRITES_KEY_NAME,
    None,
    cache_name='RoomDesignSprites'
)
ALLOWED_ROOM_NAMES: List[str]
__display_name_properties: Dict[str, entity.EntityDetailProperty]  = __create_display_name_properties(__DISPLAY_NAMES)
__properties: entity.EntityDetailsCreationPropertiesCollection = {
    'title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Room name', False, omit_if_none=False, transform_function=__get_room_name)
    ),
    'description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='RoomDescription'),
        property_short=entity.NO_PROPERTY
    ),
    'properties': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty(__display_name_properties['category'], True, entity_property_name='CategoryType', transform_function=__get_value),
            entity.EntityDetailProperty(__display_name_properties['type'], True, entity_property_name=ROOM_DESIGN_TYPE_PROPERTY_NAME, transform_function=__get_value),
            entity.EntityDetailProperty(__display_name_properties['size'], True, transform_function=__get_size),
            entity.EntityDetailProperty(__display_name_properties['max_power_used'], True, entity_property_name='MaxSystemPower', transform_function=__get_value),
            entity.EntityDetailProperty(__display_name_properties['power_generated'], True, entity_property_name='MaxPowerGenerated', transform_function=__get_value),
            entity.EntityDetailProperty(__display_name_properties['innate_armor'], True, transform_function=__get_innate_armor, forbidden_room_types=['Corridor']),
            entity.EntityDetailProperty(__display_name_properties['enhanced_by'], True, entity_property_name='EnhancementType', transform_function=__get_value),
            entity.EntityDetailProperty(__display_name_properties['min_hull_lvl'], True, entity_property_name='MinShipLevel', transform_function=__get_value),
            entity.EntityDetailProperty(__display_name_properties['reload_speed'], True, transform_function=__get_reload_time),
            entity.EntityDetailProperty(__display_name_properties['cooldown'], True, entity_property_name='CooldownTime', transform_function=__get_value_as_seconds),
            entity.EntityDetailProperty(__display_name_properties['shots_fired'], True, transform_function=__get_shots_fired),
            entity.EntityDetailProperty(__display_name_properties['system_dmg'], True, entity_property_name='MissileDesign.SystemDamage', transform_function=__get_damage, print_percent=False),
            entity.EntityDetailProperty(__display_name_properties['shield_dmg'], True, entity_property_name='MissileDesign.ShieldDamage', transform_function=__get_damage, print_percent=False),
            entity.EntityDetailProperty(__display_name_properties['crew_dmg'], True, entity_property_name='MissileDesign.CharacterDamage', transform_function=__get_damage, print_percent=False),
            entity.EntityDetailProperty(__display_name_properties['hull_dmg'], True, entity_property_name='MissileDesign.HullDamage', transform_function=__get_damage, print_percent=False),
            entity.EntityDetailProperty(__display_name_properties['ap_dmg'], True, entity_property_name='MissileDesign.DirectSystemDamage', transform_function=__get_damage, print_percent=False),
            entity.EntityDetailProperty(__display_name_properties['emp_duration'], True, entity_property_name='MissileDesign.EMPLength', transform_function=__get_value_as_seconds),
            entity.EntityDetailProperty(__display_name_properties['max_storage'], True, transform_function=__get_max_storage_and_type, forbidden_room_types=['Anticraft', 'Corridor', 'Lift', 'Radar', 'Reactor', 'Stealth', 'Training']),
            entity.EntityDetailProperty(__display_name_properties['cap_per_tick'], True, transform_function=__get_capacity_per_tick, allowed_room_types=CAPACITY_PER_TICK_UNITS.keys()),
            entity.EntityDetailProperty(__display_name_properties['queue_limit'], True, transform_function=__get_queue_limit_float, allowed_room_types=['Shield']),
            entity.EntityDetailProperty(__display_name_properties['queue_limit'], True, transform_function=__get_queue_limit, forbidden_room_types=['Shield']),
            entity.EntityDetailProperty(__display_name_properties['manufacture_speed'], True, transform_function=__get_manufacture_rate, forbidden_room_types=['Recycling']),
            entity.EntityDetailProperty(__display_name_properties['gas_per_crew'], True, entity_property_name='ManufactureRate', transform_function=__get_value, allowed_room_types=['Recycling']),
            entity.EntityDetailProperty(__display_name_properties['max_crew_blend'], True, entity_property_name='ManufactureCapacity', transform_function=__get_value, allowed_room_types=['Recycling']),
            entity.EntityDetailProperty(__display_name_properties['build_time'], True, entity_property_name='ConstructionTime', transform_function=__get_value_as_duration),
            entity.EntityDetailProperty(__display_name_properties['build_cost'], True, transform_function=__get_build_cost),
            entity.EntityDetailProperty(__display_name_properties['required_research'], True, transform_function=__get_required_research),
            entity.EntityDetailProperty(__display_name_properties['required_item'], True, transform_function=__get_required_item),
            entity.EntityDetailProperty(__display_name_properties['grid_types'], True, transform_function=__get_is_allowed_in_extension_grids),
            entity.EntityDetailProperty(__display_name_properties['more_info'], True, transform_function=__convert_room_flags),
            entity.EntityDetailProperty(__display_name_properties['wikia'], True, transform_function=__get_wikia_link),
        ],
        properties_medium=[
            entity.EntityDetailProperty('Room Type', False, entity_property_name=ROOM_DESIGN_TYPE_PROPERTY_NAME, transform_function=__get_value),
            entity.EntityDetailProperty('Enhanced by', True, entity_property_name='EnhancementType', transform_function=__get_value),
            entity.EntityDetailProperty('Ship lvl', True, entity_property_name='MinShipLevel', transform_function=__get_value),
        ]
    ),
    'embed_settings': {
        'icon_url': entity.EntityDetailProperty('icon_url', False, entity_property_name='LogoSpriteId', transform_function=sprites.get_download_sprite_link_by_property),
        'image_url': entity.EntityDetailProperty('image_url', False, transform_function=__get_interior_sprite_url),
        'thumbnail_url': entity.EntityDetailProperty('thumbnail_url', False, transform_function=__get_random_exterior_sprite_url)
    }
}


async def init() -> None:
    global ALLOWED_ROOM_NAMES
    rooms_data = await rooms_designs_retriever.get_data_dict3()
    ALLOWED_ROOM_NAMES = sorted(__get_allowed_room_short_names(rooms_data))