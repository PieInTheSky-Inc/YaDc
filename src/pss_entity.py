#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from abc import ABC, abstractstaticmethod
from discord import Embed
from typing import Callable, List, Tuple

from cache import PssCache
import pss_core as core


class EntityDesignDetails(object):
    def __init__(self, name: str = None, description: str = None, details_long: List[Tuple[str, str]] = None, details_short: List[Tuple[str, str, bool]] = None):
        self.__name: str = name
        self.__description: str = description
        self.__details_long: List[Tuple[str, str]] = details_long or []
        self.__details_short: List[Tuple[str, str, bool]] = details_short or []


    @property
    def description(self) -> str:
        return self.__description

    @property
    def details_long(self) -> List[Tuple[str, str]]:
        return list(self.__details_long)

    @property
    def details_short(self) -> List[Tuple[str, str, bool]]:
        return list(self.__details_short)

    @property
    def name(self) -> str:
        return self.__name


    def get_details_as_embed(self) -> Embed:
        return EntityDesignDetails._get_details_as_embed(self.name, self.description, self.details_long)


    def get_details_as_text_long(self) -> List[str]:
        return EntityDesignDetails._get_details_as_text_long(self.name, self.description, self.details_long)


    def get_details_as_text_short(self) -> List[str]:
        return EntityDesignDetails._get_details_as_text_short(self.name, self.details_short)


    @staticmethod
    def _get_details_as_embed(title: str, description: str, details: List[Tuple[str, str]]) -> Embed:
        result = Embed()
        if title:
            result.title = title
        if description:
            result.description = description
        if details:
            for (detail_name, detail_value) in details:
                result.add_field(name=detail_name, value=detail_value)
        return result


    @staticmethod
    def _get_details_as_text_long(title: str, description: str, details: List[Tuple[str,str]]) -> List[str]:
        result = []
        if title:
            result.append(f'**{title}**')
        if description:
            result.append(f'_{description}_')
        if details:
            for (detail_name, detail_value) in details:
                if detail_value:
                    result.append(f'{detail_name} = {detail_value}')
        return result


    @staticmethod
    def _get_details_as_text_short(title: str, details: List[Tuple[str,str]]) -> List[str]:
        result = []
        if title:
            result.append(title)
        if details:
            result_details = []
            for (detail_name, detail_value, include_detail_name) in details:
                if detail_value:
                    if include_detail_name and detail_name:
                        result_details.append(f'{detail_name}: {detail_value}')
                    else:
                        result_details.append(detail_value)
            result.append(f'({", ".join(result_details)})')
        result = [' '.join(result)]
        return result










class EntityDesignsRetriever:
    def __init__(self, entity_design_base_path: str, entity_design_key_name: str, entity_design_description_property_name: str, cache_name: str = None, sorted_key_function: Callable[[dict, dict], str] = None, fix_data_delegate: Callable[[str], str] = None):
        self.__cache_name: str = cache_name or ''
        self.__base_path: str = entity_design_base_path
        self.__key_name: str = entity_design_key_name
        self.__description_property_name: str = entity_design_description_property_name
        self.__sorted_key_function: Callable[[dict, dict], str] = sorted_key_function
        self.__fix_data_delegate = fix_data_delegate

        self.__cache = PssCache(
            self.__base_path,
            self.__cache_name,
            key_name=self.__key_name
        )


    def get_data_dict3(self) -> dict:
        return self.__cache.get_data_dict3()


    def get_entity_infos_by_name(self, entity_name: str, entity_designs_data: dict = None, sorted_key_function: Callable[[dict, dict], str] = None):
        entity_designs_data = entity_designs_data or self.get_data_dict3()
        sorted_key_function = sorted_key_function or self.__sorted_key_function

        entity_design_ids = self.get_entity_design_ids_by_name(entity_name, entity_designs_data=entity_designs_data)
        entity_designs_data_keys = entity_designs_data.keys()
        result = [entity_designs_data[entity_design_id] for entity_design_id in entity_design_ids if entity_design_id in entity_designs_data_keys]
        if sorted_key_function is not None:
            result = sorted(result, key=lambda entity_info: (
                sorted_key_function(entity_info, entity_designs_data)
            ))

        return result


    def get_entity_design_ids_by_name(self, entity_name: str, entity_designs_data: dict = None) -> list:
        entity_designs_data = entity_designs_data or self.get_data_dict3()

        results = core.get_ids_from_property_value(entity_designs_data, self.__description_property_name, entity_name, fix_data_delegate=self.__fix_data_delegate)
        return results