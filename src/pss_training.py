#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import timedelta

from cache import PssCache
import pss_assert
import pss_core as core
import settings
import utility as util

# ---------- Constants ----------

TRAINING_DESIGN_BASE_PATH = 'TrainingService/ListAllTrainingDesigns2?languageKey=en'
TRAINING_DESIGN_KEY_NAME = 'TrainingDesignId'
TRAINING_DESIGN_DESCRIPTION_PROPERTY_NAME = 'TrainingName'










# ---------- Initilization ----------

__training_designs_cache = PssCache(
    TRAINING_DESIGN_BASE_PATH,
    'TrainingDesigns',
    TRAINING_DESIGN_KEY_NAME)









# ---------- Helper functions ----------

def get_training_details_from_id_as_text(training_id: str, training_designs_data: dict = None) -> list:
    if not training_designs_data:
        training_designs_data = __training_designs_cache.get_data_dict3()

    training_info = training_designs_data[training_id]
    return get_training_details_from_data_as_text(training_info, training_designs_data)


def get_training_details_from_data_as_text(training_info: dict, training_designs_data: dict = None) -> list:
    if not training_designs_data:
        training_designs_data = __training_designs_cache.get_data_dict3()

    name = training_info[TRAINING_DESIGN_DESCRIPTION_PROPERTY_NAME]

    result = [f'**{name}**']

    return result

def get_training_details_short_from_id_as_text(training_id: str, training_designs_data: dict = None) -> list:
    if not training_designs_data:
        training_designs_data = __training_designs_cache.get_data_dict3()

    training_info = training_designs_data[training_id]
    return get_training_details_short_from_data_as_text(training_info)


def get_training_details_short_from_data_as_text(training_info: dict) -> list:
    name = training_info[TRAINING_DESIGN_DESCRIPTION_PROPERTY_NAME]
    return [f'**{name}**:']


def _get_parents(training_info: dict, training_designs_data: dict) -> list:
    parent_training_design_id = training_info['RequiredTrainingDesignId']
    if parent_training_design_id == '0':
        parent_training_design_id = None

    if parent_training_design_id is not None:
        parent_info = training_designs_data[parent_training_design_id]
        result = _get_parents(parent_info, training_designs_data)
        result.append(parent_info)
        return result
    else:
        return []









# ---------- Training info ----------

def get_training_details_from_name(training_name: str, as_embed: bool = settings.USE_EMBEDS):
    pss_assert.valid_entity_name(training_name)

    training_designs_data = __training_designs_cache.get_data_dict3()
    training_infos = _get_training_infos(training_name, training_designs_data=training_designs_data)

    if not training_infos:
        return [f'Could not find a training named **{training_name}**.'], False
    else:
        if as_embed:
            return _get_training_info_as_embed(training_name, training_infos, training_designs_data), True
        else:
            return _get_training_info_as_text(training_name, training_infos, training_designs_data), True


def _get_training_infos(training_name: str, training_designs_data: dict = None):
    if training_designs_data is None:
        training_designs_data = __training_designs_cache.get_data_dict3()

    training_design_ids = _get_training_design_ids_from_name(training_name, training_designs_data=training_designs_data)
    result = [training_designs_data[training_design_id] for training_design_id in training_design_ids if training_design_id in training_designs_data.keys()]

    return result


def _get_training_design_ids_from_name(training_name: str, training_designs_data: dict = None):
    if training_designs_data is None:
        training_designs_data = __training_designs_cache.get_data_dict3()

    results = core.get_ids_from_property_value(training_designs_data, TRAINING_DESIGN_DESCRIPTION_PROPERTY_NAME, training_name)
    return results


def _get_training_info_as_embed(training_name: str, training_infos: dict, training_designs_data: dict):
    return ''


def _get_training_info_as_text(training_name: str, training_infos: dict, training_designs_data: dict):
    lines = [f'**Training stats for \'{training_name}\'**']
    training_infos = sorted(training_infos, key=lambda training_info: (
        _get_key_for_training_sort(training_info, training_designs_data)
    ))

    training_infos_count = len(training_infos)
    big_set = training_infos_count > 2

    for i, training_info in enumerate(training_infos):
        if big_set:
            lines.extend(get_training_details_short_from_data_as_text(training_info))
        else:
            lines.extend(get_training_details_from_data_as_text(training_info, training_designs_data))
            if i < training_infos_count - 1:
                lines.append(settings.EMPTY_LINE)

    return lines


def _get_key_for_training_sort(training_info: dict, training_designs_data: dict) -> str:
    result = ''
    parent_infos = _get_parents(training_info, training_designs_data)
    if parent_infos:
        for parent_info in parent_infos:
            result += parent_info[TRAINING_DESIGN_KEY_NAME].zfill(4)
    result += training_info[TRAINING_DESIGN_KEY_NAME].zfill(4)
    return result