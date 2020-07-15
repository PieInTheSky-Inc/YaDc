#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import timedelta
import discord
from typing import Callable, Dict, List, Tuple, Union

from cache import PssCache
import emojis
import pss_assert
import pss_core as core
import pss_entity as entity
import pss_item as item
import pss_lookups as lookups
import pss_research as research
import settings
import utility as util

# ---------- Constants ----------

TRAINING_DESIGN_BASE_PATH = 'TrainingService/ListAllTrainingDesigns2?languageKey=en'
TRAINING_DESIGN_KEY_NAME = 'TrainingDesignId'
TRAINING_DESIGN_DESCRIPTION_PROPERTY_NAME = 'TrainingName'

BASE_STATS = lookups.STATS_LEFT + lookups.STATS_RIGHT










# ---------- Training info ----------

async def get_training_details_from_name(training_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(training_name)

    trainings_designs_data = await trainings_designs_retriever.get_data_dict3()
    training_infos = await trainings_designs_retriever.get_entities_designs_infos_by_name(training_name, trainings_designs_data)
    items_designs_data = await item.items_designs_retriever.get_data_dict3()
    researches_designs_data = await research.researches_designs_retriever.get_data_dict3()
    trainings_details = __create_training_design_details_list_from_infos(training_infos, trainings_designs_data, items_designs_data, researches_designs_data)

    if not training_infos:
        return [f'Could not find a training named **{training_name}**.'], False
    else:
        if as_embed:
            return await _get_training_info_as_embed(training_name, trainings_details), True
        else:
            return await _get_training_info_as_text(training_name, trainings_details), True


async def _get_training_info_as_embed(training_name: str, trainings_details: List[entity.EntityDesignDetails]) -> discord.Embed:
    result = [(await training_details.get_details_as_embed()) for training_details in trainings_details]
    return result


async def _get_training_info_as_text(training_name: str, trainings_details: List[entity.EntityDesignDetails]) -> List[str]:
    trainings_details_count = len(trainings_details)

    lines = [f'Training stats for **{training_name}**']
    for i, training_details in enumerate(trainings_details):
        if trainings_details_count > 2:
            lines.extend(await training_details.get_details_as_text_short())
        else:
            lines.extend(await training_details.get_details_as_text_long())
            if i < trainings_details_count - 1:
                lines.append(settings.EMPTY_LINE)

    return lines










# ---------- Helper functions ----------

def __create_training_design_details_from_info(training_design_info: entity.EntityDesignInfo, trainings_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData) -> entity.EntityDesignDetails:
    return entity.EntityDesignDetails(training_design_info, __properties['title'], __properties['description'], __properties['long'], __properties['short'], __properties['long'], trainings_designs_data, items_designs_data, researches_designs_data)


def __create_training_design_details_list_from_infos(trainings_designs_infos: List[entity.EntityDesignInfo], trainings_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData) -> List[entity.EntitiesDesignsData]:
    return [__create_training_design_details_from_info(training_design_info, trainings_designs_data, items_designs_data, researches_designs_data) for training_design_info in trainings_designs_infos]


def __get_costs(training_design_info: entity.EntityDesignInfo, trainings_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    cost = int(training_design_info['MineralCost'])
    if cost:
        cost_compact = util.get_reduced_number_compact(cost)
        result = f'{cost_compact} {emojis.pss_min_big}'
    else:
        result = None
    return result


def __get_duration(training_design_info: entity.EntityDesignInfo, trainings_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    seconds = int(training_design_info['Duration'])
    if seconds:
        result = util.get_formatted_duration(seconds, include_relative_indicator=False)
    else:
        result = 'Instant'
    return result


def __get_fatigue(training_design_info: entity.EntityDesignInfo, trainings_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    fatigue = int(training_design_info['Fatigue'])
    if fatigue:
        result = f'{fatigue}h'
    else:
        result = None
    return result


def __get_required_research(training_design_info: entity.EntityDesignInfo, trainings_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    required_research_id = training_design_info['RequiredResearchDesignId']
    result = research.get_research_name_from_id(required_research_id, researches_designs_data)
    return result


def __get_stat_chances(training_design_info: entity.EntityDesignInfo, trainings_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    chances = []
    max_chance_value = 0
    result = []
    for stat_name in BASE_STATS:
        stat_chance = _get_stat_chance(stat_name, training_design_info)
        if stat_chance is not None:
            chances.append(stat_chance)

    if chances:
        chance_values = [stat_chance[2] for stat_chance in chances]
        max_chance_value = max(chance_values)
        result = [_get_stat_chance_as_text(*stat_chance) for stat_chance in chances if stat_chance[2] == max_chance_value]
        result.extend([_get_stat_chance_as_text(*stat_chance) for stat_chance in chances if stat_chance[2] != max_chance_value])

    xp_stat_chance = _get_stat_chance('Xp', training_design_info, guaranteed=True)
    result.append(_get_stat_chance_as_text(*xp_stat_chance))

    return ' '.join(result)


async def __get_training_item_name(training_design_info: entity.EntityDesignInfo, trainings_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    training_id = training_design_info[TRAINING_DESIGN_KEY_NAME]
    result = await item.get_item_details_short_by_training_id(training_id, items_designs_data)
    return ''.join(result)


def __get_training_room(training_design_info: entity.EntityDesignInfo, trainings_designs_data: entity.EntitiesDesignsData, items_designs_data: entity.EntitiesDesignsData, researches_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    required_room_level = training_design_info['RequiredRoomLevel']
    training_room_type = int(training_design_info['Rank'])
    room_name, _ = _get_room_names(training_room_type)
    if room_name:
        result = f'{room_name} lvl {required_room_level}'
    else:
        result = None
    return result









def _get_key_for_training_sort(training_info: dict, trainings_designs_data: dict) -> str:
    result = ''
    parent_infos = _get_parents(training_info, trainings_designs_data)
    if parent_infos:
        for parent_info in parent_infos:
            result += parent_info[TRAINING_DESIGN_KEY_NAME].zfill(4)
    result += training_info[TRAINING_DESIGN_KEY_NAME].zfill(4)
    return result


def _get_parents(training_info: dict, trainings_designs_data: dict) -> list:
    parent_training_design_id = training_info['RequiredTrainingDesignId']
    if parent_training_design_id == '0':
        parent_training_design_id = None

    if parent_training_design_id is not None:
        parent_info = trainings_designs_data[parent_training_design_id]
        result = _get_parents(parent_info, trainings_designs_data)
        result.append(parent_info)
        return result
    else:
        return []


def _get_stat_chance(stat_name: str, training_info: dict, guaranteed: bool = False) -> (str, str, str, str):
    if stat_name and training_info:
        chance_name = f'{stat_name}Chance'
        if chance_name in training_info.keys():
            stat_chance = int(training_info[chance_name])
            if stat_chance > 0:
                stat_emoji = lookups.STAT_EMOJI_LOOKUP[stat_name]
                stat_unit = lookups.STAT_UNITS_LOOKUP[stat_name]
                operator = '' if guaranteed else '\u2264'
                return (stat_emoji, operator, stat_chance, stat_unit)
    return None


def _get_stat_chance_as_text(stat_emoji: str, operator: str, stat_chance: str, stat_unit: str) -> str:
    return f'{stat_emoji} {operator}{stat_chance}{stat_unit}'


def _get_room_names(training_room_type: int) -> Tuple[str, str]:
    return lookups.TRAINING_RANK_ROOM_LOOKUP.get(training_room_type, (None, None))










# ---------- Initilization ----------

trainings_designs_retriever = entity.EntityDesignsRetriever(
    TRAINING_DESIGN_BASE_PATH,
    TRAINING_DESIGN_KEY_NAME,
    TRAINING_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='TrainingDesigns',
    sorted_key_function=_get_key_for_training_sort
)


__properties: Dict[str, Union[entity.EntityDesignDetailProperty, List[entity.EntityDesignDetailProperty]]] = {
    'title': entity.EntityDesignDetailProperty('Title', False, omit_if_none=False, entity_property_name=TRAINING_DESIGN_DESCRIPTION_PROPERTY_NAME),
    'description': entity.EntityDesignDetailProperty('Description', False, omit_if_none=False, entity_property_name='TrainingDescription'),
    'long': [
        entity.EntityDesignDetailProperty('Duration', True, transform_function=__get_duration),
        entity.EntityDesignDetailProperty('Cost', True, transform_function=__get_costs),
        entity.EntityDesignDetailProperty('Fatigue', True, transform_function=__get_fatigue),
        entity.EntityDesignDetailProperty('Training room', True, transform_function=__get_training_room),
        entity.EntityDesignDetailProperty('Research required', True, transform_function=__get_required_research),
        entity.EntityDesignDetailProperty('Consumable', True, transform_function=__get_training_item_name),
        entity.EntityDesignDetailProperty('Results', True, transform_function=__get_stat_chances)
    ],
    'short': [
        entity.EntityDesignDetailProperty('Level', False, transform_function=__get_stat_chances),
    ]
}