#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from abc import ABC, abstractstaticmethod
import discord
from typing import Callable, Dict, List, Optional, Tuple, Union

from cache import PssCache
import pss_core as core
import settings










class EntityDesignDetailProperty(object):
    def __init__(self, display_name: Union[str, Callable[[list], str]], transform_function: Callable[[list], str], entity_info_property_names: List[str], force_display_name: bool):
        if isinstance(display_name, str):
            self.__display_name: str = display_name
            self.__display_name_function: Callable[[list], str] = None
        elif isinstance(display_name, Callable[[list], str]):
            self.__display_name: str = None
            self.__display_name_function: Callable[[list], str] = display_name
        else:
            raise TypeError()










class EntityDesignDetails(object):
    def __init__(self, entity_design_info: Dict[str, object], name_property_name: str, description_property_name: str, properties_long_text: List[Dict[str, object]], properties_short_text: List[Dict[str, object]], properties_embed: List[Dict[str, object]], entities_designs_data: Optional[Dict[str, Dict[str, object]]] = None):
        """
        _coroutine_
        """
        self.__entity_design_info: Dict[str, object] = entity_design_info
        self.__name_property_name: str = name_property_name
        self.__description_property_name: str = description_property_name
        self.__properties_long_text: List[Dict[str, object]] = properties_long_text
        self.__properties_short_text: List[Dict[str, object]] = properties_short_text
        self.__properties_embed: List[Dict[str, object]] = properties_embed


    #def __init__(self, name: str = None, description: str = None, details_long: List[Tuple[str, str]] = None, details_short: List[Tuple[str, str, bool]] = None, hyperlink: str = None):
    #    self.__name: str = name or None
    #    self.__description: str = description or None
    #    self.__details_long: List[Tuple[str, str]] = details_long or []
    #    self.__details_short: List[Tuple[str, str, bool]] = details_short or []
    #    self.__hyperlink: str = hyperlink or None


    @property
    def description(self) -> str:
        return self.__entity_design_info[self.__description_property_name]

    @property
    def name(self) -> str:
        return self.__entity_design_info[self.__name_property_name]


    def get_details_as_embed(self) -> discord.Embed:
        result = discord.Embed()
        result.title = self.name
        result.description = self.description


    def get_details_as_text_long(self) -> List[str]:
        pass
        #return EntityDesignDetails._get_details_as_text_long(self.name, self.description, self.details_long, self.link)


    def get_details_as_text_short(self) -> List[str]:
        pass
        #return EntityDesignDetails._get_details_as_text_short(self.name, self.details_short)


    @staticmethod
    def _get_properties():
        pass


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
