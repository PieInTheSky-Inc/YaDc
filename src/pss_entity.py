#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from abc import ABC, abstractstaticmethod
from collections import namedtuple
import discord
import inspect
import json
from typing import Awaitable, Callable, Dict, Iterable, List, NamedTuple, Optional, Tuple, Union
from xml.etree import ElementTree


from cache import PssCache
import pss_core as core
import settings
import utility as util










# ---------- Typing definitions ----------

EntityDesignInfo = Dict[str, 'EntityDesignInfo']
EntitiesDesignsData = Dict[str, EntityDesignInfo]










# ---------- Classes ----------

CalculatedEntityDesignDetailProperty = namedtuple('CalculatedEntityDesignDetailProperty', ['display_name', 'value'])


class EntityDesignDetailProperty(object):
    def __init__(self, display_name: Union[str, Callable[[EntityDesignInfo, EntitiesDesignsData, ...], str], EntityDesignDetailProperty], force_display_name: bool, omit_if_none: bool = True, entity_property_name: str = None, transform_function: Union[Awaitable[[str], str ], Awaitable[[EntityDesignInfo, EntitiesDesignsData, ...], str ], Callable[[str], str], Callable[[EntityDesignInfo, EntitiesDesignsData, ...], str]] = None, **transform_kwargs):
        self.__display_name: str = None
        self.__display_name_function: Callable[[EntityDesignInfo, EntitiesDesignsData, ...], str] = None
        self.__display_name_property: EntityDesignDetailProperty = None
        if isinstance(display_name, str):
            self.__display_name = display_name
        elif isinstance(display_name, EntityDesignDetailProperty):
            self.__display_name_property = display_name
        elif callable(display_name):
            self.__display_name_function = display_name
        else:
            raise TypeError('The display_name must either be of type \'str\', \'Awaitable[[EntityDesignInfo, EntitiesDesignsData, ...], str]\' or \'Callable[[EntityDesignInfo, EntitiesDesignsData, ...], str]\'.')

        if not entity_property_name and not transform_function:
            raise Exception('Invalid paramaeters: either the \'entity_property_name\' or the \'transform_function\' need to be provided!')

        self.__transform_function: Callable[[EntityDesignInfo, EntitiesDesignsData, ...], str] = None
        self.__transform_function_async: Awaitable[[EntityDesignInfo, EntitiesDesignsData, ...], str] = None
        if transform_function:
            if inspect.isawaitable(transform_function):
                self.__transform_function_async = transform_function
            elif callable(transform_function):
                self.__transform_function = transform_function
            else:
                raise TypeError('The transform_function must either be of type \'Awaitable[[EntityDesignInfo, EntitiesDesignsData, ...], str]\' or \'Callable[[EntityDesignInfo, EntitiesDesignsData, ...], str]\'.')

        self.__entity_property_name: str = entity_property_name or None
        self.__force_display_name: bool = force_display_name
        self.__use_transform_function: bool = self.__transform_function is not None or self.__transform_function_async is not None
        self.__use_entity_property_name: bool = self.__entity_property_name is not None
        self.__kwargs: Dict[str, object] = transform_kwargs or {}
        self.__omit_if_none: bool = omit_if_none


    @property
    def display_name(self) -> Union[str, Callable[[EntityDesignInfo, EntitiesDesignsData], str]]:
        return self.__display_name

    @property
    def force_display_name(self) -> bool:
        return self.__force_display_name

    @property
    def omit_if_none(self) -> bool:
        return self.__omit_if_none


    async def get_full_property(self, entity_design_info: EntityDesignInfo, *entities_designs_data: EntitiesDesignsData, **additional_kwargs) -> CalculatedEntityDesignDetailProperty:
        kwargs = {**self.__kwargs, **additional_kwargs}
        if self.__force_display_name:
            display_name = self.__get_display_name(entity_design_info, *entities_designs_data, **kwargs)
        else:
            display_name = None
        value = await self.__get_value(entity_design_info, *entities_designs_data, **kwargs)
        if self.__omit_if_none and not value:
            return CalculatedEntityDesignDetailProperty(None, None)
        return CalculatedEntityDesignDetailProperty(display_name, value)


    def __get_display_name(self, entity_design_info: EntityDesignInfo, *entities_designs_data: EntitiesDesignsData, **kwargs) -> str:
        if self.__display_name:
            return self.__display_name
        elif self.__display_name_function:
            result = self.__display_name_function(entity_design_info, *entities_designs_data, **kwargs)
            return result
        elif self.__display_name_property:
            _, result = self.__display_name_property.get_full_property(entity_design_info, entities_designs_data, kwargs)
        else:
            return ''


    async def __get_value(self, entity_design_info: EntityDesignInfo, *entities_designs_data: EntitiesDesignsData, **kwargs) -> str:
        if self.__use_transform_function:
            if self.__use_entity_property_name:
                entity_property = entity_design_info[self.__entity_property_name]
                kwargs['entity_property'] = entity_property
            if self.__transform_function:
                result = self.__transform_function(entity_design_info, *entities_designs_data, **kwargs)
            elif self.__transform_function_async:
                result = await self.__transform_function_async(entity_design_info, *entities_designs_data, **kwargs)
        elif self.__use_entity_property_name:
            result = entity_design_info[self.__entity_property_name]
        else:
            result = None
        return result










