#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import discord
import os
from typing import Dict, List, Set, Tuple, Union

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

__prestige_from_cache_dict = {}
__prestige_to_cache_dict = {}










# ---------- Classes ----------

class LegacyPrestigeDetails(entity.LegacyEntityDesignDetails):
    def __init__(self, char_design_info: dict, prestige_infos: Dict[str, List[str]], error_message: str, title_template: str, sub_title_template: str):
        self.__char_design_name: str = char_design_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
        self.__count: int = sum([len(prestige_partners) for prestige_partners in prestige_infos.values()])
        self.__error: str = error_message
        self.__prestige_infos: Dict[str, List[str]] = prestige_infos
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
        return self.__error

    @property
    def prestige_infos(self) -> Dict[str, List[str]]:
        return self.__prestige_infos

    @property
    def title(self) -> str:
        result = self.__title_template
        result = result.replace('$char_design_name$', self.char_design_name)
        result = result.replace('$count$', str(self.count))
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










class LegacyPrestigeFromDetails(LegacyPrestigeDetails):
    def __init__(self, char_from_design_info: dict, chars_designs_data: dict, prestige_from_data: dict):
        chars_designs_data = chars_designs_data
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










class LegacyPrestigeToDetails(LegacyPrestigeDetails):
    def __init__(self, char_to_design_info: dict, chars_designs_data: dict, prestige_to_data: dict):
        chars_designs_data = chars_designs_data
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

            prestige_recipe_ingredients: List[Tuple[str, Set[str]]] = [(char_design_name, prestige_partners) for char_design_name, prestige_partners in prestige_recipes.items()]

            prestige_infos: Dict[str, List[str]] = {}
            while prestige_recipe_ingredients:
                prestige_recipe_ingredients = sorted(prestige_recipe_ingredients, key=lambda t: len(t[1]), reverse=True)
                (char_design_name, prestige_partners) = prestige_recipe_ingredients[0]
                prestige_infos[char_design_name] = list(prestige_partners)
                prestige_recipe_ingredients = LegacyPrestigeToDetails._update_prestige_recipe_ingredients(prestige_recipe_ingredients)
        else:
            if char_to_design_info['Rarity'] == 'Special':
                error = 'One cannot prestige to **Special** crew.'
            elif char_to_design_info['Rarity'] == 'Common':
                error = 'One cannot prestige to **Common** crew.'
            else:
                error = 'noone'

        super().__init__(char_to_design_info, prestige_infos, error, template_title, template_subtitle)


    @staticmethod
    def _update_prestige_recipe_ingredients(prestige_recipe_ingredients: List[Tuple[str, Set[str]]]) -> List[Tuple[str, Set[str]]]:
        result: List[Tuple[str, Set[str]]] = []
        # Take 1st char name & prestige partners
        # Remove that pair from the result
        # Iterate through
        (base_char_design_name, base_prestige_partners) = prestige_recipe_ingredients[0]
        for (char_design_name, prestige_partners) in prestige_recipe_ingredients[1:]:
            if base_char_design_name in prestige_partners and char_design_name in base_prestige_partners:
                prestige_partners = [x for x in prestige_partners if x != base_char_design_name]
            if prestige_partners:
                result.append((char_design_name, prestige_partners))
        return result










# ---------- Helper functions ----------

def __create_character_design_details_from_info(character_design_info: entity.EntityDesignInfo, characters_designs_data: entity.EntitiesDesignsData, collections_designs_data: entity.EntitiesDesignsData, level: int) -> entity.EntityDesignDetails:
    return entity.EntityDesignDetails(character_design_info, __properties['character_title'], __properties['character_description'], __properties['character_long'], __properties['character_short'], __properties['character_long'], characters_designs_data, collections_designs_data, level=level)


def __create_character_design_data_list_from_infos(characters_designs_infos: List[entity.EntityDesignInfo], characters_designs_data: entity.EntitiesDesignsData, collections_designs_data: entity.EntitiesDesignsData, level: int) -> List[entity.EntitiesDesignsData]:
    return [__create_character_design_details_from_info(character_design_info, characters_designs_data, collections_designs_data, level) for character_design_info in characters_designs_infos]


