#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from abc import ABC, abstractstaticmethod
from collections import namedtuple
import discord
import discord.ext.commands as commands
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
    def __init__(self, display_name: Union[str, Callable[[EntityDesignInfo, Tuple[EntitiesDesignsData, ...]], str], 'EntityDesignDetailProperty'], force_display_name: bool, omit_if_none: bool = True, entity_property_name: str = None, transform_function: Union[Callable[[str], Union[str, Awaitable[str]]], Callable[[EntityDesignInfo, Tuple[EntitiesDesignsData, ...]], Union[str, Awaitable[str]]]] = None, embed_only: bool = False, text_only: bool = False, **transform_kwargs):
        if embed_only and text_only:
            raise ValueError('Only one of these parameters may be True at a time: embed_only, text_only')
        self.__embed_only: bool = embed_only or False
        self.__text_only: bool = text_only or False
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

        self.__transform_function: Callable[[EntityDesignInfo, EntitiesDesignsData, ...], Union[str, Awaitable[str]]] = None
        self.__call_transform_function_async: bool = None
        if transform_function:
            if inspect.iscoroutinefunction(transform_function):
                self.__call_transform_function_async = True
                self.__transform_function = transform_function
            elif callable(transform_function):
                self.__call_transform_function_async = False
                self.__transform_function = transform_function
            else:
                raise TypeError('The transform_function must either be of type \'Awaitable[[EntityDesignInfo, EntitiesDesignsData, ...], str]\' or \'Callable[[EntityDesignInfo, EntitiesDesignsData, ...], str]\'.')

        self.__entity_property_name: str = entity_property_name or None
        self.__force_display_name: bool = force_display_name
        self.__use_transform_function: bool = self.__transform_function is not None
        self.__use_entity_property_name: bool = self.__entity_property_name is not None
        self.__kwargs: Dict[str, object] = transform_kwargs or {}
        self.__omit_if_none: bool = omit_if_none


    @property
    def display_name(self) -> Union[str, Callable[[EntityDesignInfo, EntitiesDesignsData], str]]:
        return self.__display_name

    @property
    def embed_only(self) -> bool:
        return self.__embed_only

    @property
    def force_display_name(self) -> bool:
        return self.__force_display_name

    @property
    def omit_if_none(self) -> bool:
        return self.__omit_if_none

    @property
    def text_only(self) -> bool:
        return self.__text_only


    async def get_full_property(self, entity_design_info: EntityDesignInfo, *entities_designs_data: EntitiesDesignsData, force_display_name: bool = False, **additional_kwargs) -> CalculatedEntityDesignDetailProperty:
        kwargs = {**self.__kwargs, **additional_kwargs}
        force_display_name = self.force_display_name or force_display_name
        if force_display_name:
            display_name = await self.__get_display_name(entity_design_info, *entities_designs_data, **kwargs)
        else:
            display_name = None
        value = await self.__get_value(entity_design_info, *entities_designs_data, **kwargs)
        if (self.__omit_if_none and not value) or (not display_name and force_display_name):
            result = CalculatedEntityDesignDetailProperty(None, None)
        else:
            result = CalculatedEntityDesignDetailProperty(display_name, value)
        return result


    async def __get_display_name(self, entity_design_info: EntityDesignInfo, *entities_designs_data: EntitiesDesignsData, **kwargs) -> str:
        if self.__display_name:
            return self.__display_name
        elif self.__display_name_function:
            result = self.__display_name_function(entity_design_info, *entities_designs_data, **kwargs)
            return result
        elif self.__display_name_property:
            _, result = await self.__display_name_property.get_full_property(entity_design_info, *entities_designs_data, **kwargs)
            return result
        else:
            return ''


    async def __get_value(self, entity_design_info: EntityDesignInfo, *entities_designs_data: EntitiesDesignsData, **kwargs) -> str:
        if self.__transform_function:
            if self.__use_entity_property_name:
                entity_property = get_property_from_entity_info(entity_design_info, self.__entity_property_name)
                kwargs['entity_property'] = entity_property
            if self.__call_transform_function_async:
                result = await self.__transform_function(entity_design_info, *entities_designs_data, **kwargs)
            else:
                result = self.__transform_function(entity_design_info, *entities_designs_data, **kwargs)
        elif self.__use_entity_property_name:
            result = get_property_from_entity_info(entity_design_info, self.__entity_property_name)
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
    def __init__(self,
        entity_design_info: EntityDesignInfo,
        title: EntityDesignDetailProperty,
        description: EntityDesignDetailProperty,
        properties_long: List[EntityDesignDetailProperty],
        properties_short: List[EntityDesignDetailProperty],
        embed_settings: Dict[str, EntityDesignDetailProperty],
        *entities_designs_data: Optional[EntitiesDesignsData],
        description_embed: EntityDesignDetailProperty = None,
        prefix: str = None,
        **kwargs):
        """

        """
        self.__entities_designs_data: EntitiesDesignsData = entities_designs_data or {}
        self.__entity_design_info: EntityDesignInfo = entity_design_info or {}
        self.__title_property: EntityDesignDetailProperty = title
        self.__description_property: EntityDesignDetailProperty = description
        self.__description_embed_property: EntityDesignDetailProperty = description_embed
        properties_long = properties_long or []
        properties_short = properties_short or []
        self.__properties_long: List[EntityDesignDetailProperty] = [entity_property for entity_property in properties_long if not entity_property.embed_only]
        self.__properties_short: List[EntityDesignDetailProperty] = [entity_property for entity_property in properties_short if not entity_property.embed_only]
        properties_embed_long = [entity_property for entity_property in properties_long if not entity_property.text_only]
        properties_embed_short = [entity_property for entity_property in properties_short if not entity_property.text_only]
        self.__properties_embed_long: List[EntityDesignDetailProperty] = properties_embed_long
        self.__properties_embed_short: List[EntityDesignDetailProperty] = properties_embed_short
        self.__embed_settings: Dict[str, EntityDesignDetailProperty] = embed_settings or {}
        self.__title: str = None
        self.__description: str = None
        self.__description_embed: str = None
        self.__details_long: List[Tuple[str, str]] = None
        self.__details_short: List[Tuple[str, str]] = None
        self.__details_embed_long: List[Tuple[str, str]] = None
        self.__details_embed_short: List[Tuple[str, str]] = None
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


    async def get_details_as_embed(self, ctx: commands.Context) -> discord.Embed:
        result = await self.__create_base_embed(ctx)
        details = await self._get_details_long(as_embed=True)
        for detail in details:
            result.add_field(name=detail.display_name, value=detail.value)
        return result


    async def get_details_as_text_long(self) -> List[str]:
        result = []
        title = await self._get_title()
        result.append(f'**{title}**')
        description = await self._get_description(as_embed=False)
        if description is not None:
            result.append(f'_{description}_')
        details_long = await self._get_details_long()
        for detail in details_long:
            if detail.display_name:
                result.append(f'{self.prefix}{detail.display_name} = {detail.value}')
            else:
                result.append(f'{self.prefix}{detail.value}')
        return result


    async def get_full_details_as_text_short(self) -> List[str]:
        title = await self._get_title()
        details = await self.get_details_as_text_short()
        result = f'{self.prefix}{title} ({details})'
        return [result]


    async def get_details_as_text_short(self, force_display_names: bool = False, as_embed: bool = False) -> str:
        details = []
        details_short = await self._get_details_short(force_display_names=force_display_names, as_embed=as_embed)
        for detail in details_short:
            if detail.display_name:
                details.append(f'{detail.display_name}: {detail.value}')
            else:
                details.append(detail.value)
        result = ', '.join(details)
        return result


    async def _get_properties(self, properties: List[EntityDesignDetailProperty], force_display_names: bool = False):
        result: List[Tuple[str, str]] = []
        entity_design_detail_property: EntityDesignDetailProperty = None
        for entity_design_detail_property in properties:
            info = self.__entity_design_info
            data = self.__entities_designs_data
            kwargs = self.__kwargs
            full_property = await entity_design_detail_property.get_full_property(info, *data, force_display_name=force_display_names, **kwargs)
            if not entity_design_detail_property.omit_if_none or full_property.value:
                result.append(full_property)
        return result


    async def _get_description(self, as_embed: bool = False) -> str:
        if as_embed:
            if self.__description_embed is None and self.__description_embed_property:
                _, self.__description_embed = await self.__description_embed_property.get_full_property(self.__entity_design_info, *self.__entities_designs_data, **self.__kwargs)
            return self.__description_embed
        else:
            if self.__description is None and self.__description_property:
                _, self.__description_embed = await self.__description_property.get_full_property(self.__entity_design_info, *self.__entities_designs_data, **self.__kwargs)
            return self.__description


    async def _get_embed_settings(self) -> Dict[str, str]:
        result = {}
        for setting_name, setting_value in self.__embed_settings.items():
            value = await self._get_properties([setting_value])
            if value and value[0] and value[0].value:
                result[setting_name] = value[0].value
        return result


    async def _get_details_long(self, as_embed: bool = False) -> List[Tuple[str, str]]:
        if as_embed:
            if self.__details_embed_long is None and self.__properties_embed_long:
                self.__details_embed_long = await self._get_properties(self.__properties_embed_long, force_display_names=True)
            return self.__details_embed_long
        else:
            if self.__details_long is None and self.__properties_long:
                self.__details_long = await self._get_properties(self.__properties_long)
            return self.__details_long


    async def _get_details_short(self, force_display_names: bool = False, as_embed: bool = False) -> List[Tuple[str, str]]:
        if as_embed:
            if self.__details_embed_short is None and self.__properties_embed_short:
                self.__details_embed_short = await self._get_properties(self.__properties_embed_short, force_display_names=force_display_names)
            return self.__details_embed_short
        else:
            if self.__details_short is None and self.__properties_short:
                self.__details_short = await self._get_properties(self.__properties_short, force_display_names=force_display_names)
            return self.__details_short


    def _get_details_short_as_text(self, details_short: List[Tuple[str, str]], force_display_names: bool = False) -> str:
        details = []
        for detail in details_short:
            if detail.display_name:
                details.append(f'{detail.display_name}: {detail.value}')
            else:
                details.append(detail.value)
        result = ', '.join(details)
        return result


    async def _get_title(self) -> str:
        if self.__title is None:
            _, self.__title = await self.__title_property.get_full_property(self.__entity_design_info, *self.__entities_designs_data, **self.__kwargs)
        return self.__title


    async def __create_base_embed(self, ctx: commands.Context) -> discord.Embed:
        title = await self._get_title()
        description = await self._get_description(as_embed=True)
        colour = util.get_bot_member_colour(ctx.bot, ctx.guild)
        embed_settings = await self._get_embed_settings()
        author_url = embed_settings.get('author_url')
        icon_url = embed_settings.get('icon_url')
        image_url = embed_settings.get('image_url')
        thumbnail_url = embed_settings.get('thumbnail_url')
        result = util.create_embed(title=title, description=description, colour=colour, thumbnail_url=thumbnail_url, image_url=image_url, icon_url=icon_url, author_url=author_url)
        return result










