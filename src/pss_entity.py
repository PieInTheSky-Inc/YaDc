#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from abc import ABC, abstractstaticmethod
import discord
from typing import Callable, Dict, List, Tuple

from cache import PssCache
import pss_core as core
import settings










class EntityDesignDetails(object):
    def __init__(self, name: str = None, description: str = None, details_long: List[Tuple[str, str]] = None, details_short: List[Tuple[str, str, bool]] = None, hyperlink: str = None):
        self.__name: str = name or None
        self.__description: str = description or None
        self.__details_long: List[Tuple[str, str]] = details_long or []
        self.__details_short: List[Tuple[str, str, bool]] = details_short or []
        self.__hyperlink: str = hyperlink or None


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
    def link(self) -> str:
        return self.__hyperlink

    @property
    def name(self) -> str:
        return self.__name


    def get_details_as_embed(self) -> discord.Embed:
        return EntityDesignDetails._get_details_as_embed(self.name, self.description, self.details_long, self.link)


    def get_details_as_text_long(self) -> List[str]:
        return EntityDesignDetails._get_details_as_text_long(self.name, self.description, self.details_long, self.link)


    def get_details_as_text_short(self) -> List[str]:
        return EntityDesignDetails._get_details_as_text_short(self.name, self.details_short)


    @staticmethod
    def _get_details_as_embed(title: str, description: str, details: List[Tuple[str, str]], link: str) -> discord.Embed:
        result = discord.Embed()
        if title:
            result.title = title
        if description:
            result.description = description
        if details:
            for (detail_name, detail_value) in details:
                result.add_field(name=detail_name, value=detail_value)
        if link:
            result.set_footer(text=link)
        return result


    @staticmethod
    def _get_details_as_text_long(title: str, description: str, details: List[Tuple[str,str]], link: str) -> List[str]:
        result = []
        if title:
            result.append(f'**{title}**')
        if description:
            result.append(f'_{description}_')
        if details:
            for (detail_name, detail_value) in details:
                if detail_value:
                    result.append(f'{detail_name} = {detail_value}')
        if link:
            result.append(f'<{link}>')
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










class EntityDesignDetailsCollection():
    def __init__(self, entity_ids: List[str], big_set_threshold: int = 3):
        entities_designs_data = None
        self.__entities_designs_details: List[EntityDesignDetails] = [entity_design_data for entity_design_data in entity_ids if entity_design_data in entities_designs_data.keys()]
        self.__big_set_threshold: int = big_set_threshold
        pass


    def get_entity_details_as_embed(self) -> List[discord.Embed]:
        return []


    def get_entity_details_as_text(self) -> List[str]:
        result = []
        set_size = len(self.__entities_designs_details)
        entity_design_details: EntityDesignDetails
        for i, entity_design_details in enumerate(self.__entities_designs_details, start=1):
            if set_size > self.__big_set_threshold:
                result.extend(entity_design_details.get_details_as_text_short())
            else:
                result.extend(entity_design_details.get_details_as_text_long())
                if i < set_size:
                    result.append(settings.EMPTY_LINE)
        return result










class EntityDesignsRetriever:
    def __init__(self, entity_design_base_path: str, entity_design_key_name: str, entity_design_description_property_name: str, cache_name: str = None, sorted_key_function: Callable[[dict, dict], str] = None, fix_data_delegate: Callable[[str], str] = None, cache_update_interval: int = 10):
        self.__cache_name: str = cache_name or ''
        self.__base_path: str = entity_design_base_path
        self.__key_name: str = entity_design_key_name or None
        self.__description_property_name: str = entity_design_description_property_name
        self.__sorted_key_function: Callable[[dict, dict], str] = sorted_key_function
        self.__fix_data_delegate: Callable[[str], str] = fix_data_delegate

        self.__cache = PssCache(
            self.__base_path,
            self.__cache_name,
            key_name=self.__key_name,
            update_interval=cache_update_interval
        )


    def get_data_dict3(self) -> Dict[str, Dict[str, object]]:
        return self.__cache.get_data_dict3()


    def get_entity_design_details_by_id(self, entity_id: str, entity_designs_data: Dict[str, Dict[str, object]] = None) -> EntityDesignDetails:
        pass


    def get_entity_design_info_by_id(self, entity_design_id: str, entity_designs_data: Dict[str, Dict[str, object]] = None) -> Dict[str, object]:
        entity_designs_data = entity_designs_data or self.get_data_dict3()
        if entity_design_id in entity_designs_data.keys():
            return entity_designs_data[entity_design_id]
        else:
            return None


    def get_entity_design_info_by_name(self, entity_name: str, entity_designs_data: Dict[str, Dict[str, object]] = None) -> Dict[str, object]:
        entity_designs_data = entity_designs_data or self.get_data_dict3()
        entity_design_id = self.get_entity_design_id_by_name(entity_name, entity_designs_data=entity_designs_data)

        if entity_design_id and entity_design_id in entity_designs_data.keys():
            return entity_designs_data[entity_design_id]
        else:
            return None


    def get_entities_designs_infos_by_name(self, entity_name: str, entity_designs_data: Dict[str, Dict[str, object]] = None, sorted_key_function: Callable[[dict, dict], str] = None) -> List[Dict[str, object]]:
        entity_designs_data = entity_designs_data or self.get_data_dict3()
        sorted_key_function = sorted_key_function or self.__sorted_key_function

        entity_design_ids = self.get_entities_designs_ids_by_name(entity_name, entity_designs_data=entity_designs_data)
        entity_designs_data_keys = entity_designs_data.keys()
        result = [entity_designs_data[entity_design_id] for entity_design_id in entity_design_ids if entity_design_id in entity_designs_data_keys]
        if sorted_key_function is not None:
            result = sorted(result, key=lambda entity_info: (
                sorted_key_function(entity_info, entity_designs_data)
            ))

        return result


    def get_entity_design_id_by_name(self, entity_name: str, entity_designs_data: Dict[str, Dict[str, object]] = None) -> str:
        results = self.get_entities_designs_ids_by_name(entity_name, entity_designs_data)
        if len(results) > 0:
            return results[0]
        else:
            return None


    def get_entities_designs_ids_by_name(self, entity_name: str, entity_designs_data: Dict[str, Dict[str, object]] = None) -> List[str]:
        entity_designs_data = entity_designs_data or self.get_data_dict3()
        results = core.get_ids_from_property_value(entity_designs_data, self.__description_property_name, entity_name, fix_data_delegate=self.__fix_data_delegate)
        return results


    def update_cache(self) -> None:
        self.__cache.update_data()