class EntityDesignDetailEmbedProperty(EntityDesignDetailProperty):
    def __init__(self, display_name: Union[str, Callable[[EntityDesignInfo, EntitiesDesignsData], str]], entity_property_name: str = None, transform_function: Callable[[EntityDesignInfo, EntitiesDesignsData], str] = None):
        super().__init__(display_name, True, entity_property_name=entity_property_name, transform_function=transform_function)


    @classmethod
    def from_entity_design_detail_property(cls, entity_design_detail_property: EntityDesignDetailProperty):
        return cls(
            entity_design_detail_property.display_name,

        )










class EntityDesignDetails(object):
    def __init__(self, entity_design_info: EntityDesignInfo, title: EntityDesignDetailProperty, description: EntityDesignDetailProperty, properties_long: List[EntityDesignDetailProperty], properties_short: List[EntityDesignDetailProperty], properties_embed: List[EntityDesignDetailProperty], *entities_designs_data: Optional[EntitiesDesignsData], prefix: str = None, **kwargs):
        """

        """
        self.__entities_designs_data: EntitiesDesignsData = entities_designs_data or {}
        self.__entity_design_info: EntityDesignInfo = entity_design_info or {}
        self.__title_property: EntityDesignDetailProperty = title
        self.__description_property: EntityDesignDetailProperty = description
        self.__properties_long: List[EntityDesignDetailProperty] = properties_long or []
        self.__properties_short: List[EntityDesignDetailProperty] = properties_short or []
        self.__properties_embed: List[EntityDesignDetailProperty] = properties_embed or []
        self.__title: str = None
        self.__description: str = None
        self.__details_embed: List[Tuple[str, str]] = None
        self.__details_long: List[Tuple[str, str]] = None
        self.__details_short: List[Tuple[str, str]] = None
        self.__prefix: str = prefix or ''
        self.__kwargs: Dict[str, object] = kwargs


    @property
    def entities_designs_data(self) -> EntitiesDesignsData:
        if self.__entities_designs_data is None:
            return None
        return dict(self.__entities_designs_data)

    @property
    def entity_design_info(self) -> EntityDesignInfo:
        if self.__entity_design_info is None:
            return None
        return dict(self.__entity_design_info)

    @property
    def prefix(self) -> str:
        return self.__prefix


    async def get_details_as_embed(self) -> discord.Embed:
        result = discord.Embed(title=(await self.__get_title()), description=(await self.__get_description()))
        for detail in (await self.__get_details_embed()):
            result.add_field(name=detail.name, value=detail.value)
        return result


    async def get_details_as_text_long(self) -> List[str]:
        result = []
        title = await self.__get_title()
        result.append(f'**{title}**')
        description = await self.__get_description()
        if description is not None:
            result.append(f'_{description}_')
        for detail in (await self.__get_details_long):
            if detail.display_name:
                result.append(f'{self.prefix}{detail.display_name} = {detail.value}')
            else:
                result.append(f'{self.prefix}{detail.value}')
        return result


    async def get_details_as_text_short(self) -> List[str]:
        details = []
        for detail in (await self.__get_details_short()):
            if detail.display_name:
                details.append(f'{detail.display_name}: {detail.value}')
            else:
                details.append(detail.value)
        title = await self.__get_title()
        result = f'{self.prefix}{title} ({", ".join(details)})'
        return [result]


    async def _get_properties(self, properties: List[EntityDesignDetailProperty]):
        result: List[Tuple[str, str]] = []
        entity_design_detail_property: EntityDesignDetailProperty = None
        for entity_design_detail_property in properties:
            info = self.__entity_design_info
            data = self.__entities_designs_data
            kwargs = self.__kwargs
            full_property = await entity_design_detail_property.get_full_property(info, *data, **kwargs)
            if not entity_design_detail_property.omit_if_none or full_property.value:
                result.append(full_property)
        return result


    async def __get_description(self) -> str:
        if self.__description is None and self.__description_property is not None:
            _, description = await self.__description_property.get_full_property(self.__entity_design_info, *self.__entities_designs_data, **self.__kwargs)
            self.__description = description or ''
        return self.__description


    async def __get_details_embed(self) -> List[Tuple[str, str]]:
        if self.__details_embed is None:
            self.__details_embed = await self._get_properties(self.__properties_embed)
        return self.__details_embed


    async def __get_details_long(self) -> List[Tuple[str, str]]:
        if self.__details_long is None:
            self.__details_long = await self._get_properties(self.__properties_long)
        return self.__details_long


    async def __get_details_short(self) -> List[Tuple[str, str]]:
        if self.__details_short is None:
            self.__details_short = await self._get_properties(self.__properties_short)
        return self.__details_short


    async def __get_title(self) -> str:
        if self.__title is None:
            _, title = await self.__title_property.get_full_property(self.__entity_design_info, *self.__entities_designs_data, **self.__kwargs)
            self.__title = title or ''
        return self.__title










