#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from cache import PssCache
import pss_assert
import pss_core as core
import pss_lookups as lookups
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

def get_ability_name(char_id: str, char_designs_data: dict = None) -> str:
    if char_id:
        if not char_designs_data:
            char_designs_data = __character_designs_cache.get_data_dict3()

        char_info = char_designs_data[char_id]
        special = char_info['SpecialAbilityType']
        if special in lookups.SPECIAL_ABILITIES_LOOKUP.keys():
            return lookups.SPECIAL_ABILITIES_LOOKUP[special]
    return 'None'


def get_collection_name(char_id: str, char_designs_data: dict = None, collection_designs_data: dict = None) -> str:
    if char_id:
        if not char_designs_data:
            char_designs_data = __character_designs_cache.get_data_dict3()
        if not collection_designs_data:
            collection_designs_data = __collection_designs_cache.get_data_dict3()

        char_info = char_designs_data[char_id]
        collection_id = char_info[COLLECTION_DESIGN_KEY_NAME]
        if collection_id and collection_id in collection_designs_data.keys():
            return collection_designs_data[collection_id][COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME]
    return 'None'



# ---------- Crew info ----------

def get_char_details_from_name(char_name: str, as_embed: bool = False):
    pss_assert.valid_entity_name(char_name)

    char_info = _get_char_info(char_name)

    if char_info is None:
        return [f'Could not find a crew named **{char_name}**.'], False
    else:
        if as_embed:
            return _get_char_info_as_embed(char_info), True
        else:
            return _get_char_info_as_text(char_info), True



def _get_char_info(char_name: str):
    char_design_data = __character_designs_cache.get_data_dict3()
    char_design_id = _get_char_design_id_from_name(char_name, char_design_data)

    if char_design_id and char_design_id in char_design_data.keys():
        return char_design_data[char_design_id]
    else:
        return None


def _get_char_design_id_from_name(char_name: str, char_data:dict = None):
    if char_data is None:
        char_data = __character_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(char_data, CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME, char_name)
    if len(results) > 0:
        return results[0]

    return None


def _get_char_info_as_embed(char_info: dict):
    return ''


def _get_char_info_as_text(char_info: dict):
    lines = get_char_info_from_data_as_text(char_info)
    return lines


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


def get_char_info_from_data_as_text(char_info: dict, char_designs_data: dict = None, collection_designs_data: dict = None) -> list:
    if not char_designs_data:
        char_designs_data = __character_designs_cache.get_data_dict3()
    if not collection_designs_data:
        collection_designs_data = __collection_designs_cache.get_data_dict3()

    char_id = char_info[CHARACTER_DESIGN_KEY_NAME]
    char_name = char_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
    special = get_ability_name(char_id)
    equipment_slots = _convert_equipment_mask(int(char_info['EquipmentMask']))
    collection_name = get_collection_name(char_id, char_designs_data, collection_designs_data)

    result = [f'**{char_name}** ({char_info["Rarity"]})']
    result.append(char_info['CharacterDesignDescription'])
    result.append(f'Race: {char_info["RaceType"]}, Collection: {collection_name}, Gender: {char_info["GenderType"]}')
    result.append(f'ability = {char_info["SpecialAbilityFinalArgument"]} ({special})')
    result.append(f'hp = {char_info["FinalHp"]}')
    result.append(f'attack = {char_info["FinalAttack"]}')
    result.append(f'repair = {char_info["FinalRepair"]}')
    result.append(f'pilot = {char_info["FinalPilot"]}')
    result.append(f'science = {char_info["FinalScience"]}')
    result.append(f'weapon = {char_info["FinalWeapon"]}')
    result.append(f'engine = {char_info["FinalEngine"]}')
    result.append(f'walk/run speed = {char_info["WalkingSpeed"]}/{char_info["RunSpeed"]}')
    result.append(f'fire resist = {char_info["FireResistance"]}')
    result.append(f'training capacity = {char_info["TrainingCapacity"]}')
    result.append(f'equipment = {equipment_slots}')

    return result


def get_char_info_short_from_id_as_text(char_design_id: dict, char_designs_data: dict = None, collection_designs_data: dict = None) -> list:
    if not char_designs_data:
        char_designs_data = __character_designs_cache.get_data_dict3()
    if not collection_designs_data:
        collection_designs_data = __collection_designs_cache.get_data_dict3()

    char_info = char_designs_data[char_design_id]
    return get_char_info_short_from_data_as_text(char_info, char_designs_data, collection_designs_data)


def get_char_info_short_from_data_as_text(char_info: dict, char_designs_data: dict = None, collection_designs_data: dict = None) -> list:
    if not char_designs_data:
        char_designs_data = __character_designs_cache.get_data_dict3()
    if not collection_designs_data:
        collection_designs_data = __collection_designs_cache.get_data_dict3()

    char_id = char_info[CHARACTER_DESIGN_KEY_NAME]
    name = char_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
    rarity = char_info['Rarity']
    collection = get_collection_name(char_id, char_designs_data, collection_designs_data)
    ability = get_ability_name(char_id, char_designs_data)
    ability_stat = int(char_info['SpecialAbilityFinalArgument'])
    ability_txt = ability
    if ability_stat:
        ability_txt = f'{ability} ({ability_stat})'
    result = [f'{name} (_{rarity}_ - Ability: _{ability_txt}_ - Collection: _{collection}_)']
    return result





# ---------- Collection Info ----------

def get_collection_info(collection_name, as_embed=False):
    pss_assert.valid_entity_name(collection_name)

    collection_info = _get_collection_info(collection_name)

    if collection_info is None:
        return [f'Could not find a collection named **{collection_name}**.'], False
    else:
        if as_embed:
            return _get_collection_info_as_embed(collection_info), True
        else:
            return _get_collection_info_as_text(collection_info), True