class EntityDesignDetailsCollection():
    def __init__(self, entities_designs_details: Iterable[EntityDesignDetails], big_set_threshold: int = 0, add_empty_lines: bool = True):
        self.__entities_designs_details: List[EntityDesignDetails] = list(entities_designs_details)
        self.__set_size: int = len(self.__entities_designs_details)
        self.__big_set_threshold: int = big_set_threshold or 0
        if self.__big_set_threshold < 0:
            self.__big_set_threshold = 0
        self.__is_big_set: bool = self.__big_set_threshold and self.__set_size > self.__big_set_threshold
        self.__add_empty_lines: bool = add_empty_lines or False


    async def get_entity_details_as_embed(self, ctx: commands.Context, custom_footer_text: str = None) -> List[discord.Embed]:
        result = []
        if self.__is_big_set:
            colour = util.get_bot_member_colour(ctx.bot, ctx.guild)
            fields = []
            for entity_design_details in self.__entities_designs_details:
                field_title = await entity_design_details._get_title()
                field_value = await entity_design_details.get_details_as_text_short(force_display_names=True, as_embed=True)
                fields.append((field_title, field_value, False))
            while (len(fields) > 25):
                embed = util.create_embed(discord.Embed.Empty, colour=colour, fields=fields[:25])
                result.append(embed)
                fields = fields[25:]
            embed = util.create_embed(discord.Embed.Empty, colour=colour, fields=fields)
            result.append(embed)
        else:
            for entity_design_details in self.__entities_designs_details:
                details = await entity_design_details.get_details_as_embed(ctx)
                result.append(details)
        return result


    async def get_entity_details_as_text(self) -> List[str]:
        result = []
        for entity_design_details in self.__entities_designs_details:
            if self.__is_big_set:
                details = await entity_design_details.get_full_details_as_text_short()
                result.extend(details)
            else:
                details = await entity_design_details.get_details_as_text_long()
                result.extend(details)
                if self.__add_empty_lines:
                    result.append(settings.EMPTY_LINE)
        if result and self.__add_empty_lines and not self.__is_big_set:
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

