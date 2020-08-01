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










# ---------- Classes ----------

class LegacyPrestigeDetails(entity.LegacyEntityDetails):
    def __init__(self, char_info: dict, prestige_infos: Dict[str, List[str]], error_message: str, title_template: str, sub_title_template: str):
        self.__char_design_name: str = char_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
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
    def __init__(self, char_from_info: dict, chars_data: dict, prestige_from_data: dict):
        chars_data = chars_data
        error = None
        prestige_infos = {}
        template_title = '**$char_design_name$** has **$count$** prestige combinations:'
        template_subtitle = 'To **$char_design_name$** with:'

        if prestige_from_data:
            for value in prestige_from_data.values():
                char_info_2_name = chars_data[value['CharacterDesignId2']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
                char_info_to_name = chars_data[value['ToCharacterDesignId']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
                prestige_infos.setdefault(char_info_to_name, []).append(char_info_2_name)
        else:
            if char_from_info['Rarity'] == 'Special':
                error = 'One cannot prestige **Special** crew.'
            elif char_from_info['Rarity'] == 'Legendary':
                error = 'One cannot prestige **Legendary** crew.'
            else:
                error = 'noone'

        super().__init__(char_from_info, prestige_infos, error, template_title, template_subtitle)





class LegacyPrestigeToDetails(LegacyPrestigeDetails):
    def __init__(self, char_to_info: dict, chars_data: dict, prestige_to_data: dict):
        chars_data = chars_data
        error = None
        prestige_infos = {}
        template_title = '**$char_design_name$** has **$count$** prestige recipes:'
        template_subtitle = '**$char_design_name$** with:'

        if prestige_to_data:
            prestige_recipes: Dict[str, Set[str]] = {}
            for value in prestige_to_data.values():
                char_1_design_name = chars_data[value['CharacterDesignId1']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
                char_2_design_name = chars_data[value['CharacterDesignId2']][CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
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
            if char_to_info['Rarity'] == 'Special':
                error = 'One cannot prestige to **Special** crew.'
            elif char_to_info['Rarity'] == 'Common':
                error = 'One cannot prestige to **Common** crew.'
            else:
                error = 'noone'

        super().__init__(char_to_info, prestige_infos, error, template_title, template_subtitle)


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










# ---------- Constants ----------

CHARACTER_DESIGN_BASE_PATH = 'CharacterService/ListAllCharacterDesigns2?languageKey=en'
CHARACTER_DESIGN_KEY_NAME = 'CharacterDesignId'
CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME = 'CharacterDesignName'

COLLECTION_DESIGN_BASE_PATH = 'CollectionService/ListAllCollectionDesigns?languageKey=en'
COLLECTION_DESIGN_KEY_NAME = 'CollectionDesignId'
COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME = 'CollectionName'

__PRESTIGE_FROM_BASE_PATH = f'CharacterService/PrestigeCharacterFrom?languagekey=en&characterDesignId='
__PRESTIGE_TO_BASE_PATH = f'CharacterService/PrestigeCharacterTo?languagekey=en&characterDesignId='










# ---------- Crew info ----------

def get_char_details_by_id(char_design_id: str, chars_data: entity.EntitiesData, collections_data: entity.EntitiesData, level: int = None) -> entity.EntityDetails:
    if char_design_id:
        if char_design_id and char_design_id in chars_data.keys():
            return __create_character_details_from_info(chars_data[char_design_id], chars_data, collections_data, level)
    return None


async def get_char_details_by_name(char_name: str, level: int, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(char_name, 'char_name', min_length=2)
    pss_assert.parameter_is_valid_integer(level, 'level', min_value=1, max_value=40, allow_none=True)

    chars_data = await characters_designs_retriever.get_data_dict3()
    char_info = await characters_designs_retriever.get_entity_info_by_name(char_name, chars_data)

    if char_info is None:
        return [f'Could not find a crew named **{char_name}**.'], False
    else:
        collections_data = await collections_designs_retriever.get_data_dict3()
        character_details = __create_character_details_from_info(char_info, None, collections_data, level)
        if as_embed:
            return (await character_details.get_details_as_embed()), True
        else:
            return (await character_details.__get_details_long_as_text()), True










# ---------- Collection Info ----------

async def get_collection_details_by_name(collection_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(collection_name, parameter_name='collection_name', allow_none_or_empty=True)

    print_all = not collection_name
    collections_data = await collections_designs_retriever.get_data_dict3()
    characters_data = await characters_designs_retriever.get_data_dict3()
    collections_designs_infos = []
    if print_all:
        collections_designs_infos = collections_data.values()
    else:
        collections_designs_infos.append(await collections_designs_retriever.get_entity_info_by_name(collection_name, collections_data))

    if collections_designs_infos is None:
        if print_all:
            return [f'An error occured upon retrieving collection info. Please try again later.'], False
        else:
            return [f'Could not find a collection named **{collection_name}**.'], False
    else:
        collections_designs_infos = sorted(collections_designs_infos, key=lambda x: x[COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME])
        collections_details = [__create_collection_details_from_info(collection_info, collections_data, characters_data) for collection_info in collections_designs_infos]
        if print_all:
            if as_embed:
                return collections_details.get_details_as_embed(), True
            else:
                long_details = []
                for collection_details in collections_details:
                    long_details.extend((await collection_details.__get_details_short_as_text()))
                long_details.append(__get_collection_hyperlink(None, None, None))
                return long_details, True
        else:
            if as_embed:
                return (await collections_details[0].get_details_as_embed()), True
            else:
                return (await collections_details[0].__get_details_long_as_text()), True










# ---------- Prestige from Info ----------

async def get_prestige_from_info(char_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(char_name, 'char_name', min_length=2)

    chars_data = await characters_designs_retriever.get_data_dict3()
    char_from_info = await characters_designs_retriever.get_entity_info_by_name(char_name, chars_data)

    if not char_from_info:
        return [f'Could not find a crew named **{char_name}**.'], False
    else:
        prestige_from_data = await _get_prestige_from_data(char_from_info)
        prestige_from_details = LegacyPrestigeFromDetails(char_from_info, chars_data, prestige_from_data)

        if as_embed:
            return prestige_from_details.get_details_as_embed(), True
        else:
            return prestige_from_details.get_details_as_text_long(), True


async def _get_prestige_from_data(char_info: dict) -> dict:
    if not char_info:
        return {}

    char_design_id = char_info[CHARACTER_DESIGN_KEY_NAME]
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

    chars_data = await characters_designs_retriever.get_data_dict3()
    char_to_info = await characters_designs_retriever.get_entity_info_by_name(char_name, chars_data)

    if not char_to_info:
        return [f'Could not find a crew named **{char_name}**.'], False
    else:
        prestige_to_data = await _get_prestige_to_data(char_to_info)
        prestige_to_details = LegacyPrestigeToDetails(char_to_info, chars_data, prestige_to_data)

        if as_embed:
            return prestige_to_details.get_details_as_embed(), True
        else:
            return prestige_to_details.get_details_as_text_long(), True


async def _get_prestige_to_data(char_info: dict) -> dict:
    if not char_info:
        return {}

    char_design_id = char_info[CHARACTER_DESIGN_KEY_NAME]
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










# ---------- Create EntityDetails ----------

def __create_character_details_from_info(character_info: entity.EntityInfo, characters_data: entity.EntitiesData, collections_data: entity.EntitiesData, level: int) -> entity.EntityDetails:
    return entity.EntityDetails(character_info, __properties['character_title'], __properties['character_description'], __properties['character_long'], __properties['character_short'], __properties['character_long'], characters_data, collections_data, level=level)


def __create_characters_details_list_from_infos(characters_designs_infos: List[entity.EntityInfo], characters_data: entity.EntitiesData, collections_data: entity.EntitiesData, level: int) -> List[entity.EntitiesData]:
    return [__create_character_details_from_info(character_info, characters_data, collections_data, level) for character_info in characters_designs_infos]


def __create_characters_details_collection_from_infos(characters_designs_infos: List[entity.EntityInfo], characters_data: entity.EntitiesData, collections_data: entity.EntitiesData, level: int) -> entity.EntityDetailsCollection:
    characters_details = __create_characters_details_list_from_infos(characters_designs_infos, characters_data, collections_data, level)
    result = entity.EntityDetailsCollection(characters_details, big_set_threshold=2)
    return result


def __create_collection_details_from_info(collection_info: entity.EntityInfo, collections_data: entity.EntitiesData, characters_data: entity.EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(collection_info, __properties['collection_title'], __properties['collection_description'], __properties['collection_long'], __properties['collection_short'], __properties['collection_long'], collections_data, characters_data)


def __create_collections_details_list_from_infos(collections_designs_infos: List[entity.EntityInfo], collections_data: entity.EntitiesData, characters_data: entity.EntitiesData) -> List[entity.EntitiesData]:
    return [__create_collection_details_from_info(collection_info, collections_data, characters_data) for collection_info in collections_designs_infos]


def __create_collections_details_collection_from_infos(collection_info: List[entity.EntityInfo], collections_data: entity.EntitiesData, characters_data: entity.EntitiesData) -> entity.EntityDetailsCollection:
    collections_details = __create_collections_details_list_from_infos(collection_info, collections_data, characters_data)
    result = entity.EntityDetailsCollection(collections_details, big_set_threshold=2)
    return result










# ---------- Transformation functions ----------

def __get_ability_stat(character_info: entity.EntityInfo, characters_data: entity.EntitiesData, collections_data: entity.EntitiesData, level: int, **kwargs) -> str:
    value = __get_stat(character_info, characters_data, collections_data, level, stat_name='SpecialAbilityArgument')
    if character_info['SpecialAbilityType']:
        special_ability = lookups.SPECIAL_ABILITIES_LOOKUP.get(character_info['SpecialAbilityType'], character_info['SpecialAbilityType'])
    else:
        special_ability is None
    if special_ability:
        result = f'{value} ({special_ability})'
    else:
        result = value
    return result


def __get_collection_member_count(collection_info: entity.EntityInfo, collections_data: entity.EntitiesData, characters_data: entity.EntitiesData, **kwargs) -> str:
    collection_id = collection_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_infos = [characters_data[char_id] for char_id in characters_data.keys() if characters_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = len(chars_designs_infos)
    return f'{result} members'


def __get_collection_member_names(collection_info: entity.EntityInfo, collections_data: entity.EntitiesData, characters_data: entity.EntitiesData, **kwargs) -> str:
    collection_id = collection_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_infos = [characters_data[char_id] for char_id in characters_data.keys() if characters_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = [char_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME] for char_info in chars_designs_infos]
    result.sort()
    return ', '.join(result)


def __get_collection_hyperlink(collection_info: entity.EntityInfo, collections_data: entity.EntitiesData, characters_data: entity.EntitiesData, **kwargs) -> str:
    return '<https://pixelstarships.fandom.com/wiki/Category:Crew_Collections>'


def __get_collection_perk(collection_info: entity.EntityInfo, collections_data: entity.EntitiesData, characters_data: entity.EntitiesData, **kwargs) -> str:
    enhancement_type = collection_info['EnhancementType']
    result = lookups.COLLECTION_PERK_LOOKUP.get(enhancement_type, enhancement_type)
    return result


def __get_crew_card_hyperlink(character_info: entity.EntityInfo, characters_data: entity.EntitiesData, collections_data: entity.EntitiesData, level: int, **kwargs) -> str:
    crew_name: str = character_info.get(CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME)
    if crew_name:
        crew_name_escaped = util.url_escape(crew_name)
        url = f'https://pixelperfectguide.com/crew/cards/?CrewName={crew_name_escaped}'
        result = f'<{url}>'
        return result
    else:
        return None


def __get_enhancement(collection_info: entity.EntityInfo, collections_data: entity.EntitiesData, characters_data: entity.EntitiesData, **kwargs) -> str:
    base_enhancement_value = collection_info['BaseEnhancementValue']
    step_enhancement_value = collection_info['StepEnhancementValue']
    result = f'{base_enhancement_value} (Base), {step_enhancement_value} (Step)'
    return result


def __get_level(character_info: entity.EntityInfo, characters_data: entity.EntitiesData, collections_data: entity.EntitiesData, level: int, **kwargs) -> str:
    if level is None:
        return None
    else:
        return str(level)


def __get_members_count_display_name(collection_info: entity.EntityInfo, collections_data: entity.EntitiesData, characters_data: entity.EntitiesData, **kwargs) -> str:
    collection_id = collection_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_infos = [characters_data[char_id] for char_id in characters_data.keys() if characters_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = f'Members ({len(chars_designs_infos)})'
    return result


def __get_min_max_combo(collection_info: entity.EntityInfo, collections_data: entity.EntitiesData, characters_data: entity.EntitiesData, **kwargs) -> str:
    min_combo = collection_info['MinCombo']
    max_combo = collection_info['MaxCombo']
    result = f'{min_combo}...{max_combo}'
    return result


def __get_slots(character_info: entity.EntityInfo, characters_data: entity.EntitiesData, collections_data: entity.EntitiesData, **kwargs) -> str:
    result = []
    equipment_mask = int(character_info['EquipmentMask'])
    for k in lookups.EQUIPMENT_MASK_LOOKUP.keys():
        if (equipment_mask & k) != 0:
            result.append(lookups.EQUIPMENT_MASK_LOOKUP[k])

    result = ', '.join(result) if result else '-'
    return result


def __get_speed(character_info: entity.EntityInfo, characters_data: entity.EntitiesData, collections_data: entity.EntitiesData, **kwargs) -> str:
    walk_speed = character_info['WalkingSpeed']
    run_speed = character_info['RunSpeed']
    result = f'{walk_speed}/{run_speed}'
    return result


def __get_stat(character_info: entity.EntityInfo, characters_data: entity.EntitiesData, collections_data: entity.EntitiesData, level: int, stat_name: str, **kwargs) -> str:
    is_special_stat = stat_name.lower().startswith('specialability')
    if is_special_stat:
        max_stat_name = 'SpecialAbilityFinalArgument'
    else:
        max_stat_name = f'Final{stat_name}'
    min_value = float(character_info[stat_name])
    max_value = float(character_info[max_stat_name])
    progression_type = character_info['ProgressionType']
    result = __get_stat_value(min_value, max_value, level, progression_type)
    return result










# ---------- Helper functions ----------

def __calculate_stat_value(min_value: float, max_value: float, level: int, progression_type: str) -> float:
    exponent = lookups.PROGRESSION_TYPES[progression_type]
    result = min_value + (max_value - min_value) * ((level - 1) / 39) ** exponent
    return result


def __get_collection_name(character_info: entity.EntityInfo, characters_data: entity.EntitiesData, collections_data: entity.EntitiesData, **kwargs) -> str:
    result = None
    collection_id = character_info[COLLECTION_DESIGN_KEY_NAME]
    if collection_id and int(collection_id):
        result = collections_data[collection_id][COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME]
    return result


def __get_stat_value(min_value: float, max_value: float, level: int, progression_type: str) -> str:
    if level is None or level < 1 or level > 40:
        return f'{min_value:0.1f} - {max_value:0.1f}'
    else:
        return f'{__calculate_stat_value(min_value, max_value, level, progression_type):0.1f}'










# ---------- Initilization ----------

__prestige_from_cache_dict = {}
__prestige_to_cache_dict = {}

characters_designs_retriever = entity.EntityRetriever(
    CHARACTER_DESIGN_BASE_PATH,
    CHARACTER_DESIGN_KEY_NAME,
    CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='CharacterDesigns'
)


collections_designs_retriever = entity.EntityRetriever(
    COLLECTION_DESIGN_BASE_PATH,
    COLLECTION_DESIGN_KEY_NAME,
    COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='CollectionDesigns'
)


__properties: Dict[str, Union[entity.EntityDetailProperty, List[entity.EntityDetailProperty]]] = {
    'character_title': entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME),
    'character_description': entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='CharacterDesignDescription'),
    'character_long': [
        entity.EntityDetailProperty('Level', True, transform_function=__get_level),
        entity.EntityDetailProperty('Rarity', True, entity_property_name='Rarity'),
        entity.EntityDetailProperty('Race', True, entity_property_name='RaceType'),
        entity.EntityDetailProperty('Collection', True, transform_function=__get_collection_name),
        entity.EntityDetailProperty('Gender', True, entity_property_name='GenderType'),
        entity.EntityDetailProperty('Ability', True, transform_function=__get_ability_stat),
        entity.EntityDetailProperty('HP', True, transform_function=__get_stat, stat_name='Hp'),
        entity.EntityDetailProperty('Attack', True, transform_function=__get_stat, stat_name='Attack'),
        entity.EntityDetailProperty('Repair', True, transform_function=__get_stat, stat_name='Repair'),
        entity.EntityDetailProperty('Pilot', True, transform_function=__get_stat, stat_name='Pilot'),
        entity.EntityDetailProperty('Science', True, transform_function=__get_stat, stat_name='Science'),
        entity.EntityDetailProperty('Engine', True, transform_function=__get_stat, stat_name='Engine'),
        entity.EntityDetailProperty('Weapon', True, transform_function=__get_stat, stat_name='Weapon'),
        entity.EntityDetailProperty('Walk/run speed', True, transform_function=__get_speed),
        entity.EntityDetailProperty('Fire resist', True, entity_property_name='FireResistance'),
        entity.EntityDetailProperty('Training cap', True, entity_property_name='TrainingCapacity'),
        entity.EntityDetailProperty('Slots', True, transform_function=__get_slots),
        entity.EntityDetailProperty('Roles', True, transform_function=__get_crew_card_hyperlink)
    ],
    'character_short': [
        entity.EntityDetailProperty('Rarity', False, entity_property_name='Rarity'),
        entity.EntityDetailProperty('Ability', True, transform_function=__get_ability_stat),
        entity.EntityDetailProperty('Collection', True, transform_function=__get_collection_name)
    ],
    'collection_title': entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME),
    'collection_description': entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='CollectionDescription'),
    'collection_long': [
        entity.EntityDetailProperty('Combo Min...Max', True, transform_function=__get_min_max_combo),
        entity.EntityDetailProperty(__get_collection_perk, True, transform_function=__get_enhancement),
        entity.EntityDetailProperty(__get_members_count_display_name, True, transform_function=__get_collection_member_names),
        entity.EntityDetailProperty('Hyperlink', False, transform_function=__get_collection_hyperlink)
    ],
    'collection_short': [
        entity.EntityDetailProperty('Perk', False, transform_function=__get_collection_perk),
        entity.EntityDetailProperty('Member count', False, transform_function=__get_collection_member_count)
    ]
}


async def init():
    pass
