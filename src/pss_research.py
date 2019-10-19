#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import timedelta

from cache import PssCache
import pss_assert
import pss_core as core
import pss_lookups as lookups
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





# ---------- Helper functions ----------

def get_research_details_from_id_as_text(research_id: str, research_designs_data: dict = None) -> list:
    if not research_designs_data:
        research_designs_data = __research_designs_cache.get_data_dict3()

    research_info = research_designs_data[research_id]
    return get_research_details_from_data_as_text(research_info, research_designs_data)


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
    result.append(description)
    result.append(f'Cost: {costs}')
    result.append(f'Duration: {duration}')
    result.append(f'Required LAB lvl: {required_lab_level}')
    if required_research_name:
        result.append(f'Required Research: {required_research_name}')

    return result


def get_research_details_short_from_id_as_text(research_id: str, research_designs_data: dict = None) -> list:
    if not research_designs_data:
        research_designs_data = __research_designs_cache.get_data_dict3()

    research_info = research_designs_data[research_id]
    return get_research_details_short_from_data_as_text(research_info)


def get_research_details_short_from_data_as_text(research_info: dict) -> list:
    name = research_info[RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    costs = _get_costs_from_research_info(research_info)
    research_time_seconds = int(research_info['ResearchTime'])
    research_timedelta = timedelta(seconds=research_time_seconds)
    duration = util.get_formatted_timedelta(research_timedelta, include_relative_indicator=False)
    required_lab_level = research_info['RequiredLabLevel']
    return [f'**{name}**: {costs} - {duration} - LAB lvl {required_lab_level}']


def _get_costs_from_research_info(research_info: dict) -> (int, str):
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

def get_research_details_from_name(research_name: str, as_embed: bool = False):
    pss_assert.valid_entity_name(research_name)

    research_designs_data = __research_designs_cache.get_data_dict3()
    research_infos = _get_research_infos(research_name, research_designs_data=research_designs_data)

    if not research_infos:
        return [f'Could not find a research named **{research_name}**.'], False
    else:
        if as_embed:
            return _get_research_info_as_embed(research_name, research_infos, research_designs_data), True
        else:
            return _get_research_info_as_text(research_name, research_infos, research_designs_data), True


def _get_research_infos(research_name: str, research_designs_data: dict = None, return_on_first: bool = False):
    if research_designs_data is None:
        research_designs_data = __research_designs_cache.get_data_dict3()

    research_design_ids = _get_research_design_ids_from_name(research_name, research_designs_data=research_designs_data, return_on_first=return_on_first)
    result = [research_designs_data[research_design_id] for research_design_id in research_design_ids if research_design_id in research_designs_data.keys()]

    return result


def _get_research_design_ids_from_name(research_name: str, research_designs_data: dict = None, return_on_first: bool = False):
    if research_designs_data is None:
        research_designs_data = __research_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(research_designs_data, RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME, research_name, return_on_first=return_on_first)
    return results


def _get_research_info_as_embed(research_name: str, research_infos: dict, research_designs_data: dict):
    return ''


def _get_research_info_as_text(research_name: str, research_infos: dict, research_designs_data: dict):
    lines = [f'**Research stats for \'{research_name}\'**']
    research_infos = sorted(research_infos, key=lambda research_info: (
        _get_key_for_research_sort(research_info, research_designs_data)
    ))

    research_infos_count = len(research_infos)
    big_set = research_infos_count > 3

    for i, research_info in enumerate(research_infos):
        if big_set:
            lines.extend(get_research_details_short_from_data_as_text(research_info))
        else:
            lines.extend(get_research_details_from_data_as_text(research_info, research_designs_data))
            if i < research_infos_count - 1:
                lines.append(core.EMPTY_LINE)

    return lines


def _get_key_for_research_sort(research_info: dict, research_designs_data: dict) -> str:
    result = ''
    parent_infos = _get_parents(research_info, research_designs_data)
    if parent_infos:
        for parent_info in parent_infos:
            result += parent_info[RESEARCH_DESIGN_KEY_NAME].zfill(4)
    result += research_info[RESEARCH_DESIGN_KEY_NAME].zfill(4)
    return result