def _get_collection_info(collection_name):
    collection_data = __collection_designs_cache.get_data_dict3()
    collection_design_id = _get_collection_design_id_from_name(collection_name, collection_data)

    if collection_design_id and collection_design_id in collection_data.keys():
        return collection_data[collection_design_id]
    else:
        return None


def _get_collection_design_id_from_name(collection_name, collection_data=None):
    if collection_data is None:
        collection_data = __collection_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(collection_data, COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME, collection_name)
    if len(results) > 0:
        return results[0]

    return None


def _get_collection_info_as_embed(collection_info):
    # Use collection_info['ColorString'] for embed color
    return []


def _get_collection_info_as_text(collection_info):
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

def get_prestige_from_info(char_name, as_embed=False):
    pss_assert.valid_entity_name(char_name)

    prestige_data = _get_prestige_from_data(char_name)

    if prestige_data is None:
        return [f'Could not find prestige paths requiring **{char_name}**'], False
    else:
        if as_embed:
            return get_prestige_from_info_as_embed(char_name, prestige_data), True
        else:
            return get_prestige_from_info_as_txt(char_name, prestige_data), True


def get_prestige_to_info(char_name, as_embed=False):
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


def get_prestige_from_info_as_txt(char_name: str, prestige_from_data: dict):
    # Format: '+ {id2} = {toid}
    char_data = __character_designs_cache.get_data_dict3()
    char_info_1 = _get_char_info(char_name)
    found_char_name = char_info_1[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]

    lines = [f'**{found_char_name} can be prestiged into**']
    body_lines = []

    for value in prestige_from_data.values():
        char_info_2 = char_data[value['CharacterDesignId2']]
        char_info_to = char_data[value['ToCharacterDesignId']]
        body_lines.append(f'+ {char_info_2[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]} = {char_info_to[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]}')

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


def get_prestige_to_info_as_embed(char_name, prestige_to_data):
    return ''


def get_prestige_to_info_as_txt(char_name, prestige_to_data):
    # Format: '{id1} + {id2}
    char_data = __character_designs_cache.get_data_dict3()
    char_info_to = _get_char_info(char_name)
    found_char_name = char_info_to[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]

    lines = [f'**{found_char_name} can be prestiged from**']
    body_lines = []

    for value in prestige_to_data.values():
        char_info_1 = char_data[value['CharacterDesignId1']]
        char_info_2 = char_data[value['CharacterDesignId2']]
        body_lines.append(f'{char_info_1[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]} + {char_info_2[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]}')

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


def _get_prestige_from_data(char_name):
    char_info = _get_char_info(char_name)
    if char_info is None:
        return None

    char_design_id = char_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in __prestige_from_cache_dict.keys():
        prestige_from_cache = __prestige_from_cache_dict[char_design_id]
    else:
        prestige_from_cache = _create_and_add_prestige_from_cache(char_design_id)
    return prestige_from_cache.get_data_dict3()


def _get_prestige_to_data(char_name) -> dict:
    char_info = _get_char_info(char_name)
    if char_info is None:
        return None

    char_design_id = char_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in __prestige_to_cache_dict.keys():
        prestige_to_cache = __prestige_to_cache_dict[char_design_id]
    else:
        prestige_to_cache = _create_and_add_prestige_to_cache(char_design_id)
    return prestige_to_cache.get_data_dict3()


def _create_and_add_prestige_from_cache(char_design_id) -> PssCache:
    cache = _create_prestige_from_cache(char_design_id)
    __prestige_from_cache_dict[char_design_id] = cache
    return cache


def _create_and_add_prestige_to_cache(char_design_id) -> PssCache:
    cache = _create_prestige_to_cache(char_design_id)
    __prestige_to_cache_dict[char_design_id] = cache
    return cache


def _create_prestige_from_cache(char_design_id) -> PssCache:
    url = f'{__PRESTIGE_FROM_BASE_PATH}{char_design_id}'
    name = f'PrestigeFrom{char_design_id}'
    result = PssCache(url, name, None)
    return result


def _create_prestige_to_cache(char_design_id) -> PssCache:
    url = f'{__PRESTIGE_TO_BASE_PATH}{char_design_id}'
    name = f'PrestigeTo{char_design_id}'
    result = PssCache(url, name, None)
    return result





# ---------- Level Info ----------

def get_level_costs(level: int) -> list:
    if not level or level < 2 or level > 40:
        return ['Invalid value. Enter a level between 2 and 40!']

    result = ['**Level costs** (non-legendary crew, max research)']
    result.extend(_get_crew_cost_txt(level, lookups.GAS_COSTS_LOOKUP, lookups.XP_COSTS_LOOKUP))
    result.append(core.EMPTY_LINE)
    result.append('**Level costs** (legendary crew, max research)')
    result.extend(_get_crew_cost_txt(level, lookups.GAS_COSTS_LEGENDARY_LOOKUP, lookups.XP_COSTS_LEGENDARY_LOOKUP))

    return result, True


def _get_crew_cost_txt(level: int, gas_costs_lookup: list, xp_costs_lookup: list) -> list:
    gas_cost = gas_costs_lookup[level - 1]
    xp_cost = xp_costs_lookup[level - 1]
    gas_cost_from_1 = sum(gas_costs_lookup[:level])
    xp_cost_from_1 = sum(xp_costs_lookup[:level])

    result = [f'Getting from level {level - 1} to {level} requires {xp_cost:,} xp and {gas_cost:,} gas.']
    result.append(f'Getting from level 1 to {level} requires {xp_cost_from_1:,} xp and {gas_cost_from_1:,} gas.')

    return result