#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import timedelta
import discord
import discord.ext.commands as commands
from typing import Dict, List, Tuple, Union

from cache import PssCache
import pss_assert
import pss_core as core
import pss_entity as entity
import pss_lookups as lookups
import pss_sprites as sprites
import settings
import utility as util










# ---------- Constants ----------

RESEARCH_DESIGN_BASE_PATH = 'ResearchService/ListAllResearchDesigns2?languageKey=en'
RESEARCH_DESIGN_KEY_NAME = 'ResearchDesignId'
RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ResearchName'










# ---------- Research info ----------

def get_research_details_by_id(research_design_id: str, researches_data: dict) -> entity.EntityDetails:
    if research_design_id:
        if research_design_id and research_design_id in researches_data.keys():
            research_info = researches_data[research_design_id]
            research_details = __create_research_design_data_from_info(research_info, researches_data)
            return research_details
    return None


async def get_research_infos_by_name(research_name: str, ctx: commands.Context, as_embed: bool = settings.USE_EMBEDS) -> Union[List[str], List[discord.Embed]]:
    pss_assert.valid_entity_name(research_name)

    researches_data = await researches_designs_retriever.get_data_dict3()
    researches_designs_infos = await researches_designs_retriever.get_entities_infos_by_name(research_name, entities_data=researches_data, sorted_key_function=_get_key_for_research_sort)

    if not researches_designs_infos:
        return [f'Could not find a research named **{research_name}**.'], False
    else:
        researches_details = __create_researches_details_collection_from_infos(researches_designs_infos, researches_data)
        if as_embed:
            return (await researches_details.get_entity_details_as_embed(ctx)), True
        else:
            return (await researches_details.get_entity_details_as_text()), True


def _get_key_for_research_sort(research_info: dict, researches_data: dict) -> str:
    result = ''
    parent_infos = _get_parents(research_info, researches_data)
    if parent_infos:
        for parent_info in parent_infos:
            result += parent_info[RESEARCH_DESIGN_KEY_NAME].zfill(4)
    result += research_info[RESEARCH_DESIGN_KEY_NAME].zfill(4)
    return result










# ---------- Create EntityDetails ----------

def __create_research_design_data_from_info(research_info: entity.EntityInfo, researches_data: entity.EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(research_info, __properties['title'], __properties['description'], __properties['properties'], __properties['embed_settings'], researches_data)


def __create_researches_data_list_from_infos(researches_designs_infos: List[entity.EntityInfo], researches_data: entity.EntitiesData) -> List[entity.EntityDetails]:
    return [__create_research_design_data_from_info(item_info, researches_data) for item_info in researches_designs_infos]


def __create_researches_details_collection_from_infos(researches_designs_infos: List[entity.EntityInfo], researches_data: entity.EntitiesData) -> entity.EntityDetailsCollection:
    researches_details = __create_researches_data_list_from_infos(researches_designs_infos, researches_data)
    result = entity.EntityDetailsCollection(researches_details, big_set_threshold=3)
    return result










# ---------- Transformation functions ----------

def __get_costs(research_info: entity.EntityInfo, researches_data: entity.EntitiesData, **kwargs) -> str:
    bux_cost = int(research_info['StarbuxCost'])
    gas_cost = int(research_info['GasCost'])

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


def __get_duration(research_info: entity.EntityInfo, researches_data: entity.EntitiesData, **kwargs) -> str:
    seconds = int(research_info['ResearchTime'])
    result = util.get_formatted_timedelta(timedelta(seconds=seconds), include_relative_indicator=False)
    return result


def __get_required_research_name(research_info: entity.EntityInfo, researches_data: entity.EntitiesData, **kwargs) -> str:
    required_research_design_id = research_info['RequiredResearchDesignId']
    if required_research_design_id != '0':
        result = researches_data[required_research_design_id][RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    else:
        result = None
    return result










# ---------- Helper functions ----------

def get_research_name_from_id(research_id: str, researches_data: dict) -> str:
    if research_id != '0':
        research_info = researches_data[research_id]
        return research_info[RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    else:
        return None


def _get_parents(research_info: dict, researches_data: dict) -> list:
    parent_research_design_id = research_info['RequiredResearchDesignId']
    if parent_research_design_id == '0':
        parent_research_design_id = None

    if parent_research_design_id is not None:
        parent_info = researches_data[parent_research_design_id]
        result = _get_parents(parent_info, researches_data)
        result.append(parent_info)
        return result
    else:
        return []










# ---------- Initilization ----------

researches_designs_retriever = entity.EntityRetriever(
    RESEARCH_DESIGN_BASE_PATH,
    RESEARCH_DESIGN_KEY_NAME,
    RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='ResearchDesigns'
)

__properties = {
    'title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME)
    ),
    'description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='ResearchDescription'),
        property_short=entity.NO_PROPERTY
    ),
    'properties': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Cost', True, transform_function=__get_costs),
            entity.EntityDetailProperty('Duration', True, transform_function=__get_duration),
            entity.EntityDetailProperty('Required LAB lvl', True, entity_property_name='RequiredLabLevel'),
            entity.EntityDetailProperty('Required Research', True, transform_function=__get_required_research_name)
        ],
        properties_short=[
            entity.EntityDetailProperty('Cost', False, transform_function=__get_costs),
            entity.EntityDetailProperty('Duration', False, transform_function=__get_duration),
            entity.EntityDetailProperty('LAB lvl', True, entity_property_name='RequiredLabLevel')
        ],
        properties_mini=[]
    ),
    'embed_settings': {
        'thumbnail_url': entity.EntityDetailProperty('thumbnail_url', False, entity_property_name='LogoSpriteId', transform_function=sprites.get_download_sprite_link_by_property)
    }
}
