#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import math
import os

from cache import PssCache
import emojis
import pss_assert
import pss_core as core
import pss_lookups as lookups
import settings
import utility as util


# ---------- Constants ----------

CHARACTER_DESIGN_BASE_PATH = 'CharacterService/ListAllCharacterDesigns2?languageKey=en'
CHARACTER_DESIGN_KEY_NAME = 'CharacterDesignId'
CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME = 'CharacterDesignName'

COLLECTION_DESIGN_BASE_PATH = 'CollectionService/ListAllCollectionDesigns?languageKey=en'
COLLECTION_DESIGN_KEY_NAME = 'CollectionDesignId'
COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME = 'CollectionName'

__PRESTIGE_FROM_BASE_PATH = f'CharacterService/PrestigeCharacterFrom?languagekey=en&characterDesignId='
__PRESTIGE_TO_BASE_PATH = f'CharacterService/PrestigeCharacterTo?languagekey=en&characterDesignId='



# ---------- Initilization ----------

__character_designs_cache = PssCache(
    CHARACTER_DESIGN_BASE_PATH,
    'CharacterDesigns',
    CHARACTER_DESIGN_KEY_NAME)

__collection_designs_cache = PssCache(
    COLLECTION_DESIGN_BASE_PATH,
    'CollectionDesigns',
    COLLECTION_DESIGN_KEY_NAME)

__prestige_from_cache_dict = {}
__prestige_to_cache_dict = {}





# ---------- Helper functions ----------

def get_ability_name(char_info: dict) -> str:
    if char_info:
        special = char_info['SpecialAbilityType']
        if special in lookups.SPECIAL_ABILITIES_LOOKUP.keys():
            return lookups.SPECIAL_ABILITIES_LOOKUP[special]
    return 'None'


def get_collection_name(char_info: dict, collection_designs_data: dict = None) -> str:
    if char_info:
        if not collection_designs_data:
            collection_designs_data = __collection_designs_cache.get_data_dict3()

        collection_id = char_info[COLLECTION_DESIGN_KEY_NAME]
        if collection_id and collection_id in collection_designs_data.keys():
            return collection_designs_data[collection_id][COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME]
    return 'None'


def _get_stat(stat_name: str, level: int, char_info: dict) -> str:
    is_special_stat = stat_name.lower().startswith('specialability')
    if is_special_stat:
        max_stat_name = 'SpecialAbilityFinalArgument'
    else:
        max_stat_name = f'Final{stat_name}'
    min_value = float(char_info[stat_name])
    max_value = float(char_info[max_stat_name])
    progression_type = char_info['ProgressionType']
    result = _get_stat_value(min_value, max_value, level, progression_type)
    return result


def _get_stat_value(min_value: float, max_value: float, level: int, progression_type: str) -> str:
    if level is None or level < 1 or level > 40:
        return f'{min_value:0.1f} - {max_value:0.1f}'
    else:
        return f'{calculate_stat_value(min_value, max_value, level, progression_type):0.1f}'


def calculate_stat_value(min_value: float, max_value: float, level: int, progression_type: str) -> float:
    exponent = lookups.PROGRESSION_TYPES[progression_type]
    result = min_value + (max_value - min_value) * ((level - 1) / 39) ** exponent
    return result





# ---------- Crew info ----------

