#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import discord
import os
from typing import Dict, List, Set, Tuple

from cache import PssCache
import emojis
import pss_assert
import pss_entity as entity
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










# ---------- Classes ----------

class CharDesignDetails(entity.EntityDesignDetails):
    def __init__(self, char_design_info: dict, collections_designs_data: dict = None, level: int = None):
        special = _get_ability_name(char_design_info)
        equipment_slots = _convert_equipment_mask(int(char_design_info['EquipmentMask']))
        collection_name = _get_collection_name(char_design_info, collections_designs_data)
        walk_speed = char_design_info['WalkingSpeed']
        run_speed = char_design_info['RunSpeed']

        ability = _get_stat('SpecialAbilityArgument', level, char_design_info)
        if special:
            ability += f' ({special})'

        self.__ability: str = ability
        self.__collection_name: str = collection_name
        self.__equipment_slots: str = equipment_slots
        self.__gender: str = char_design_info['GenderType']
        self.__level: int = level
        self.__race: str = char_design_info['RaceType']
        self.__rarity: str = char_design_info['Rarity']
        self.__speed: str = f'{walk_speed}/{run_speed}'
        self.__stat_attack: str = _get_stat('Attack', level, char_design_info)
        self.__stat_engine: str = _get_stat('Engine', level, char_design_info)
        self.__stat_fire_resistance: str = char_design_info['FireResistance']
        self.__stat_hp: str = _get_stat('Hp', level, char_design_info)
        self.__stat_pilot: str = _get_stat('Pilot', level, char_design_info)
        self.__stat_repair: str = _get_stat('Repair', level, char_design_info)
        self.__stat_science: str = _get_stat('Science', level, char_design_info)
        self.__stat_weapon: str = _get_stat('Weapon', level, char_design_info)
        self.__training_capacity: str = char_design_info['TrainingCapacity']

        details_long: List[Tuple[str, str]] = [
            ('Level', self.__level),
            ('Rarity', self.__rarity),
            ('Race', self.__race),
            ('Collection', self.__collection_name),
            ('Gender', self.__gender),
            ('Ability', self.__ability),
            ('HP', self.__stat_hp),
            ('Attack', self.__stat_attack),
            ('Repair', self.__stat_repair),
            ('Pilot', self.__stat_pilot),
            ('Science', self.__stat_science),
            ('Engine', self.__stat_engine),
            ('Weapon', self.__stat_weapon),
            ('Walk/run speed', self.__speed),
            ('Fire resist', self.__stat_fire_resistance),
            ('Training cap', self.__training_capacity),
            ('Slots', self.__equipment_slots)
        ]
        details_short: List[Tuple[str, str, bool]] = [
            ('Rarity', self.__rarity, False),
            ('Ability', self.__ability, True),
            ('Collection', self.__collection_name, True)
        ]

        super().__init__(
            name=char_design_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME],
            description=char_design_info['CharacterDesignDescription'],
            details_long=details_long,
            details_short=details_short
        )


    @property
    def ability(self) -> str:
        return self.__ability

    @property
    def attack(self) -> str:
        return self.__stat_attack

    @property
    def collection_name(self) -> str:
        return self.__collection_name

    @property
    def engine(self) -> str:
        return self.__stat_engine

    @property
    def equipment_slots(self) -> str:
        return self.__equipment_slots

    @property
    def fire_resistance(self) -> str:
        return self.__stat_fire_resistance

    @property
    def gender(self) -> str:
        return self.__gender

    @property
    def hp(self) -> str:
        return self.__stat_hp

    @property
    def level(self) -> int:
        return self.__level

    @property
    def pilot(self) -> str:
        return self.__stat_pilot

    @property
    def race(self) -> str:
        return self.__race

    @property
    def rarity(self) -> str:
        return self.__rarity

    @property
    def repair(self) -> str:
        return self.__stat_repair

    @property
    def science(self) -> str:
        return self.__stat_science

    @property
    def speed(self) -> str:
        return self.__speed

    @property
    def training_capacity(self) -> str:
        return self.__training_capacity

    @property
    def weapon(self) -> str:
        return self.__stat_weapon





