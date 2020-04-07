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










# ---------- Initilization ----------

__research_designs_cache = PssCache(
    RESEARCH_DESIGN_BASE_PATH,
    'ResearchDesigns',
    RESEARCH_DESIGN_KEY_NAME)










# ---------- Classes ----------

class ResearchDesignDetails(entity.LegacyEntityDesignDetails):
    def __init__(self, research_info: dict, researches_designs_data: dict = None):
        if not researches_designs_data:
            researches_designs_data = __research_designs_cache.get_data_dict3()

        self.__cost: str = _get_costs_from_research_info(research_info)
        self.__research_time_seconds: int = int(research_info['ResearchTime'])
        self.__required_lab_level: str = research_info['RequiredLabLevel']
        self.__required_research_design_id: str = research_info['RequiredResearchDesignId']

        self.__research_timedelta: timedelta = timedelta(seconds=self.__research_time_seconds)
        self.__duration: int = util.get_formatted_timedelta(self.__research_timedelta, include_relative_indicator=False)
        if self.__required_research_design_id != '0':
            self.__required_research_name = researches_designs_data[self.__required_research_design_id][RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
        else:
            self.__required_research_name = None

        details_long: List[Tuple[str, str]] = [
            ('Cost', self.__cost),
            ('Duration', self.__duration),
            ('Required LAB lvl', self.__required_lab_level),
            ('Required Research', self.__required_research_name)
        ]
        details_short: List[Tuple[str, str, bool]] = [
            (None, self.__cost, False),
            (None, self.__duration, False),
            ('LAB lvl', self.__required_lab_level, False)
        ]

        super().__init__(
            name=research_info[RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME],
            description=research_info['ResearchDescription'],
            details_long=details_long,
            details_short=details_short
        )


    @property
    def cost(self) -> str:
        return self.__cost

    @property
    def duration(self) -> int:
        return self.__duration

    @property
    def required_lab_level(self) -> str:
        return self.__required_lab_level

    @property
    def required_research_design_id(self) -> str:
        return list(self.__required_research_design_id)

    @property
    def required_research_name(self) -> str:
        return self.__required_research_name










# ---------- Helper functions ----------

def get_research_details_from_id_as_text(research_id: str, research_designs_data: dict = None) -> list:
    if not research_designs_data:
        research_designs_data = __research_designs_cache.get_data_dict3()

    research_design_details = ResearchDesignDetails(research_id, researches_designs_data=research_designs_data)
    return research_design_details.get_details_as_text_long()


def get_research_details_from_data_as_text(research_info: dict, research_designs_data: dict = None) -> list:
    if not research_designs_data:
        research_designs_data = __research_designs_cache.get_data_dict3()

    name = research_info[RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    description = research_info['ResearchDescription']
    costs = _get_costs_from_research_info(research_info)
    research_time_seconds = int(research_info['ResearchTime'])
    research_timedelta = timedelta(seconds=research_time_seconds)
    duration = util.get_formatted_timedelta(research_timedelta, include_relative_indicator=False)
    required_lab_level = research_info['RequiredLabLevel']
    required_research_design_id = research_info['RequiredResearchDesignId']
    if required_research_design_id != '0':
        required_research_name = research_designs_data[required_research_design_id][RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    else:
        required_research_name = None

    result = [f'**{name}**']
    result.append(f'_{description}_')
    result.append(f'Cost = {costs}')
    result.append(f'Duration = {duration}')
    result.append(f'Required LAB lvl = {required_lab_level}')
    if required_research_name:
        result.append(f'Required Research = {required_research_name}')

    return result


def get_research_details_short_from_id_as_text(research_id: str, research_designs_data: dict = None) -> list:
    if not research_designs_data:
        research_designs_data = __research_designs_cache.get_data_dict3()

    research_design_details = ResearchDesignDetails(research_id, researches_designs_data=research_designs_data)
    return research_design_details.get_details_as_text_short()


def get_research_details_short_from_data_as_text(research_info: dict) -> list:
    name = research_info[RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    costs = _get_costs_from_research_info(research_info)
    research_time_seconds = int(research_info['ResearchTime'])
    research_timedelta = timedelta(seconds=research_time_seconds)
    duration = util.get_formatted_timedelta(research_timedelta, include_relative_indicator=False)
    required_lab_level = research_info['RequiredLabLevel']
    return [f'**{name}**: {costs} - {duration} - LAB lvl {required_lab_level}']


def get_research_name_from_id(research_id: str, research_designs_data: dict = None) -> str:
    if research_id != '0':
        if not research_designs_data:
            research_designs_data = __research_designs_cache.get_data_dict3()

        research_info = research_designs_data[research_id]
        return research_info[RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    else:
        return None


def _get_costs_from_research_info(research_info: dict) -> str:
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
    if currency:
        currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[currency]
    else:
        currency_emoji = ''
    return f'{cost_reduced}{cost_multiplier} {currency_emoji}'


def _get_parents(research_info: dict, research_designs_data: dict) -> list:
    parent_research_design_id = research_info['RequiredResearchDesignId']
    if parent_research_design_id == '0':
        parent_research_design_id = None

    if parent_research_design_id is not None:
        parent_info = research_designs_data[parent_research_design_id]
        result = _get_parents(parent_info, research_designs_data)
        result.append(parent_info)
        return result
    else:
        return []






# ---------- Research info ----------

def get_research_design_details_by_id(research_design_id: str, research_designs_data: dict = None) -> ResearchDesignDetails:
    if research_design_id:
        if research_designs_data is None:
            research_designs_data = research_designs_retriever.get_data_dict3()

        if research_design_id and research_design_id in research_designs_data.keys():
            char_design_info = research_designs_data[research_design_id]
            char_design_details = ResearchDesignDetails(char_design_info, researches_designs_data=research_designs_data)
            return char_design_details

    return None


def get_research_infos_by_name(research_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[str], List[discord.Embed]]:
    pss_assert.valid_entity_name(research_name)

    research_designs_details = research_designs_retriever.get_entities_designs_infos_by_name(research_name, sorted_key_function=_get_key_for_research_sort)

    if not research_designs_details:
        return [f'Could not find a research named **{research_name}**.'], False
    else:
        if as_embed:
            return _get_research_infos_as_embed(research_designs_details), True
        else:
            return _get_research_infos_as_text(research_name, research_designs_details), True


def _get_research_infos(research_name: str, research_designs_data: dict = None):
    if research_designs_data is None:
        research_designs_data = __research_designs_cache.get_data_dict3()

    research_design_ids = _get_research_design_ids_from_name(research_name, research_designs_data=research_designs_data)
    result = [research_designs_data[research_design_id] for research_design_id in research_design_ids if research_design_id in research_designs_data.keys()]

    return result


def _get_research_design_ids_from_name(research_name: str, research_designs_data: dict = None):
    if research_designs_data is None:
        research_designs_data = __research_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(research_designs_data, RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME, research_name)
    return results


def _get_research_infos_as_embed(research_designs_details: List[ResearchDesignDetails]) -> List[discord.Embed]:
    result = [research_design_details.get_details_as_embed() for research_design_details in research_designs_details]
    return result


def _get_research_infos_as_text(research_name: str, research_designs_details: List[ResearchDesignDetails]) -> List[str]:
    lines = [f'Research stats for **{research_name}**']

    research_infos_count = len(research_designs_details)
    big_set = research_infos_count > 3

    for i, research_design_details in enumerate(research_designs_details):
        if big_set:
            lines.extend(research_design_details.get_details_as_text_short())
        else:
            lines.extend(research_design_details.get_details_as_text_long())
            if i < research_infos_count - 1:
                lines.append(settings.EMPTY_LINE)

    return lines


def _get_key_for_research_sort(research_info: dict, research_designs_data: dict) -> str:
    result = ''
    parent_infos = _get_parents(research_info, research_designs_data)
    if parent_infos:
        for parent_info in parent_infos:
            result += parent_info[RESEARCH_DESIGN_KEY_NAME].zfill(4)
    result += research_info[RESEARCH_DESIGN_KEY_NAME].zfill(4)
    return result










# ---------- Initilization ----------

research_designs_retriever = entity.NewEntityDesignsRetriever(
    RESEARCH_DESIGN_BASE_PATH,
    RESEARCH_DESIGN_KEY_NAME,
    RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='ResearchDesigns'
)