async def get_download_sprite_link_by_property(entity_info: EntityDesignInfo, *entities_designs_data, **kwargs) -> str:
    entity_property = kwargs.get('entity_property')
    return await get_download_sprite_link(entity_property)


async def get_download_sprite_link(sprite_id: str) -> str:
    if has_value(sprite_id):
        base_url = await core.get_base_url()
        result = f'{base_url}FileService/DownloadSprite?spriteId={sprite_id}'
        return result
    else:
        return None


def get_property_from_entity_info(entity_info: EntityDesignInfo, entity_property_name: str) -> object:
    while '.' in entity_property_name:
        split_parameter = entity_property_name.split('.')
        property_name = split_parameter[0]
        entity_property_name = '.'.join(split_parameter[1:])
        if property_name not in entity_info.keys():
            continue
        entity_info = entity_info[property_name]

    if entity_property_name in entity_info.keys():
        result = entity_info[entity_property_name]
        result_lower = result.lower()
        if not result or result_lower == '0' or result_lower == 'none':
            return None
        else:
            return result


def group_entities_designs_details(entities_designs_details: List[EntityDesignDetails], property_name: str) -> Dict[object, List[EntityDesignDetails]]:
    result = {}
    for entity_design_details in entities_designs_details:
        key = entity_design_details.entity_design_info[property_name]
        result.setdefault(key, []).append(entity_design_details)
    return result


def has_value(entity_property: str) -> bool:
    return entity_property and entity_property != '0' and entity_property.lower() != 'none'










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