def get_char_details_from_name(char_name: str, level: int, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(char_name, 'char_name')
    pss_assert.parameter_is_valid_integer(level, 'level', min_value=1, max_value=40, allow_none=True)

    char_info = _get_char_info(char_name)

    if char_info is None:
        return [f'Could not find a crew named **{char_name}**.'], False
    else:
        if as_embed:
            return _get_char_info_as_embed(char_info, level), True
        else:
            return _get_char_info_as_text(char_info, level), True



def _get_char_info(char_name: str) -> dict:
    char_design_data = __character_designs_cache.get_data_dict3()
    char_design_id = _get_char_design_id_from_name(char_name, char_design_data)

    if char_design_id and char_design_id in char_design_data.keys():
        return char_design_data[char_design_id]
    else:
        return None


def _get_char_design_id_from_name(char_name: str, char_data: dict = None) -> str:
    if char_data is None:
        char_data = __character_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(char_data, CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME, char_name)
    if len(results) > 0:
        return results[0]

    return None


def _get_char_info_as_embed(char_info: dict, level: int):
    return ''


def _get_char_info_as_text(char_info: dict, level: int, collection_designs_data: dict = None) -> list:
    if not collection_designs_data:
        collection_designs_data = __collection_designs_cache.get_data_dict3()

    char_name = char_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
    special = get_ability_name(char_info)
    equipment_slots = _convert_equipment_mask(int(char_info['EquipmentMask']))
    collection_name = get_collection_name(char_info, collection_designs_data)
    ability_stat = _get_stat('SpecialAbilityArgument', level, char_info)
    hp_stat = _get_stat('Hp', level, char_info)
    attack_stat = _get_stat('Attack', level, char_info)
    repair_stat = _get_stat('Repair', level, char_info)
    pilot_stat = _get_stat('Pilot', level, char_info)
    science_stat = _get_stat('Science', level, char_info)
    weapon_stat = _get_stat('Weapon', level, char_info)
    engine_stat = _get_stat('Engine', level, char_info)
    level_text = ''
    if level is not None:
        level_text = f' - lvl {level}'

    result = [f'**{char_name}** ({char_info["Rarity"]}){level_text}']
    result.append(char_info['CharacterDesignDescription'])
    result.append(f'Race: {char_info["RaceType"]}, Collection: {collection_name}, Gender: {char_info["GenderType"]}')
    result.append(f'Ability = {ability_stat} ({special})')
    result.append(f'HP = {hp_stat}')
    result.append(f'Attack = {attack_stat}')
    result.append(f'Repair = {repair_stat}')
    result.append(f'Pilot = {pilot_stat}')
    result.append(f'Science = {science_stat}')
    result.append(f'Engine = {engine_stat}')
    result.append(f'Weapon = {weapon_stat}')
    result.append(f'Walk/run speed = {char_info["WalkingSpeed"]}/{char_info["RunSpeed"]}')
    result.append(f'Fire resist = {char_info["FireResistance"]}')
    result.append(f'Training cap = {char_info["TrainingCapacity"]}')
    result.append(f'Slots = {equipment_slots}')

    return result


def _convert_equipment_mask(eqpt_mask: int) -> str:
    result = []
    for k in lookups.EQUIPMENT_MASK_LOOKUP.keys():
        if (eqpt_mask & k) != 0:
            result.append(lookups.EQUIPMENT_MASK_LOOKUP[k])

    if result:
        return ', '.join(result)
    else:
        return None


def _get_char_list() -> list:
    char_data = __character_designs_cache.get_data_dict3()
    result = [char_data[key][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME] for key in char_data.keys()]
    return result


def get_char_info_short_from_id_as_text(char_design_id: dict, char_designs_data: dict = None, collection_designs_data: dict = None) -> list:
    if not char_designs_data:
        char_designs_data = __character_designs_cache.get_data_dict3()
    if not collection_designs_data:
        collection_designs_data = __collection_designs_cache.get_data_dict3()

    char_info = char_designs_data[char_design_id]
    return get_char_info_short_from_data_as_text(char_info, collection_designs_data)


def get_char_info_short_from_data_as_text(char_info: dict, collection_designs_data: dict = None) -> list:
    if not collection_designs_data:
        collection_designs_data = __collection_designs_cache.get_data_dict3()

    name = char_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
    rarity = char_info['Rarity']
    collection = get_collection_name(char_info, collection_designs_data)
    ability = get_ability_name(char_info)
    ability_stat = int(char_info['SpecialAbilityFinalArgument'])
    ability_txt = ability
    if ability_stat:
        ability_txt = f'{ability} ({ability_stat})'
    result = [f'{name} (_{rarity}_ - Ability: _{ability_txt}_ - Collection: _{collection}_)']
    return result





# ---------- Collection Info ----------

def get_collection_info(collection_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(collection_name)

    collection_info = _get_collection_info(collection_name)

    if collection_info is None:
        return [f'Could not find a collection named **{collection_name}**.'], False
    else:
        if as_embed:
            return _get_collection_info_as_embed(collection_info), True
        else:
            return _get_collection_info_as_text(collection_info), True


def _get_collection_info(collection_name: str):
    collection_data = __collection_designs_cache.get_data_dict3()
    collection_design_id = _get_collection_design_id_from_name(collection_name, collection_data)

    if collection_design_id and collection_design_id in collection_data.keys():
        return collection_data[collection_design_id]
    else:
        return None


def _get_collection_design_id_from_name(collection_name: str, collection_data: dict = None):
    if collection_data is None:
        collection_data = __collection_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(collection_data, COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME, collection_name)
    if len(results) > 0:
        return results[0]

    return None


def _get_collection_info_as_embed(collection_info: dict):
    # Use collection_info['ColorString'] for embed color
    return []


def _get_collection_info_as_text(collection_info: dict):
    collection_crew = _get_collection_crew(collection_info)
    collection_perk = collection_info['EnhancementType']
    if collection_perk in lookups.COLLECTION_PERK_LOOKUP.keys():
        collection_perk = lookups.COLLECTION_PERK_LOOKUP[collection_perk]

    lines = []
    lines.append(f'**{collection_info[COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME]}**')
    lines.append(f'{collection_info["CollectionDescription"]}')
    lines.append(f'Combo Min...Max: {collection_info["MinCombo"]}...{collection_info["MaxCombo"]}')
    lines.append(f'{collection_perk}: {collection_info["BaseEnhancementValue"]} (Base), {collection_info["StepEnhancementValue"]} (Step)')
    lines.append(f'Characters: {", ".join(collection_crew)}')

    return lines


def _get_collection_crew(collection_info):
    #util.dbg_prnt(f'+ _get_collection_crew(collection_info[{collection_info[COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME]}])')
    collection_id = collection_info[COLLECTION_DESIGN_KEY_NAME]
    char_data = __character_designs_cache.get_data_dict3()
    char_infos = [char_data[char_id] for char_id in char_data.keys() if char_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = [char_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME] for char_info in char_infos]
    result.sort()
    return result


def fix_collection_name(collection_name):
    result = collection_name.lower()
    return result





# ---------- Prestige Info ----------

def get_prestige_from_info(char_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(char_name)

    prestige_data = _get_prestige_from_data(char_name)

    if prestige_data is None:
        return [f'Could not find prestige paths requiring **{char_name}**'], False
    else:
        if as_embed:
            return get_prestige_from_info_as_embed(char_name, prestige_data), True
        else:
            return get_prestige_from_info_as_txt(char_name, prestige_data), True


def get_prestige_to_info(char_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(char_name)

    prestige_data = _get_prestige_to_data(char_name)

    if prestige_data is None:
        return [f'Could not find prestige paths leading to **{char_name}**'], False
    else:
        if as_embed:
            return get_prestige_to_info_as_embed(char_name, prestige_data), True
        else:
            return get_prestige_to_info_as_txt(char_name, prestige_data), True


def get_prestige_from_info_as_embed(char_name: str, prestige_from_data: dict):
    return ''


def get_prestige_from_info_as_txt(char_name: str, prestige_from_data: dict) -> list:
    # Format: '+ {id2} = {toid}
    char_data = __character_designs_cache.get_data_dict3()
    char_info_1 = _get_char_info(char_name)
    found_char_name = char_info_1[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]

    lines = [f'**There are {len(prestige_from_data)} ways to prestige {found_char_name} into:**']

    prestige_infos = []
    for value in prestige_from_data.values():
        char_info_2_name = char_data[value['CharacterDesignId2']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
        char_info_to_name = char_data[value['ToCharacterDesignId']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
        prestige_infos.append((char_info_2_name, char_info_to_name))

    body_lines = []
    if prestige_infos:
        prestige_infos = util.sort_tuples_by(prestige_infos, [(1, False), (0, False)])
        for (char_info_2_name, char_info_to_name) in prestige_infos:
            body_lines.append(f'+ {char_info_2_name} = {char_info_to_name}')

    if body_lines:
        lines.extend(body_lines)
    else:
        if char_info_1['Rarity'] == 'Special':
            error = 'One cannot prestige **Special** crew.'
        elif char_info_1['Rarity'] == 'Legendary':
            error = 'One cannot prestige **Legendary** crew.'
        else:
            error = 'noone'
        lines.append(error)

    return lines


def get_prestige_to_info_as_embed(char_name: str, prestige_to_data: dict):
    return ''


def get_prestige_to_info_as_txt(char_name: str, prestige_to_data: dict) -> list:
    # Format: '{id1} + {id2}
    char_data = __character_designs_cache.get_data_dict3()
    char_info_to = _get_char_info(char_name)
    found_char_name = char_info_to[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]

    lines = [f'**There are {len(prestige_to_data)} ways to prestige {found_char_name} from:**']

    prestige_infos = []
    for value in prestige_to_data.values():
        char_info_1_name = char_data[value['CharacterDesignId1']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
        char_info_2_name = char_data[value['CharacterDesignId2']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
        prestige_infos.append((char_info_1_name, char_info_2_name))

    body_lines = []
    if prestige_infos:
        prestige_infos = util.sort_tuples_by(prestige_infos, [(0, False), (1, False)])
        for (char_info_1_name, char_info_2_name) in prestige_infos:
            body_lines.append(f'{char_info_1_name} + {char_info_2_name}')

    if body_lines:
        lines.extend(body_lines)
    else:
        if char_info_to['Rarity'] == 'Special':
            error = 'One cannot prestige to **Special** crew.'
        elif char_info_to['Rarity'] == 'Common':
            error = 'One cannot prestige to **Common** crew.'
        else:
            error = 'noone'
        lines.append(error)

    return lines


def _get_prestige_from_data(char_name: str) -> dict:
    char_info = _get_char_info(char_name)
    if char_info is None:
        return None

    char_design_id = char_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in __prestige_from_cache_dict.keys():
        prestige_from_cache = __prestige_from_cache_dict[char_design_id]
    else:
        prestige_from_cache = _create_and_add_prestige_from_cache(char_design_id)
    return prestige_from_cache.get_data_dict3()


def _get_prestige_to_data(char_name: str) -> dict:
    char_info = _get_char_info(char_name)
    if char_info is None:
        return None

    char_design_id = char_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in __prestige_to_cache_dict.keys():
        prestige_to_cache = __prestige_to_cache_dict[char_design_id]
    else:
        prestige_to_cache = _create_and_add_prestige_to_cache(char_design_id)
    return prestige_to_cache.get_data_dict3()


def _create_and_add_prestige_from_cache(char_design_id: str) -> PssCache:
    cache = _create_prestige_from_cache(char_design_id)
    __prestige_from_cache_dict[char_design_id] = cache
    return cache


def _create_and_add_prestige_to_cache(char_design_id: str) -> PssCache:
    cache = _create_prestige_to_cache(char_design_id)
    __prestige_to_cache_dict[char_design_id] = cache
    return cache


def _create_prestige_from_cache(char_design_id: str) -> PssCache:
    url = f'{__PRESTIGE_FROM_BASE_PATH}{char_design_id}'
    name = f'PrestigeFrom{char_design_id}'
    result = PssCache(url, name, None)
    return result


def _create_prestige_to_cache(char_design_id: str) -> PssCache:
    url = f'{__PRESTIGE_TO_BASE_PATH}{char_design_id}'
    name = f'PrestigeTo{char_design_id}'
    result = PssCache(url, name, None)
    return result





# ---------- Level Info ----------

def get_level_costs(from_level: int, to_level: int = None) -> list:
    # If to_level: assert that to_level > from_level and <= 41
    # Else: swap both, set from_level = 1
    if to_level:
        pss_assert.parameter_is_valid_integer(from_level, 'from_level', 1, to_level - 1)
        pss_assert.parameter_is_valid_integer(to_level, 'to_level', from_level + 1, 40)
    else:
        pss_assert.parameter_is_valid_integer(from_level, 'from_level', 2, 40)
        to_level = from_level
        from_level = 1

    crew_costs = _get_crew_costs(from_level, to_level, lookups.GAS_COSTS_LOOKUP, lookups.XP_COSTS_LOOKUP)
    legendary_crew_costs = _get_crew_costs(from_level, to_level, lookups.GAS_COSTS_LEGENDARY_LOOKUP, lookups.XP_COSTS_LEGENDARY_LOOKUP)

    crew_cost_txt = _get_crew_cost_txt(from_level, to_level, crew_costs)
    legendary_crew_cost_txt = _get_crew_cost_txt(from_level, to_level, legendary_crew_costs)

    result = ['**Level costs** (non-legendary crew, max research)']
    result.extend(crew_cost_txt)
    result.append(core.EMPTY_LINE)
    result.append('**Level costs** (legendary crew, max research)')
    result.extend(legendary_crew_cost_txt)

    return result, True


def _get_crew_costs(from_level: int, to_level: int, gas_costs_lookup: list, xp_cost_lookup: list) -> (int, int, int, int):
    gas_cost = gas_costs_lookup[to_level - 1]
    xp_cost = xp_cost_lookup[to_level - 1]
    gas_cost_from = sum(gas_costs_lookup[from_level - 1:to_level])
    xp_cost_from = sum(xp_cost_lookup[from_level - 1:to_level])

    if from_level > 1:
        return (None, None, gas_cost_from, xp_cost_from)
    else:
        return (gas_cost, xp_cost, gas_cost_from, xp_cost_from)


def _get_crew_cost_txt(from_level: int, to_level: int, costs: tuple) -> list:
    result = []
    if from_level == 1:
        result.append(f'Getting from level {to_level - 1:d} to {to_level:d} requires {costs[1]:,} {emojis.pss_stat_xp} and {costs[0]:,}{emojis.pss_gas_big}.')
    result.append(f'Getting from level {from_level:d} to {to_level:d} requires {costs[3]:,} {emojis.pss_stat_xp} and {costs[2]:,}{emojis.pss_gas_big}.')

    return result










# Get stat for level:
# - get exponent 'p' by ProgressionType:
#   - Linear: p = 1.0
#   - EaseIn: p = 2.0
#   - EaseOut: p = 0.5
# - get min stat 'min' & max stat 'max'
# result = min + (max - min) * ((level - 1) / 39) ** p

# ---------- Testing ----------

if __name__ == '__main__':
    #f = get_level_costs(20, 30)
    test_crew = [('xin', None), ('xin', 5)]
    for (crew_name, level) in test_crew:
        os.system('clear')
        result = get_char_details_from_name(crew_name, level, as_embed=False)
        for line in result[0]:
            print(line)
        print('')
        result = get_prestige_from_info(crew_name, as_embed=False)
        for line in result[0]:
            print(line)
        print('')
        result = get_prestige_to_info(crew_name, as_embed=False)
        for line in result[0]:
            print(line)
        print('')
        result = ''