def __create_collection_design_details_from_info(collection_design_info: entity.EntityDesignInfo, collections_designs_data: entity.EntitiesDesignsData, characters_designs_data: entity.EntitiesDesignsData) -> entity.EntityDesignDetails:
    return entity.EntityDesignDetails(collection_design_info, __properties['collection_title'], __properties['collection_description'], __properties['collection_long'], __properties['collection_short'], __properties['collection_long'], collections_designs_data, characters_designs_data)


def __create_collection_design_data_list_from_infos(collections_designs_infos: List[entity.EntityDesignInfo], collections_designs_data: entity.EntitiesDesignsData, characters_designs_data: entity.EntitiesDesignsData) -> List[entity.EntitiesDesignsData]:
    return [__create_collection_design_details_from_info(collection_design_info, collections_designs_data, characters_designs_data) for collection_design_info in collections_designs_infos]





def __calculate_stat_value(min_value: float, max_value: float, level: int, progression_type: str) -> float:
    exponent = lookups.PROGRESSION_TYPES[progression_type]
    result = min_value + (max_value - min_value) * ((level - 1) / 39) ** exponent
    return result


def __get_ability_stat(character_design_info: entity.EntityDesignInfo, characters_designs_data: entity.EntitiesDesignsData, collections_designs_data: entity.EntitiesDesignsData, level: int, **kwargs) -> str:
    value = __get_stat(character_design_info, characters_designs_data, collections_designs_data, level, stat_name='SpecialAbilityArgument')
    if character_design_info['SpecialAbilityType']:
        special_ability = lookups.SPECIAL_ABILITIES_LOOKUP.get(character_design_info['SpecialAbilityType'], character_design_info['SpecialAbilityType'])
    else:
        special_ability is None
    if special_ability:
        result = f'{value} ({special_ability})'
    else:
        result = value
    return result


