#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import timedelta
import discord
from typing import Dict, List, Tuple, Union

from cache import PssCache
import pss_assert
import pss_core as core
import pss_entity as entity
import pss_lookups as lookups
import settings
import utility as util










# ---------- Constants ----------

RESEARCH_DESIGN_BASE_PATH = 'ResearchService/ListAllResearchDesigns2?languageKey=en'
RESEARCH_DESIGN_KEY_NAME = 'ResearchDesignId'
RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ResearchName'










# ---------- Research info ----------

def get_research_design_details_by_id(research_design_id: str, researches_designs_data: dict) -> entity.EntityDesignDetails:
    if research_design_id:
        if research_design_id and research_design_id in researches_designs_data.keys():
            research_design_info = researches_designs_data[research_design_id]
            research_design_details = __create_research_design_data_from_info(research_design_info, researches_designs_data)
            return research_design_details
    return None


async def get_research_infos_by_name(research_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[str], List[discord.Embed]]:
    pss_assert.valid_entity_name(research_name)

    researches_designs_data = await researches_designs_retriever.get_data_dict3()
    researches_designs_infos = await researches_designs_retriever.get_entities_designs_infos_by_name(research_name, entities_designs_data=researches_designs_data, sorted_key_function=_get_key_for_research_sort)

    if not researches_designs_infos:
        return [f'Could not find a research named **{research_name}**.'], False
    else:
        researches_designs_details = __create_researches_designs_details_collection_from_infos(researches_designs_infos, researches_designs_data)
        if as_embed:
            return (await researches_designs_details.get_entity_details_as_embed()), True
        else:
            return (await researches_designs_details.get_entity_details_as_text()), True


def _get_key_for_research_sort(research_info: dict, researches_designs_data: dict) -> str:
    result = ''
    parent_infos = _get_parents(research_info, researches_designs_data)
    if parent_infos:
        for parent_info in parent_infos:
            result += parent_info[RESEARCH_DESIGN_KEY_NAME].zfill(4)
    result += research_info[RESEARCH_DESIGN_KEY_NAME].zfill(4)
    return result










# ---------- Create EntityDesignDetails ----------

def __create_research_design_data_from_info(research_design_info: entity.EntityDesignInfo, researches_designs_data: entity.EntitiesDesignsData) -> entity.EntityDesignDetails:
    return entity.EntityDesignDetails(research_design_info, __properties['title'], __properties['description'], __properties['long'], __properties['short'], __properties['short'], researches_designs_data)


def __create_researches_designs_data_list_from_infos(researches_designs_infos: List[entity.EntityDesignInfo], researches_designs_data: entity.EntitiesDesignsData) -> List[entity.EntityDesignDetails]:
    return [__create_research_design_data_from_info(item_design_info, researches_designs_data) for item_design_info in researches_designs_infos]


def __create_researches_designs_details_collection_from_infos(researches_designs_infos: List[entity.EntityDesignInfo], researches_designs_data: entity.EntitiesDesignsData) -> entity.EntityDesignDetailsCollection:
    researches_designs_details = __create_researches_designs_data_list_from_infos(researches_designs_infos, researches_designs_data)
    result = entity.EntityDesignDetailsCollection(researches_designs_details, big_set_threshold=3)
    return result










# ---------- Transformation functions ----------

def __get_costs(research_design_info: entity.EntityDesignInfo, researches_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    bux_cost = int(research_design_info['StarbuxCost'])
    gas_cost = int(research_design_info['GasCost'])

    if bux_cost:
        cost = bux_cost
        currency = 'starbux'
    elif gas_cost:
        cost = gas_cost
        currency = 'gas'
    else:
        cost = 0
        currency = ''

    cost_reduced, cost_multiplier = util.get_reduced_number(cost)
    currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP.get(currency, '')
    result = f'{cost_reduced}{cost_multiplier} {currency_emoji}'
    return result


def __get_duration(research_design_info: entity.EntityDesignInfo, researches_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    seconds = int(research_design_info['ResearchTime'])
    result = util.get_formatted_timedelta(timedelta(seconds=seconds), include_relative_indicator=False)
    return result


def __get_required_research_name(research_design_info: entity.EntityDesignInfo, researches_designs_data: entity.EntitiesDesignsData, **kwargs) -> str:
    required_research_design_id = research_design_info['RequiredResearchDesignId']
    if required_research_design_id != '0':
        result = researches_designs_data[required_research_design_id][RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    else:
        result = None
    return result










# ---------- Helper functions ----------

def get_research_name_from_id(research_id: str, researches_designs_data: dict) -> str:
    if research_id != '0':
        research_info = researches_designs_data[research_id]
        return research_info[RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    else:
        return None


def _get_parents(research_info: dict, researches_designs_data: dict) -> list:
    parent_research_design_id = research_info['RequiredResearchDesignId']
    if parent_research_design_id == '0':
        parent_research_design_id = None

    if parent_research_design_id is not None:
        parent_info = researches_designs_data[parent_research_design_id]
        result = _get_parents(parent_info, researches_designs_data)
        result.append(parent_info)
        return result
    else:
        return []










# ---------- Initilization ----------

researches_designs_retriever = entity.EntityDesignsRetriever(
    RESEARCH_DESIGN_BASE_PATH,
    RESEARCH_DESIGN_KEY_NAME,
    RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='ResearchDesigns'
)

__properties = {
    'title': entity.EntityDesignDetailProperty('Title', False, omit_if_none=False, entity_property_name=RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME),
    'description': entity.EntityDesignDetailProperty('Description', False, omit_if_none=False, entity_property_name='ResearchDescription'),
    'long': [
        entity.EntityDesignDetailProperty('Cost', True, transform_function=__get_costs),
        entity.EntityDesignDetailProperty('Duration', True, transform_function=__get_duration),
        entity.EntityDesignDetailProperty('Required LAB lvl', True, entity_property_name='RequiredLabLevel'),
        entity.EntityDesignDetailProperty('Required Research', True, transform_function=__get_required_research_name)
    ],
    'short': [
        entity.EntityDesignDetailProperty('Cost', False, transform_function=__get_costs),
        entity.EntityDesignDetailProperty('Duration', False, transform_function=__get_duration),
        entity.EntityDesignDetailProperty('LAB lvl', True, entity_property_name='RequiredLabLevel')
    ]
}