class CollectionDesignDetails(entity.EntityDesignDetails):
    def __init__(self, collection_design_info: dict):
        collection_crew = _get_collection_chars_designs_infos(collection_design_info)
        collection_perk = collection_design_info['EnhancementType']
        collection_perk = lookups.COLLECTION_PERK_LOOKUP.get(collection_design_info['EnhancementType'], collection_design_info['EnhancementType'])
        min_combo = collection_design_info['MinCombo']
        max_combo = collection_design_info['MaxCombo']
        base_enhancement_value = collection_design_info['BaseEnhancementValue']
        step_enhancement_value = collection_design_info['StepEnhancementValue']

        self.__characters: str = ', '.join(collection_crew)
        self.__min_max_combo = f'{min_combo}...{max_combo}'
        self.__enhancement = f'{base_enhancement_value} (Base), {step_enhancement_value} (Step)'

        details_long: List[Tuple[str, str]] = [
            ('Combo Min...Max', self.__min_max_combo),
            (collection_perk, self.__enhancement),
            ('Characters', self.__characters)
        ]
        details_short: List[Tuple[str, str, bool]] = [
        ]

        super().__init__(
            name=collection_design_info[COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME],
            description=collection_design_info['CollectionDescription'],
            details_long=details_long,
            details_short=details_short
        )


    @property
    def characters(self) -> str:
        return self.__characters

    @property
    def min_max_combo(self) -> str:
        return self.__min_max_combo

    @property
    def enhancement(self) -> str:
        return self.__enhancement











class PrestigeDetails(entity.EntityDesignDetails):
    def __init__(self, char_design_info: dict, prestige_infos: Dict[str, List[str]], error_message: str, title_template: str, sub_title_template: str):
        self.__char_design_name: str = char_design_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
        self.__count: int = len(prestige_infos)
        self.__error: str = error_message
        self.__prestige_infos: Dict[str, List[str]]
        self.__title_template: str = title_template or '**$char_design_name$** has **$count$** combinations:'
        self.__sub_title_template: str = sub_title_template or '**$char_design_name$**:'


    @property
    def char_design_name(self) -> str:
        return self.__char_design_name

    @property
    def count(self) -> int:
        return self.__count

    @property
    def error(self) -> str:
        return len(self.__error)

    @property
    def prestige_infos(self) -> Dict[str, List[str]]:
        return self.__prestige_infos

    @property
    def title(self) -> str:
        result = self.__title_template
        result = result.replace('$char_design_name$', self.char_design_name)
        result = result.replace('$count$', self.count)
        return result


    def get_details_as_embed(self) -> discord.Embed:
        return None


    def get_details_as_text_long(self) -> List[str]:
        result = [self.title]
        if self.error:
            result.append(self.error)
        else:
            for char_design_name in sorted(list(self.prestige_infos.keys())):
                prestige_partners = sorted(self.prestige_infos[char_design_name])
                result.append(self._get_sub_title(char_design_name))
                result.append(f'> {", ".join(prestige_partners)}')
        return result


    def get_details_as_text_short(self) -> List[str]:
        return self.get_details_as_text_long()


    def _get_sub_title(self, char_design_name: str) -> str:
        result = self.__sub_title_template.replace('$char_design_name$', char_design_name)
        return result










