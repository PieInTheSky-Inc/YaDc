#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import timedelta

from cache import PssCache
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
    cost, currency = _get_costs_from_research_info(research_info)
    cost_reduced = util.get_reduced_number(cost)
    if currency:
        currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP[currency]
    else:
        currency_emoji = ''
    research_time_seconds = int(research_info['ResearchTime'])
    research_timedelta = timedelta(seconds=research_time_seconds)
    duration = util.get_formatted_timedelta(research_timedelta, include_relative_indicator=False)
    required_lab_level = research_info['RequiredLabLevel']
    required_research_design_id = research_info['RequiredResearchDesignId']
    if required_research_design_id > 0:
        required_research_name = research_designs_data[required_research_design_id][RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    else:
        required_research_name = None

    result = [name]
    result.append(description)
    result.append(f'Cost: {cost_reduced} {currency_emoji}')
    result.append(f'Duration: {duration}')
    result.append(f'Required LAB lvl: {required_lab_level}')
    if required_research_name:
        result.append(f'Required Research: {required_research_name}')

    return []


def _get_costs_from_research_info(research_info: dict) -> (int, str):
    bux_cost = int(research_info['StarbuxCost'])
    gas_cost = int(research_info['GasCost'])
    if bux_cost:
        return bux_cost, 'starbux'
    elif gas_cost:
        return gas_cost, 'gas'
    else:
        return 0, ''





# ---------- Research info ----------

def get_research_details_from_name(research_name: str, as_embed: bool = False):
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

    for item_info in research_infos:
        lines.extend(get_research_details_from_data_as_text(item_info, research_designs_data))
        lines.append('')

    return lines