def __get_collection_name(character_design_info: entity.EntityDesignInfo, characters_designs_data: entity.EntitiesDesignsData, collections_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    result = None
    collection_id = character_design_info[COLLECTION_DESIGN_KEY_NAME]
    if collection_id and int(collection_id):
        result = collections_designs_data[collection_id][COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME]
    return result


def __get_collection_member_count(collection_design_info: entity.EntityDesignInfo, collections_designs_data: entity.EntitiesDesignsData, characters_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    collection_id = collection_design_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_infos = [characters_designs_data[char_id] for char_id in characters_designs_data.keys() if characters_designs_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = len(chars_designs_infos)
    return f'{result} members'


def __get_collection_member_names(collection_design_info: entity.EntityDesignInfo, collections_designs_data: entity.EntitiesDesignsData, characters_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    collection_id = collection_design_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_infos = [characters_designs_data[char_id] for char_id in characters_designs_data.keys() if characters_designs_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = [char_design_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME] for char_design_info in chars_designs_infos]
    result.sort()
    return ', '.join(result)


def __get_collection_hyperlink(collection_design_info: entity.EntityDesignInfo, collections_designs_data: entity.EntitiesDesignsData, characters_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    return '<https://pixelstarships.fandom.com/wiki/Category:Crew_Collections>'


def __get_collection_perk(collection_design_info: entity.EntityDesignInfo, collections_designs_data: entity.EntitiesDesignsData, characters_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    enhancement_type = collection_design_info['EnhancementType']
    result = lookups.COLLECTION_PERK_LOOKUP.get(enhancement_type, enhancement_type)
    return result


def __get_enhancement(collection_design_info: entity.EntityDesignInfo, collections_designs_data: entity.EntitiesDesignsData, characters_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    base_enhancement_value = collection_design_info['BaseEnhancementValue']
    step_enhancement_value = collection_design_info['StepEnhancementValue']
    result = f'{base_enhancement_value} (Base), {step_enhancement_value} (Step)'
    return result


def __get_level(character_design_info: entity.EntityDesignInfo, characters_designs_data: entity.EntitiesDesignsData, collections_designs_data: entity.EntitiesDesignsData, level: int, **kwargs) -> str:
    if level is None:
        return None
    else:
        return str(level)


def __get_members_count_display_name(collection_design_info: entity.EntityDesignInfo, collections_designs_data: entity.EntitiesDesignsData, characters_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    collection_id = collection_design_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_infos = [characters_designs_data[char_id] for char_id in characters_designs_data.keys() if characters_designs_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = f'Members ({len(chars_designs_infos)})'
    return result


def __get_min_max_combo(collection_design_info: entity.EntityDesignInfo, collections_designs_data: entity.EntitiesDesignsData, characters_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    min_combo = collection_design_info['MinCombo']
    max_combo = collection_design_info['MaxCombo']
    result = f'{min_combo}...{max_combo}'
    return result


def __get_slots(character_design_info: entity.EntityDesignInfo, characters_designs_data: entity.EntitiesDesignsData, collections_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    result = []
    equipment_mask = int(character_design_info['EquipmentMask'])
    for k in lookups.EQUIPMENT_MASK_LOOKUP.keys():
        if (equipment_mask & k) != 0:
            result.append(lookups.EQUIPMENT_MASK_LOOKUP[k])

    result = ', '.join(result) if result else '-'
    return result


def __get_speed(character_design_info: entity.EntityDesignInfo, characters_designs_data: entity.EntitiesDesignsData, collections_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    walk_speed = character_design_info['WalkingSpeed']
    run_speed = character_design_info['RunSpeed']
    result = f'{walk_speed}/{run_speed}'
    return result


def __get_stat(character_design_info: entity.EntityDesignInfo, characters_designs_data: entity.EntitiesDesignsData, collections_designs_data: entity.EntitiesDesignsData, level: int, stat_name: str, **kwargs) -> str:
    is_special_stat = stat_name.lower().startswith('specialability')
    if is_special_stat:
        max_stat_name = 'SpecialAbilityFinalArgument'
    else:
        max_stat_name = f'Final{stat_name}'
    min_value = float(character_design_info[stat_name])
    max_value = float(character_design_info[max_stat_name])
    progression_type = character_design_info['ProgressionType']
    result = __get_stat_value(min_value, max_value, level, progression_type)
    return result


def __get_stat_value(min_value: float, max_value: float, level: int, progression_type: str) -> str:
    if level is None or level < 1 or level > 40:
        return f'{min_value:0.1f} - {max_value:0.1f}'
    else:
        return f'{__calculate_stat_value(min_value, max_value, level, progression_type):0.1f}'









async def _get_collection_chars_designs_infos(collection_design_info: Dict[str, str]) -> list:
    collection_id = collection_design_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_data = await characters_designs_retriever.get_data_dict3()
    chars_designs_infos = [chars_designs_data[char_id] for char_id in chars_designs_data.keys() if chars_designs_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = [char_design_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME] for char_design_info in chars_designs_infos]
    result.sort()
    return result










# ---------- Crew info ----------

def get_char_design_details_by_id(char_design_id: str, chars_designs_data: entity.EntitiesDesignsData, collections_designs_data: entity.EntitiesDesignsData, level: int = None) -> entity.EntityDesignDetails:
    if char_design_id:
        if char_design_id and char_design_id in chars_designs_data.keys():
            return __create_character_design_details_from_info(chars_designs_data[char_design_id], chars_designs_data, collections_designs_data, level)
    return None


async def get_char_design_details_by_name(char_name: str, level: int, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(char_name, 'char_name', min_length=2)
    pss_assert.parameter_is_valid_integer(level, 'level', min_value=1, max_value=40, allow_none=True)

    chars_designs_data = await characters_designs_retriever.get_data_dict3()
    char_design_info = await characters_designs_retriever.get_entity_design_info_by_name(char_name, chars_designs_data)

    if char_design_info is None:
        return [f'Could not find a crew named **{char_name}**.'], False
    else:
        collections_designs_data = await collections_designs_retriever.get_data_dict3()
        character_design_details = __create_character_design_details_from_info(char_design_info, None, collections_designs_data, level)
        if as_embed:
            return character_design_details.get_details_as_embed(), True
        else:
            return character_design_details.get_details_as_text_long(), True










# ---------- Collection Info ----------

async def get_collection_design_details_by_name(collection_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(collection_name, parameter_name='collection_name', allow_none_or_empty=True)

    print_all = not collection_name
    collections_designs_data = await collections_designs_retriever.get_data_dict3()
    characters_designs_data = await characters_designs_retriever.get_data_dict3()
    collections_designs_infos = []
    if print_all:
        collections_designs_infos = collections_designs_data.values()
    else:
        collections_designs_infos.append(await collections_designs_retriever.get_entity_design_info_by_name(collection_name, collections_designs_data))

    if collections_designs_infos is None:
        if print_all:
            return [f'An error occured upon retrieving collection info. Please try again later.'], False
        else:
            return [f'Could not find a collection named **{collection_name}**.'], False
    else:
        collections_designs_infos = sorted(collections_designs_infos, key=lambda x: x[COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME])
        collections_designs_details = [__create_collection_design_details_from_info(collection_design_info, collections_designs_data, characters_designs_data) for collection_design_info in collections_designs_infos]
        if print_all:
            if as_embed:
                return collections_designs_details.get_details_as_embed(), True
            else:
                long_details = []
                for collection_design_details in collections_designs_details:
                    long_details.extend(collection_design_details.get_details_as_text_short())
                long_details.append(__get_collection_hyperlink(None, None, None))
                return long_details, True
        else:
            if as_embed:
                return collections_designs_details[0].get_details_as_embed(), True
            else:
                return collections_designs_details[0].get_details_as_text_long(), True










# ---------- Prestige from Info ----------

async def get_prestige_from_info(char_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(char_name, 'char_name', min_length=2)

    chars_designs_data = await characters_designs_retriever.get_data_dict3()
    char_from_design_info = await characters_designs_retriever.get_entity_design_info_by_name(char_name, chars_designs_data)

    if not char_from_design_info:
        return [f'Could not find a crew named **{char_name}**.'], False
    else:
        prestige_from_data = await _get_prestige_from_data(char_from_design_info)
        prestige_from_details = LegacyPrestigeFromDetails(char_from_design_info, chars_designs_data, prestige_from_data)

        if as_embed:
            return prestige_from_details.get_details_as_embed(), True
        else:
            return prestige_from_details.get_details_as_text_long(), True


async def _get_prestige_from_data(char_design_info: dict) -> dict:
    if not char_design_info:
        return {}

    char_design_id = char_design_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in __prestige_from_cache_dict.keys():
        prestige_from_cache = __prestige_from_cache_dict[char_design_id]
    else:
        prestige_from_cache = _create_and_add_prestige_from_cache(char_design_id)
    return await prestige_from_cache.get_data_dict3()


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

async def get_prestige_to_info(char_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(char_name, 'char_name', min_length=2)

    chars_designs_data = await characters_designs_retriever.get_data_dict3()
    char_to_design_info = await characters_designs_retriever.get_entity_design_info_by_name(char_name, chars_designs_data)

    if not char_to_design_info:
        return [f'Could not find a crew named **{char_name}**.'], False
    else:
        prestige_to_data = await _get_prestige_to_data(char_to_design_info)
        prestige_to_details = LegacyPrestigeToDetails(char_to_design_info, chars_designs_data, prestige_to_data)

        if as_embed:
            return prestige_to_details.get_details_as_embed(), True
        else:
            return prestige_to_details.get_details_as_text_long(), True


async def _get_prestige_to_data(char_design_info: dict) -> dict:
    if not char_design_info:
        return {}

    char_design_id = char_design_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in __prestige_to_cache_dict.keys():
        prestige_to_cache = __prestige_to_cache_dict[char_design_id]
    else:
        prestige_to_cache = _create_and_add_prestige_to_cache(char_design_id)
    return await prestige_to_cache.get_data_dict3()


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










# ---------- Initilization ----------

characters_designs_retriever = entity.EntityDesignsRetriever(
    CHARACTER_DESIGN_BASE_PATH,
    CHARACTER_DESIGN_KEY_NAME,
    CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='CharacterDesigns'
)


collections_designs_retriever = entity.EntityDesignsRetriever(
    COLLECTION_DESIGN_BASE_PATH,
    COLLECTION_DESIGN_KEY_NAME,
    COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='CollectionDesigns'
)


__properties: Dict[str, Union[entity.EntityDesignDetailProperty, List[entity.EntityDesignDetailProperty]]] = {
    'character_title': entity.EntityDesignDetailProperty('Title', False, entity_property_name=CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME),
    'character_description': entity.EntityDesignDetailProperty('Description', False, entity_property_name='CharacterDesignDescription'),
    'character_long': [
        entity.EntityDesignDetailProperty('Level', True, omit_if_none=True, transform_function=__get_level),
        entity.EntityDesignDetailProperty('Rarity', True, entity_property_name='Rarity'),
        entity.EntityDesignDetailProperty('Race', True, entity_property_name='RaceType'),
        entity.EntityDesignDetailProperty('Collection', True, transform_function=__get_collection_name),
        entity.EntityDesignDetailProperty('Gender', True, entity_property_name='GenderType'),
        entity.EntityDesignDetailProperty('Ability', True, transform_function=__get_ability_stat),
        entity.EntityDesignDetailProperty('HP', True, transform_function=__get_stat, stat_name='Hp'),
        entity.EntityDesignDetailProperty('Attack', True, transform_function=__get_stat, stat_name='Attack'),
        entity.EntityDesignDetailProperty('Repair', True, transform_function=__get_stat, stat_name='Repair'),
        entity.EntityDesignDetailProperty('Pilot', True, transform_function=__get_stat, stat_name='Pilot'),
        entity.EntityDesignDetailProperty('Science', True, transform_function=__get_stat, stat_name='Science'),
        entity.EntityDesignDetailProperty('Engine', True, transform_function=__get_stat, stat_name='Engine'),
        entity.EntityDesignDetailProperty('Weapon', True, transform_function=__get_stat, stat_name='Weapon'),
        entity.EntityDesignDetailProperty('Walk/run speed', True, transform_function=__get_speed),
        entity.EntityDesignDetailProperty('Fire resist', True, entity_property_name='FireResistance'),
        entity.EntityDesignDetailProperty('Training cap', True, entity_property_name='TrainingCapacity'),
        entity.EntityDesignDetailProperty('Slots', True, transform_function=__get_slots)
    ],
    'character_short': [
        entity.EntityDesignDetailProperty('Rarity', False, entity_property_name='Rarity'),
        entity.EntityDesignDetailProperty('Ability', True, transform_function=__get_ability_stat),
        entity.EntityDesignDetailProperty('Collection', True, omit_if_none=True, transform_function=__get_collection_name)
    ],
    'collection_title': entity.EntityDesignDetailProperty('Title', False, entity_property_name=COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME),
    'collection_description': entity.EntityDesignDetailProperty('Description', False, entity_property_name='CollectionDescription'),
    'collection_long': [
        entity.EntityDesignDetailProperty('Combo Min...Max', True, omit_if_none=True, transform_function=__get_min_max_combo),
        entity.EntityDesignDetailProperty(__get_collection_perk, True, omit_if_none=True, transform_function=__get_enhancement),
        entity.EntityDesignDetailProperty(__get_members_count_display_name, True, omit_if_none=True, transform_function=__get_collection_member_names),
        entity.EntityDesignDetailProperty('Hyperlink', False, omit_if_none=True, transform_function=__get_collection_hyperlink)
    ],
    'collection_short': [
        entity.EntityDesignDetailProperty('Perk', False, omit_if_none=True, transform_function=__get_collection_perk),
        entity.EntityDesignDetailProperty('Member count', False, omit_if_none=True, transform_function=__get_collection_member_count)
    ]
}


async def init():
    pass





# Get stat for level:
# - get exponent 'p' by ProgressionType:
#   - Linear: p = 1.0
#   - EaseIn: p = 2.0
#   - EaseOut: p = 0.5
# - get min stat 'min' & max stat 'max'
# result = min + (max - min) * ((level - 1) / 39) ** p

# ---------- Testing ----------

#if __name__ == '__main__':
#    f = get_level_costs(20, 30)
#    test_crew = [('alpaco', 5)]
#    for (crew_name, level) in test_crew:
#        os.system('clear')
#        result = await get_char_design_details_by_name(crew_name, level, as_embed=False)
#        for line in result[0]:
#            print(line)
#        print('')
#        result = await get_prestige_from_info(crew_name, as_embed=False)
#        for line in result[0]:
#            print(line)
#        print('')
#        result = await get_prestige_to_info(crew_name, as_embed=False)
#        for line in result[0]:
#            print(line)
#        print('')
#        result = ''