class PrestigeFromDetails(PrestigeDetails):
    def __init__(self, char_from_design_info: dict, chars_designs_data: dict = None, prestige_from_data: dict = None):
        chars_designs_data = chars_designs_data or __character_designs_cache.get_data_dict3()
        error = None
        prestige_infos = {}
        template_title = '**$char_design_name$** has **$count$** prestige combinations:'
        template_subtitle = 'To **$char_design_name$** with:'

        if prestige_from_data:
            for value in prestige_from_data.values():
                char_info_2_name = chars_designs_data[value['CharacterDesignId2']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
                char_info_to_name = chars_designs_data[value['ToCharacterDesignId']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
                prestige_infos.setdefault(char_info_to_name, []).append(char_info_2_name)
        else:
            if char_from_design_info['Rarity'] == 'Special':
                error = 'One cannot prestige **Special** crew.'
            elif char_from_design_info['Rarity'] == 'Legendary':
                error = 'One cannot prestige **Legendary** crew.'
            else:
                error = 'noone'

        super().__init__(char_from_design_info, prestige_infos, error, template_title, template_subtitle)










class PrestigeToDetails(PrestigeDetails):
    def __init__(self, char_to_design_info: dict, chars_designs_data: dict = None, prestige_to_data: dict = None):
        chars_designs_data = chars_designs_data or __character_designs_cache.get_data_dict3()
        error = None
        prestige_infos = {}
        template_title = '**$char_design_name$** has **$count$** prestige recipes:'
        template_subtitle = '**$char_design_name$** with:'

        if prestige_to_data:
            prestige_recipes: Dict[str, Set[str]] = {}
            for value in prestige_to_data.values():
                char_1_design_name = chars_designs_data[value['CharacterDesignId1']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
                char_2_design_name = chars_designs_data[value['CharacterDesignId2']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
                prestige_recipes.setdefault(char_1_design_name, set()).add(char_2_design_name)
                prestige_recipes.setdefault(char_2_design_name, set()).add(char_1_design_name)

            prestige_recipe_ingredients: List[Tuple[str, str]] = [(char_design_name, prestige_partners) for char_design_name, prestige_partners in prestige_recipes.items()]
            prestige_recipe_ingredients = sorted(prestige_recipe_ingredients, key=lambda t: len(t[1]), reverse=True)
            remaining_names = set(prestige_recipes.keys())

            prestige_infos: Dict[str, List[str]] = {}
            for (char_design_name, prestige_partners) in prestige_recipe_ingredients:
                add_to_output = char_design_name in remaining_names or len([t for t in prestige_recipe_ingredients if t[0] in remaining_names])
                if add_to_output:
                    prestige_infos[char_design_name] = list(prestige_partners)
                    remaining_names.discard(char_design_name)
                    for prestige_partner in prestige_partners:
                        remaining_names.discard(prestige_partner)
                if not remaining_names:
                    break
        else:
            if char_to_design_info['Rarity'] == 'Special':
                error = 'One cannot prestige to **Special** crew.'
            elif char_to_design_info['Rarity'] == 'Common':
                error = 'One cannot prestige to **Common** crew.'
            else:
                error = 'noone'

        super().__init__(char_to_design_info, prestige_infos, error, template_title, template_subtitle)










# ---------- Helper functions ----------

def _convert_equipment_mask(equipment_mask: int) -> str:
    result = []
    for k in lookups.EQUIPMENT_MASK_LOOKUP.keys():
        if (equipment_mask & k) != 0:
            result.append(lookups.EQUIPMENT_MASK_LOOKUP[k])

    if result:
        return ', '.join(result)
    else:
        return '-'


def _get_ability_name(char_design_info: dict) -> str:
    if char_design_info:
        special = char_design_info['SpecialAbilityType']
        if special in lookups.SPECIAL_ABILITIES_LOOKUP.keys():
            return lookups.SPECIAL_ABILITIES_LOOKUP[special]
    return None


def _get_collection_chars_designs_infos(collection_design_info: Dict[str, str]) -> list:
    collection_id = collection_design_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_data = __character_designs_cache.get_data_dict3()
    chars_designs_infos = [chars_designs_data[char_id] for char_id in chars_designs_data.keys() if chars_designs_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = [char_design_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME] for char_design_info in chars_designs_infos]
    result.sort()
    return result


def _get_collection_name(char_design_info: dict, collections_designs_data: dict = None) -> str:
    if char_design_info:
        collection_id = char_design_info[COLLECTION_DESIGN_KEY_NAME]
        if collection_id and collection_id != '0':
            if not collections_designs_data:
                collections_designs_data = __collection_designs_cache.get_data_dict3()
            if collection_id in collections_designs_data.keys():
                return collections_designs_data[collection_id][COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME]
    return None


def _get_stat(stat_name: str, level: int, char_design_info: dict) -> str:
    is_special_stat = stat_name.lower().startswith('specialability')
    if is_special_stat:
        max_stat_name = 'SpecialAbilityFinalArgument'
    else:
        max_stat_name = f'Final{stat_name}'
    min_value = float(char_design_info[stat_name])
    max_value = float(char_design_info[max_stat_name])
    progression_type = char_design_info['ProgressionType']
    result = _get_stat_value(min_value, max_value, level, progression_type)
    return result


def _get_stat_value(min_value: float, max_value: float, level: int, progression_type: str) -> str:
    if level is None or level < 1 or level > 40:
        return f'{min_value:0.1f} - {max_value:0.1f}'
    else:
        return f'{_calculate_stat_value(min_value, max_value, level, progression_type):0.1f}'


def _calculate_stat_value(min_value: float, max_value: float, level: int, progression_type: str) -> float:
    exponent = lookups.PROGRESSION_TYPES[progression_type]
    result = min_value + (max_value - min_value) * ((level - 1) / 39) ** exponent
    return result










# ---------- Crew info ----------

def get_char_design_details_by_id(char_design_id: str, level: int, chars_designs_data: dict = None, collections_designs_data: dict = None) -> CharDesignDetails:
    if char_design_id:
        if chars_designs_data is None:
            chars_designs_data = __character_designs_cache.get_data_dict3()

        if char_design_id and char_design_id in chars_designs_data.keys():
            char_design_info = chars_designs_data[char_design_id]
            char_design_details = CharDesignDetails(char_design_info, collections_designs_data=collections_designs_data, level=level)
            return char_design_details

    return None


def get_char_design_details_by_name(char_name: str, level: int, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(char_name, 'char_name')
    pss_assert.parameter_is_valid_integer(level, 'level', min_value=1, max_value=40, allow_none=True)

    chars_designs_data = __character_designs_cache.get_data_dict3()
    char_design_info = _get_char_design_info_by_name(char_name, chars_designs_data)

    if char_design_info is None:
        return [f'Could not find a crew named **{char_name}**.'], False
    else:
        char_design_details = CharDesignDetails(char_design_info, level=level)
        if as_embed:
            return char_design_details.get_details_as_embed(), True
        else:
            return char_design_details.get_details_as_text_long(), True



def _get_char_design_info_by_name(char_name: str, chars_designs_data: dict = None) -> dict:
    chars_designs_data = chars_designs_data or __character_designs_cache.get_data_dict3()
    char_design_id = _get_char_design_id_by_name(char_name, chars_designs_data)

    if char_design_id and char_design_id in chars_designs_data.keys():
        return chars_designs_data[char_design_id]
    else:
        return None


def _get_char_design_id_by_name(char_name: str, chars_designs_data: dict = None) -> str:
    if chars_designs_data is None:
        chars_designs_data = __character_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(chars_designs_data, CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME, char_name)
    if len(results) > 0:
        return results[0]

    return None


def _get_chars_designs_infos() -> list:
    chars_designs_data = __character_designs_cache.get_data_dict3()
    result = [chars_designs_data[key][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME] for key in chars_designs_data.keys()]
    return result










# ---------- Collection Info ----------

def get_collection_design_details_by_name(collection_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(collection_name)

    collection_design_info = _get_collection_design_info(collection_name)

    if collection_design_info is None:
        return [f'Could not find a collection named **{collection_name}**.'], False
    else:
        collection_design_details = CollectionDesignDetails(collection_design_info)
        if as_embed:
            return collection_design_details.get_details_as_embed(), True
        else:
            return collection_design_details.get_details_as_text_long(), True


def _get_collection_design_info(collection_name: str):
    collections_designs_data = __collection_designs_cache.get_data_dict3()
    collection_design_id = _get_collection_design_id_by_name(collection_name, collections_designs_data)

    if collection_design_id and collection_design_id in collections_designs_data.keys():
        return collections_designs_data[collection_design_id]
    else:
        return None


def _get_collection_design_id_by_name(collection_name: str, collections_designs_data: dict = None):
    if collections_designs_data is None:
        collections_designs_data = __collection_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(collections_designs_data, COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME, collection_name)
    if len(results) > 0:
        return results[0]

    return None










# ---------- Prestige from Info ----------

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


def get_prestige_from_info_as_embed(char_name: str, prestige_from_data: dict):
    return ''


def get_prestige_from_info_as_txt(char_name: str, prestige_from_data: dict) -> list:
    char_data = __character_designs_cache.get_data_dict3()
    char_info_1 = _get_char_design_info_by_name(char_name)
    found_char_name = char_info_1[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
    combination_count = len(prestige_from_data)

    lines = [f'**{found_char_name}** has **{combination_count}** prestige combinations:']

    prestige_targets = {}
    for value in prestige_from_data.values():
        char_info_2_name = char_data[value['CharacterDesignId2']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
        char_info_to_name = char_data[value['ToCharacterDesignId']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]

        if char_info_to_name not in prestige_targets.keys():
            prestige_targets[char_info_to_name] = []
        prestige_targets[char_info_to_name].append(char_info_2_name)

    body_lines = []
    for prestige_target in sorted(list(prestige_targets.keys())):
        prestige_partners = sorted(prestige_targets[prestige_target])
        body_lines.append(f'**{prestige_target}** with:')
        body_lines.append(f'> {", ".join(prestige_partners)}')

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


def _get_prestige_from_data(char_name: str) -> dict:
    char_info = _get_char_design_info_by_name(char_name)
    if char_info is None:
        return None

    char_design_id = char_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in __prestige_from_cache_dict.keys():
        prestige_from_cache = __prestige_from_cache_dict[char_design_id]
    else:
        prestige_from_cache = _create_and_add_prestige_from_cache(char_design_id)
    return prestige_from_cache.get_data_dict3()


def _create_and_add_prestige_from_cache(char_design_id: str) -> PssCache:
    cache = _create_prestige_from_cache(char_design_id)
    __prestige_from_cache_dict[char_design_id] = cache
    return cache


def _create_prestige_from_cache(char_design_id: str) -> PssCache:
    url = f'{__PRESTIGE_FROM_BASE_PATH}{char_design_id}'
    name = f'PrestigeFrom{char_design_id}'
    result = PssCache(url, name, None)
    return result










# ---------- Prestige to Info ----------

def get_prestige_to_info(char_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(char_name)

    chars_designs_data = __character_designs_cache.get_data_dict3()
    char_to_design_info = _get_char_design_info_by_name(char_name, chars_designs_data)
    if not char_to_design_info:
        return [f'Could not find a crew named **{char_name}**.'], False
    else:
        prestige_to_data = _get_prestige_to_data(char_to_design_info)
        prestige_to_details = PrestigeToDetails(char_to_design_info, chars_designs_data=chars_designs_data, prestige_to_data=prestige_to_data)

        if as_embed:
            return prestige_to_details.get_details_as_embed(), True
        else:
            return prestige_to_details.get_details_as_text_long(), True


def _get_prestige_to_data(char_design_info: dict) -> dict:
    if not char_design_info:
        return {}

    char_design_id = char_design_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in __prestige_to_cache_dict.keys():
        prestige_to_cache = __prestige_to_cache_dict[char_design_id]
    else:
        prestige_to_cache = _create_and_add_prestige_to_cache(char_design_id)
    return prestige_to_cache.get_data_dict3()


def _create_and_add_prestige_to_cache(char_design_id: str) -> PssCache:
    cache = _create_prestige_to_cache(char_design_id)
    __prestige_to_cache_dict[char_design_id] = cache
    return cache


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
    result.append(settings.EMPTY_LINE)
    result.append('**Level costs** (legendary crew, max research)')
    result.extend(legendary_crew_cost_txt)

    return result, True


def _get_crew_costs(from_level: int, to_level: int, gas_costs_lookup: list, xp_cost_lookup: list) -> (int, int, int, int):
    gas_cost = gas_costs_lookup[to_level - 1]
    xp_cost = xp_cost_lookup[to_level - 1]
    gas_cost_from = sum(gas_costs_lookup[from_level:to_level])
    xp_cost_from = sum(xp_cost_lookup[from_level:to_level])

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
    f = get_level_costs(20, 30)
    test_crew = [('alpaco', 5)]
    for (crew_name, level) in test_crew:
        os.system('clear')
        result = get_char_design_details_by_name(crew_name, level, as_embed=False)
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