class EntityDesignDetailsCollection():
    def __init__(self, entities_designs_details: Iterable[EntityDesignDetails], big_set_threshold: int = 0, add_empty_lines: bool = True):
        self.__entities_designs_details: List[EntityDesignDetails] = list(entities_designs_details)
        self.__set_size: int = len(self.__entities_designs_details)
        self.__big_set_threshold: int = big_set_threshold or 0
        if self.__big_set_threshold < 0:
            self.__big_set_threshold = 0
        self.__is_big_set: bool = self.__big_set_threshold and self.__set_size > self.__big_set_threshold
        self.__add_empty_lines: bool = add_empty_lines or False


    def get_entity_details_as_embed(self) -> List[discord.Embed]:
        raise Exception('get_entity_details_as_embed is not yet implemented.')


    async def get_entity_details_as_text(self) -> List[str]:
        result = []
        for entity_design_details in self.__entities_designs_details:
            if self.__is_big_set:
                result.extend(await entity_design_details.get_details_as_text_short())
            else:
                result.extend(await entity_design_details.get_details_as_text_long())
                if self.__add_empty_lines:
                    result.append(settings.EMPTY_LINE)
        if result and self.__add_empty_lines:
            result = result[:-1]
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


    @property
    def base_path(self) -> str:
        return self.__base_path

    @property
    def description_property_name(self) -> str:
        return self.__description_property_name

    @property
    def key_name(self) -> str:
        return self.__key_name


    async def get_data_dict3(self) -> Dict[str, Dict[str, object]]:
        return await self.__cache.get_data_dict3()


    async def get_entity_design_info_by_name(self, entity_name: str, entities_designs_data: EntitiesDesignsData = None) -> Dict[str, object]:
        entities_designs_data = entities_designs_data or await self.get_data_dict3()
        entity_design_id = await self.get_entity_design_id_by_name(entity_name, entities_designs_data=entities_designs_data)
        return entities_designs_data.get(entity_design_id, None)


    async def get_entities_designs_infos_by_name(self, entity_name: str, entities_designs_data: EntitiesDesignsData = None, sorted_key_function: Callable[[dict, dict], str] = None) -> List[Dict[str, object]]:
        entities_designs_data = entities_designs_data or await self.get_data_dict3()
        sorted_key_function = sorted_key_function or self.__sorted_key_function

        entity_design_ids = await self.get_entities_designs_ids_by_name(entity_name, entities_designs_data=entities_designs_data)
        entities_designs_data_keys = entities_designs_data.keys()
        result = [entities_designs_data[entity_design_id] for entity_design_id in entity_design_ids if entity_design_id in entities_designs_data_keys]
        if sorted_key_function is not None:
            result = sorted(result, key=lambda entity_info: (
                sorted_key_function(entity_info, entities_designs_data)
            ))

        return result


    async def get_entity_design_id_by_name(self, entity_name: str, entities_designs_data: EntitiesDesignsData = None) -> str:
        entities_designs_data = entities_designs_data or await self.get_data_dict3()
        results = await self.get_entities_designs_ids_by_name(entity_name, entities_designs_data)
        if len(results) > 0:
            return results[0]
        else:
            return None


    async def get_entities_designs_ids_by_name(self, entity_name: str, entities_designs_data: EntitiesDesignsData = None) -> List[str]:
        entities_designs_data = entities_designs_data or await self.get_data_dict3()
        results = core.get_ids_from_property_value(entities_designs_data, self.__description_property_name, entity_name, fix_data_delegate=self.__fix_data_delegate)
        return results


    async def get_raw_data(self) -> str:
        return await self.__cache.get_raw_data()


    async def get_raw_entity_design_info_by_id_as_xml(self, entity_id: str) -> str:
        result = None
        raw_data = await self.__cache.get_raw_data()
        for element in ElementTree.fromstring(raw_data).iter():
            element_id = element.attrib.get(self.__key_name)
            if element_id:
                result = ElementTree.tostring(element).decode("utf-8")
                break
        return result


    async def get_raw_entity_design_info_by_id_as_json(self, entity_id: str, fix_xml_attributes: bool = False) -> str:
        result = None
        raw_xml = await self.get_raw_entity_design_info_by_id_as_xml(entity_id)
        if raw_xml is not None:
            result = core.xmltree_to_raw_dict(raw_xml, fix_attributes=True)
        if result is not None:
            result = json.dumps(result)
        return result


    async def update_cache(self) -> None:
        await self.__cache.update_data()










# ---------- Helper ----------

def group_entities_designs_details(entities_designs_details: List[EntityDesignDetails], property_name: str) -> Dict[object, List[EntityDesignDetails]]:
    result = {}
    for entity_design_details in entities_designs_details:
        key = entity_design_details.entity_design_info[property_name]
        result.setdefault(key, []).append(entity_design_details)
    return result










# ---------- Legacy ----------

class LegacyEntityDesignDetails(object):
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
        return LegacyEntityDesignDetails._get_details_as_embed(self.name, self.description, self.details_long, self.link)


    def get_details_as_text_long(self) -> List[str]:
        return LegacyEntityDesignDetails._get_details_as_text_long(self.name, self.description, self.details_long, self.link)


    def get_details_as_text_short(self) -> List[str]:
        return LegacyEntityDesignDetails._get_details_as_text_short(self.name, self.details_short)


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