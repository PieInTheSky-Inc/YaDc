from enum import IntEnum
import inspect
import json
from typing import Any, Awaitable, Callable, Dict, Iterable, Iterator, List, Optional, Tuple, Union
from xml.etree import ElementTree

from discord import Embed
from discord.ext.commands import Context

from .cache import PssCache
from . import pss_core as core
from . import pss_entity as entity
from .pss_exception import Error
from . import settings
from .typehints import EntitiesData, EntityInfo
from . import utils


# ---------- Constants ----------

DEFAULT_ENTITY_DETAIL_PROPERTY_PREFIX: str = ''
DEFAULT_VALUE_IF_NONE: str = settings.DEFAULT_HYPHEN
DEFAULT_DETAIL_PROPERTY_LONG_SEPARATOR: str = ' = '
DEFAULT_DETAIL_PROPERTY_SHORT_SEPARATOR: str = ': '
DEFAULT_DETAILS_PROPERTIES_SEPARATOR: str = ' | '
DEFAULT_TITLE_DETAILS_SEPARATOR: str = f' {settings.DEFAULT_HYPHEN} '

ERROR_ENTITY_DETAILS_TYPE_EMBED_NOT_ALLOWED: str = f'The detail type \'EMBED\' is not valid for this method!'
ERROR_ENTITY_DETAILS_TYPE_NONE_NOT_ALLOWED: str = f'You have to provide a detail type!'

NO_PROPERTY: 'EntityDetailProperty'





# ---------- Typehint definitions ----------

EntityDetailsCreationPropertiesCollection = Dict[str, Union['EntityDetailPropertyCollection', 'EntityDetailPropertyListCollection', Dict[str, 'EntityDetailProperty']]]





# ---------- Classes ----------

class EntityDetailsType(IntEnum):
    LONG = 1
    SHORT = 2
    MINI = 3
    EMBED = 4





class CalculatedEntityDetailProperty(object):
    def __init__(self, display_name: str, value: str, force_display_name: bool, omit_if_none: bool, display_inline_for_embeds: bool = utils.discord.DEFAULT_EMBED_INLINE) -> None:
        self.__display_name: str = display_name
        self.__display_inline_for_embeds: bool = utils.discord.DEFAULT_EMBED_INLINE if display_inline_for_embeds is None else display_inline_for_embeds
        self.__value: str = value
        self.__force_display_name: bool = force_display_name
        self.__omit_if_none: bool = omit_if_none
        self.__tuple: Tuple[str, str, bool, bool] = [self.__display_name, self.__value, self.__force_display_name, self.__omit_if_none, self.__display_inline_for_embeds]


    @property
    def display_name(self) -> str:
        return self.__display_name

    @property
    def display_inline(self) -> bool:
        return self.__display_inline_for_embeds

    @property
    def force_display_name(self) -> bool:
        return self.__force_display_name

    @property
    def omit_if_none(self) -> bool:
        return self.__omit_if_none

    @property
    def value(self) -> str:
        return self.__value


    def get_text(self, separator: str, prefix: str = DEFAULT_ENTITY_DETAIL_PROPERTY_PREFIX, suppress_display_name: bool = False, force_value: bool = False) -> str:
        result = None
        if not self.omit_if_none or self.value or force_value:
            value = self.get_value_or_default()
            result = prefix
            if not suppress_display_name and self.display_name and self.force_display_name:
                result += f'{self.display_name}{separator}{value}'
            else:
                result += value
        return result


    def get_value_or_default(self, default: str = DEFAULT_VALUE_IF_NONE) -> str:
        result = self.value or default
        return result


    def __iter__(self) -> Iterator[Union[str, bool]]:
        return iter(self.__tuple)





class EntityDetailProperty(object):
    def __init__(self, display_name: Union[str, Callable[[EntityInfo, EntitiesData], str], 'EntityDetailProperty'], force_display_name: bool, omit_if_none: bool = True, entity_property_name: str = None, transform_function: Union[Callable[[str], Union[str, Awaitable[str]]], Callable[[EntityInfo, Tuple[EntitiesData, ...]], Union[str, Awaitable[str]]]] = None, embed_only: bool = False, text_only: bool = False, **transform_kwargs) -> None:
        if embed_only and text_only:
            raise ValueError('Only one of these parameters may be True at a time: embed_only, text_only')
        self.__embed_only: bool = embed_only or False
        self.__text_only: bool = text_only or False
        self.__display_name: str = None
        self.__display_name_function: Callable[[EntityInfo, EntitiesData], str] = None
        self.__display_name_property: EntityDetailProperty = None
        if display_name:
            if isinstance(display_name, str):
                self.__display_name = display_name
            elif isinstance(display_name, EntityDetailProperty):
                self.__display_name_property = display_name
            elif callable(display_name):
                self.__display_name_function = display_name
            else:
                raise TypeError('The display_name must either be of type \'str\', \'Awaitable[[EntityInfo, EntitiesData, ...], str]\' or \'Callable[[EntityInfo, EntitiesData, ...], str]\'.')

        self.__transform_function: Callable[[EntityInfo, EntitiesData], Union[str, Awaitable[str]]] = None
        self.__call_transform_function_async: bool = None
        if transform_function:
            if inspect.iscoroutinefunction(transform_function):
                self.__call_transform_function_async = True
                self.__transform_function = transform_function
            elif callable(transform_function):
                self.__call_transform_function_async = False
                self.__transform_function = transform_function
            else:
                raise TypeError('The transform_function must either be of type \'Awaitable[[EntityInfo, EntitiesData, ...], str]\' or \'Callable[[EntityInfo, EntitiesData, ...], str]\'.')

        self.__entity_property_name: str = entity_property_name or None
        self.__force_display_name: bool = force_display_name
        self.__use_transform_function: bool = self.__transform_function is not None
        self.__use_entity_property_name: bool = self.__entity_property_name is not None
        self.__kwargs: Dict[str, object] = transform_kwargs or {}
        self.__omit_if_none: bool = omit_if_none


    @property
    def display_name(self) -> Union[str, Callable[[EntityInfo, EntitiesData], str]]:
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


    async def get_full_property(self, entity_info: EntityInfo, *entities_data: EntitiesData, **additional_kwargs) -> CalculatedEntityDetailProperty:
        kwargs = {**self.__kwargs, **additional_kwargs}
        display_name = await self.__get_display_name(entity_info, *entities_data, **kwargs)
        value = await self.__get_value(entity_info, *entities_data, **kwargs)
        display_inline_for_embeds = kwargs.get('display_inline_for_embeds')

        return CalculatedEntityDetailProperty(display_name, value, self.__force_display_name, self.__omit_if_none, display_inline_for_embeds=display_inline_for_embeds)


    async def __get_display_name(self, entity_info: EntityInfo, *entities_data: EntitiesData, **kwargs) -> str:
        if self.__display_name:
            return self.__display_name
        elif self.__display_name_function:
            result = self.__display_name_function(entity_info, *entities_data, **kwargs)
            return result
        elif self.__display_name_property:
            full_property = await self.__display_name_property.get_full_property(entity_info, *entities_data, **kwargs)
            return full_property.value
        else:
            return ''


    async def __get_value(self, entity_info: EntityInfo, *entities_data: EntitiesData, **kwargs) -> Optional[str]:
        if self.__transform_function:
            if self.__use_entity_property_name:
                entity_property = get_property_from_entity_info(entity_info, self.__entity_property_name)
                kwargs['entity_property'] = entity_property
            if self.__call_transform_function_async:
                result = await self.__transform_function(entity_info, *entities_data, **kwargs)
            else:
                result = self.__transform_function(entity_info, *entities_data, **kwargs)
        elif self.__use_entity_property_name:
            result = get_property_from_entity_info(entity_info, self.__entity_property_name)
        else:
            result = None
        return result





class EntityDetailEmbedOnlyProperty(EntityDetailProperty):
    def __init__(self, display_name: Union[str, Callable[[EntityInfo, Tuple[EntitiesData, ...]], str], 'EntityDetailProperty'], force_display_name: bool, omit_if_none: bool = True, entity_property_name: str = None, transform_function: Union[Callable[[str], Union[str, Awaitable[str]]], Callable[[EntityInfo, Tuple[EntitiesData, ...]], Union[str, Awaitable[str]]]] = None, display_inline: bool = utils.discord.DEFAULT_EMBED_INLINE, **transform_kwargs) -> None:
        self.__display_inline: bool = display_inline
        super().__init__(display_name, force_display_name, omit_if_none=omit_if_none, entity_property_name=entity_property_name, transform_function=transform_function, embed_only=True, **transform_kwargs)


    @property
    def display_inline(self) -> bool:
        return self.__display_inline


    async def get_full_property(self, entity_info: EntityInfo, *entities_data: EntitiesData, **additional_kwargs) -> CalculatedEntityDetailProperty:
        result = await super().get_full_property(entity_info, *entities_data, **additional_kwargs)
        return CalculatedEntityDetailProperty(result.display_name, result.value, result.force_display_name, result.omit_if_none, display_inline_for_embeds=self.display_inline)





class EntityDetailTextOnlyProperty(EntityDetailProperty):
    def __init__(self, display_name: Union[str, Callable[[EntityInfo, Tuple[EntitiesData, ...]], str], 'EntityDetailProperty'], force_display_name: bool, omit_if_none: bool = True, entity_property_name: str = None, transform_function: Union[Callable[[str], Union[str, Awaitable[str]]], Callable[[EntityInfo, Tuple[EntitiesData, ...]], Union[str, Awaitable[str]]]] = None, **transform_kwargs) -> None:
        super().__init__(display_name, force_display_name, omit_if_none=omit_if_none, entity_property_name=entity_property_name, transform_function=transform_function, text_only=True, **transform_kwargs)





class EntityDetailPropertyCollection(object):
    def __init__(self, property_long: EntityDetailProperty,
                       property_short: EntityDetailProperty = None,
                       property_mini: EntityDetailProperty = None,
                       property_embed: EntityDetailProperty = None):
        self.__property_long: EntityDetailProperty = property_long
        self.__property_short: EntityDetailProperty = property_short or None
        self.__property_mini: EntityDetailProperty = property_mini or None
        self.__property_embed: EntityDetailProperty = property_embed or None


    @property
    def property_long(self) -> EntityDetailProperty:
        return self.__property_long

    @property
    def property_short(self) -> EntityDetailProperty:
        if self.__property_short:
            return self.__property_short
        else:
            return self.property_long

    @property
    def property_mini(self) -> EntityDetailProperty:
        if self.__property_mini:
            return self.__property_mini
        else:
            return self.property_short

    @property
    def property_embed(self) -> EntityDetailProperty:
        if self.__property_embed:
            return self.__property_embed
        else:
            return self.property_long


    def get_property(self, entity_details_type: EntityDetailsType) -> List[EntityDetailProperty]:
        if entity_details_type == EntityDetailsType.LONG:
            return self.property_long
        elif entity_details_type == EntityDetailsType.SHORT:
            return self.property_short
        elif entity_details_type == EntityDetailsType.MINI:
            return self.property_mini
        elif entity_details_type == EntityDetailsType.EMBED:
            return self.property_embed
        else:
            raise ValueError(ERROR_ENTITY_DETAILS_TYPE_NONE_NOT_ALLOWED)





class EntityDetailPropertyListCollection(object):
    def __init__(self, properties_long: List[EntityDetailProperty],
                       properties_short: List[EntityDetailProperty] = None,
                       properties_mini: List[EntityDetailProperty] = None):
        self.__properties_long: List[EntityDetailProperty] = properties_long
        self.__properties_short: List[EntityDetailProperty] = properties_short
        self.__properties_mini: List[EntityDetailProperty] = properties_mini


    @property
    def properties_long(self) -> List[EntityDetailProperty]:
        return self.__properties_long

    @property
    def properties_short(self) -> List[EntityDetailProperty]:
        if self.__properties_short is not None:
            return self.__properties_short
        else:
            return self.properties_long

    @property
    def properties_mini(self) -> List[EntityDetailProperty]:
        if self.__properties_mini is not None:
            return self.__properties_mini
        else:
            return self.properties_short


    def get_properties(self, entity_details_type: EntityDetailsType) -> List[EntityDetailProperty]:
        if entity_details_type == EntityDetailsType.LONG:
            return self.properties_long
        elif entity_details_type == EntityDetailsType.SHORT:
            return self.properties_short
        elif entity_details_type == EntityDetailsType.MINI:
            return self.properties_mini
        elif entity_details_type == EntityDetailsType.EMBED:
            raise ValueError(ERROR_ENTITY_DETAILS_TYPE_EMBED_NOT_ALLOWED)
        else:
            raise ValueError(ERROR_ENTITY_DETAILS_TYPE_NONE_NOT_ALLOWED)





class EntityDetails(object):
    def __init__(self, entity_info: EntityInfo,
                       title: EntityDetailPropertyCollection,
                       description: EntityDetailPropertyCollection,
                       properties: EntityDetailPropertyCollection,
                       embed_settings: Dict[str, EntityDetailProperty],
                       *entities_data: Optional[EntitiesData],
                       prefix: str = None,
                       **kwargs):
        """

        """
        self.__entities_data: EntitiesData = entities_data or {}
        self.__entity_info: EntityInfo = entity_info or {}
        self.__title_property_collection: EntityDetailPropertyCollection = title or NO_PROPERTY
        self.__description_property_collection: EntityDetailPropertyCollection = description or NO_PROPERTY
        self.__properties: Dict[bool, Dict[EntityDetailsType, List[EntityDetailProperty]]] = {}
        if properties:
            self.__properties = {
                False: {
                    EntityDetailsType.LONG: [entity_property for entity_property in properties.properties_long if not entity_property.embed_only],
                    EntityDetailsType.SHORT: [entity_property for entity_property in properties.properties_short if not entity_property.embed_only],
                    EntityDetailsType.MINI: [entity_property for entity_property in properties.properties_mini if not entity_property.embed_only]
                },
                True: {
                    EntityDetailsType.LONG: [entity_property for entity_property in properties.properties_long if not entity_property.text_only],
                    EntityDetailsType.SHORT: [entity_property for entity_property in properties.properties_short if not entity_property.text_only],
                    EntityDetailsType.MINI: [entity_property for entity_property in properties.properties_mini if not entity_property.text_only]
                }
            }
        else:
            self.__properties = {
                False: {
                    EntityDetailsType.LONG: [],
                    EntityDetailsType.SHORT: [],
                    EntityDetailsType.MINI: []
                },
                True: {
                    EntityDetailsType.LONG: [],
                    EntityDetailsType.SHORT: [],
                    EntityDetailsType.MINI: []
                }
            }
        self.__embed_settings: Dict[str, EntityDetailProperty] = embed_settings or {}
        self.__calculated_embed_settings: Dict[str, str] = None
        self.__titles: Dict[EntityDetailsType, str] = {}
        self.__descriptions: Dict[EntityDetailsType, str] = {}
        self.__details: Dict[bool, Dict[EntityDetailsType, List[CalculatedEntityDetailProperty]]] = {
            False: {
                EntityDetailsType.LONG: None,
                EntityDetailsType.SHORT: None,
                EntityDetailsType.MINI: None
            },
            True: {
                EntityDetailsType.LONG: None,
                EntityDetailsType.SHORT: None,
                EntityDetailsType.MINI: None
            }
        }
        self.__prefix: str = prefix or ''
        self.__kwargs: Dict[str, object] = kwargs


    @property
    def entities_data(self) -> EntitiesData:
        if self.__entities_data is None:
            return None
        return dict(self.__entities_data)

    @property
    def entity_info(self) -> EntityInfo:
        if self.__entity_info is None:
            return None
        return dict(self.__entity_info)

    @property
    def prefix(self) -> str:
        return self.__prefix


    async def get_details(self, as_embed: bool, details_type: EntityDetailsType) -> List[CalculatedEntityDetailProperty]:
        result = await self._get_details_properties(as_embed, details_type)
        return result


    async def get_details_as_embed(self, ctx: Context, display_inline: bool = None) -> Embed:
        result = await self.__create_base_embed(ctx)
        details_long = await self._get_details_properties(True, EntityDetailsType.LONG)
        detail: CalculatedEntityDetailProperty
        for detail in details_long:
            if detail.value or not detail.omit_if_none:
                inline = display_inline if display_inline is not None else (detail.display_inline if detail.display_inline is not None else True)
                field_name = detail.display_name if '**' in detail.display_name else f'**{detail.display_name}**'
                result.add_field(name=field_name, value=detail.value, inline=inline)
        return result


    async def get_details_as_text(self, details_type: EntityDetailsType, for_embed: bool = False) -> List[str]:
        if details_type == EntityDetailsType.EMBED:
            raise ValueError(ERROR_ENTITY_DETAILS_TYPE_EMBED_NOT_ALLOWED)
        if details_type == EntityDetailsType.LONG:
            return await self.__get_details_long_as_text()
        elif details_type == EntityDetailsType.SHORT:
            return await self.__get_details_short_as_text(for_embed)
        elif details_type == EntityDetailsType.MINI:
            return await self.__get_details_mini_as_text(for_embed)


    async def get_display_names(self, as_embed: bool, details_type: EntityDetailsType) -> List[str]:
        if details_type == EntityDetailsType.EMBED:
            raise ValueError(ERROR_ENTITY_DETAILS_TYPE_EMBED_NOT_ALLOWED)
        details = await self._get_details_properties(as_embed, details_type)
        result = [detail.display_name for detail in details]
        return result


    async def get_embed_settings(self) -> Dict[str, str]:
        if self.__calculated_embed_settings is None and self.__embed_settings:
            result = {}
            for setting_name, setting_value in self.__embed_settings.items():
                value = await self.__get_calculated_property(setting_value)
                if value and value.value:
                    result[setting_name] = value.value
            self.__calculated_embed_settings = result
        return self.__calculated_embed_settings


    async def get_full_details(self, as_embed: bool, details_type: EntityDetailsType) -> Tuple[str, str, List[CalculatedEntityDetailProperty]]:
        details_type = details_type or (EntityDetailsType.EMBED if as_embed else None)
        if not details_type:
            raise Error('You have to specify a details_type or set as_embed to True!')
        title, description = await self.__get_title_and_description(details_type)
        details = await self._get_details_properties(as_embed, details_type)
        return title, description, details


    async def _get_description(self, details_type: EntityDetailsType = EntityDetailsType.LONG) -> str:
        return await self.__get_property_from_collection(self.__description_property_collection, self.__descriptions, details_type)


    async def _get_details_properties(self, as_embed: bool, details_type: EntityDetailsType) -> List[CalculatedEntityDetailProperty]:
        if details_type == EntityDetailsType.EMBED:
            as_embed = True
            details_type = EntityDetailsType.LONG
        if self.__details[as_embed][details_type] is None and self.__properties[as_embed][details_type] is not None:
            self.__details[as_embed][details_type] = [await self.__get_calculated_property(entity_detail_property) for entity_detail_property in self.__properties[as_embed][details_type]]
        return self.__details[as_embed][details_type]


    async def _get_title(self, details_type: EntityDetailsType = EntityDetailsType.LONG) -> str:
        return await self.__get_property_from_collection(self.__title_property_collection, self.__titles, details_type)


    async def __create_base_embed(self, ctx: Context) -> Embed:
        title = await self._get_title(details_type=EntityDetailsType.EMBED)
        description = await self._get_description(details_type=EntityDetailsType.EMBED)

        embed_settings = await self.get_embed_settings()
        colour = embed_settings.get('color', embed_settings.get('colour', utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)))
        author_url = embed_settings.get('author_url')
        icon_url = embed_settings.get('icon_url')
        image_url = embed_settings.get('image_url')
        thumbnail_url = embed_settings.get('thumbnail_url')
        timestamp = embed_settings.get('timestamp')
        footer = embed_settings.get('footer')
        result = utils.discord.create_embed(title=title, description=description, colour=colour, footer=footer, thumbnail_url=thumbnail_url, image_url=image_url, icon_url=icon_url, author_url=author_url, timestamp=timestamp)
        return result


    async def __get_calculated_property(self, entity_detail_property: EntityDetailProperty) -> CalculatedEntityDetailProperty:
        info = self.__entity_info
        data = self.__entities_data
        kwargs = self.__kwargs
        result = await entity_detail_property.get_full_property(info, *data, **kwargs)
        return result


    async def __get_details_long_as_text(self) -> List[str]:
        title, description, details_long = await self.get_full_details(False, EntityDetailsType.LONG)
        result = []
        if title:
            result.append(f'**{title}**')
        if description:
            result.append(f'_{description}_')
        for detail in [d for d in details_long if d.value]:
            result.append(detail.get_text(separator=DEFAULT_DETAIL_PROPERTY_LONG_SEPARATOR, prefix=self.prefix))
        return result


    async def __get_details_mini_as_text(self, for_embed: bool) -> List[str]:
        title, description, details_mini = await self.get_full_details(for_embed, EntityDetailsType.MINI)
        title_text = title if title else ''
        details = []
        if description:
            details.append(description)
        details += [detail.get_text(separator=DEFAULT_DETAIL_PROPERTY_SHORT_SEPARATOR) for detail in details_mini if detail.value]
        details_text = DEFAULT_DETAILS_PROPERTIES_SEPARATOR.join([detail for detail in details if detail])
        if details_text and title_text:
            details_text = f' ({details_text})'
        result = f'{self.prefix}{title_text}{details_text}'
        return [result]


    async def __get_details_short_as_text(self, for_embed: bool) -> List[str]:
        title, description, details_short = await self.get_full_details(for_embed, EntityDetailsType.SHORT)
        title_text = title if title else ''
        if description:
            if title_text:
                description = f' ({description})'
            else:
                description =f'({description})'
        else:
            description = ''
        details = [detail.get_text(separator=DEFAULT_DETAIL_PROPERTY_SHORT_SEPARATOR) for detail in details_short if detail.value]
        details_text = DEFAULT_DETAILS_PROPERTIES_SEPARATOR.join([detail for detail in details if detail])
        if details_text and title_text:
            details_text = f' ({details_text})'
        result = f'{self.prefix}{title_text}{description}{details_text}'
        return [result]


    async def __get_property_from_collection(self, property_collection: EntityDetailPropertyCollection, detail_lookup: Dict[EntityDetailsType, str], details_type: EntityDetailsType) -> str:
        if property_collection == NO_PROPERTY:
            return None

        if details_type == EntityDetailsType.LONG:
            prop = property_collection.property_long
        elif details_type == EntityDetailsType.SHORT:
            prop = property_collection.property_short
        elif details_type == EntityDetailsType.MINI:
            prop = property_collection.property_mini
        elif details_type == EntityDetailsType.EMBED:
            prop = property_collection.property_embed
        else:
            raise ValueError(f'The parameter \'details_type\' received an invalid value: {details_type}')

        if details_type not in detail_lookup.keys():
            full_property = await prop.get_full_property(self.__entity_info, *self.__entities_data, force_if_none=True, **self.__kwargs)
            detail_lookup[details_type] = full_property.value

        return detail_lookup[details_type]


    async def __get_title_and_description(self, details_type: EntityDetailsType) -> Tuple[str, str]:
        title = await self._get_title(details_type=details_type)
        description = await self._get_description(details_type=details_type)
        return title, description





class EscapedEntityDetails(EntityDetails):
    async def get_details_as_text(self, details_type: EntityDetailsType, for_embed: bool = False) -> List[str]:
        if details_type == EntityDetailsType.EMBED:
            raise ValueError(ERROR_ENTITY_DETAILS_TYPE_EMBED_NOT_ALLOWED)
        return await self.__get_details_long_as_text()


    async def __get_details_long_as_text(self) -> List[str]:
        title, description, details_long = await self.get_full_details(False, EntityDetailsType.LONG)

        result = [f'**```{title}```**']
        if description:
            result[-1] += '```'
            result.append(f'{description} ```')
        if details_long:
            result[-1] += '```'
            for detail in [d for d in details_long if d.value]:
                result.append(detail.get_text(separator=DEFAULT_DETAIL_PROPERTY_LONG_SEPARATOR, prefix=self.prefix))
            result[-1] += '```'
        return result





class EntityDetailsCollection():
    def __init__(self, entities_details: Iterable[entity.EntityDetails], big_set_threshold: int = 0, add_empty_lines: bool = True) -> None:
        """
        big_set_threshold: if 0 or less, there's no threshold
        """
        self.__entities_details: List[entity.EntityDetails] = list(entities_details)
        self.__set_size: int = len(self.__entities_details)
        self.__big_set_threshold: int = big_set_threshold or 0
        if self.__big_set_threshold < 0:
            self.__big_set_threshold = 0
        self.__add_empty_lines: bool = add_empty_lines or False


    async def get_entities_details_as_embed(self, ctx: Context, custom_detail_property_separator: str = None, custom_title: str = None, custom_footer_text: str = None, custom_thumbnail_url: str = None, display_inline: bool = True, big_set_threshold: int = None) -> List[Embed]:
        """
        custom_title: only relevant for big sets
        """
        result: List[Embed] = []
        display_names = []
        if self._get_is_big_set(big_set_threshold):
            detail_property_separator = custom_detail_property_separator if custom_detail_property_separator is not None else DEFAULT_DETAILS_PROPERTIES_SEPARATOR
            title = custom_title or Embed.Empty
            colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            display_names = await self.__entities_details[0].get_display_names(True, EntityDetailsType.SHORT)
            fields = []
            for entity_details in self.__entities_details:
                entity_title, _, entity_details_properties = await entity_details.get_full_details(True, EntityDetailsType.SHORT)
                field_name = entity_title if '**' in entity_title else f'**{entity_title}**'
                details = detail_property_separator.join([detail.get_text(DEFAULT_DETAIL_PROPERTY_SHORT_SEPARATOR, suppress_display_name=True, force_value=True) for detail in entity_details_properties])
                fields.append((field_name, details, display_inline))

            footer = ''
            if display_names:
                footer = 'Properties displayed:   '
                footer += DEFAULT_DETAILS_PROPERTIES_SEPARATOR.join(display_names)
            if custom_footer_text:
                if footer:
                    footer += '\n\n'
                footer += custom_footer_text

            full_embed_length = 0
            embed = None
            while len(fields) > 0:
                full_embed_length = len(title) + len(footer)
                for i, field in enumerate(fields, 1):
                    full_embed_length += len(field[0]) + len(field[1])
                    if i == 25 or i == len(fields) or full_embed_length + len(fields[i][0]) + len(fields[i][1]) > 6000:
                        break
                if i == len(fields):
                    embed = utils.discord.create_embed(title, colour=colour, fields=fields[:i], footer=footer, thumbnail_url=custom_thumbnail_url)
                else:
                    embed = utils.discord.create_embed(title, colour=colour, fields=fields[:i], footer=footer)
                fields = fields[i:]
                result.append(embed)
        else:
            for entity_details in self.__entities_details:
                embed = await entity_details.get_details_as_embed(ctx)
                if custom_footer_text:
                    embed.set_footer(text=custom_footer_text)
                result.append(embed)
        return result


    async def get_entities_details_as_text(self, custom_title: str = None, custom_footer_text: str = None, big_set_details_type: EntityDetailsType = EntityDetailsType.SHORT, big_set_threshold: int = None) -> List[str]:
        result = []
        is_big_set = self._get_is_big_set(big_set_threshold)
        if custom_title:
            result.append(custom_title)
        for entity_details in self.__entities_details:
            if is_big_set:
                details = await entity_details.get_details_as_text(big_set_details_type)
                result.extend(details)
            else:
                details = await entity_details.get_details_as_text(EntityDetailsType.LONG)
                result.extend(details)
                if self.__add_empty_lines:
                    result.append(utils.discord.ZERO_WIDTH_SPACE)
        if result and self.__add_empty_lines and not is_big_set:
            result = result[:-1]
        if custom_footer_text:
            result.append(utils.discord.ZERO_WIDTH_SPACE)
            result.append(custom_footer_text)
        return result


    def _get_is_big_set(self, big_set_threshold: int = None) -> bool:
        if big_set_threshold is None:
            big_set_threshold = self.__big_set_threshold
        result = big_set_threshold and self.__set_size >= big_set_threshold
        return result





class EntityRetriever:
    def __init__(self, entity_base_path: str, entity_key_name: str, entity_description_property_name: str, cache_name: str = None, sorted_key_function: Callable[[dict, dict], str] = None, fix_data_delegate: Callable[[str], str] = None, cache_update_interval: int = 10) -> None:
        self.__cache_name: str = cache_name or ''
        self.__base_path: str = entity_base_path
        self.__key_name: str = entity_key_name or None
        self.__description_property_name: str = entity_description_property_name
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


    async def get_entity_info_by_name(self, entity_name: str, entities_data: EntitiesData = None) -> Dict[str, object]:
        entities_data = entities_data or await self.get_data_dict3()
        entity_id = await self.get_entity_id_by_name(entity_name, entities_data=entities_data)
        return entities_data.get(entity_id, None)


    async def get_entities_infos_by_name(self, entity_name: str, entities_data: EntitiesData = None, sorted_key_function: Callable[[dict, dict], str] = None) -> List[Dict[str, object]]:
        entities_data = entities_data or await self.get_data_dict3()
        sorted_key_function = sorted_key_function or self.__sorted_key_function

        entity_ids = await self.get_entities_ids_by_name(entity_name, entities_data=entities_data)
        entities_data_keys = entities_data.keys()
        result = [entities_data[entity_id] for entity_id in entity_ids if entity_id in entities_data_keys]
        if sorted_key_function is not None:
            result = sorted(result, key=lambda entity_info: (
                sorted_key_function(entity_info, entities_data)
            ))

        return result


    async def get_entity_id_by_name(self, entity_name: str, entities_data: EntitiesData = None) -> str:
        entities_data = entities_data or await self.get_data_dict3()
        results = await self.get_entities_ids_by_name(entity_name, entities_data)
        if len(results) > 0:
            return results[0]
        else:
            return None


    async def get_entities_ids_by_name(self, entity_name: str, entities_data: EntitiesData = None) -> List[str]:
        entities_data = entities_data or await self.get_data_dict3()
        results = core.get_ids_from_property_value(entities_data, self.__description_property_name, entity_name, fix_data_delegate=self.__fix_data_delegate)
        return results


    async def get_raw_data(self) -> str:
        return await self.__cache.get_raw_data()


    async def get_raw_entity_info_by_id_as_xml(self, entity_id: str) -> str:
        result = None
        raw_data = await self.__cache.get_raw_data()
        for element in ElementTree.fromstring(raw_data).iter():
            element_id = element.attrib.get(self.__key_name)
            if element_id == entity_id:
                result = ElementTree.tostring(element).decode("utf-8")
                break
        return result


    async def get_raw_entity_info_by_id_as_json(self, entity_id: str, fix_xml_attributes: bool = False) -> str:
        result = None
        raw_xml = await self.get_raw_entity_info_by_id_as_xml(entity_id)
        if raw_xml is not None:
            result = utils.convert.raw_xml_to_dict(raw_xml, fix_attributes=fix_xml_attributes, preserve_lists=True)
        if result is not None:
            result = json.dumps(result)
        return result


    async def update_cache(self) -> None:
        await self.__cache.update_data()





# ---------- Helper ----------

def entity_property_has_value(entity_property: str) -> bool:
    return entity_property and entity_property != '0' and entity_property.lower() != 'none' and entity_property.strip()


def group_entities_details(entities_details: List[entity.EntityDetails], property_name: str) -> Dict[Any, List[entity.EntityDetails]]:
    result = {}
    for entity_details in entities_details:
        key = entity_details.entity_info[property_name]
        result.setdefault(key, []).append(entity_details)
    return result


def get_property_from_entity_info(entity_info: EntityInfo, entity_property_name: str) -> Any:
    while '.' in entity_property_name:
        split_parameter = entity_property_name.split('.')
        property_name = split_parameter[0]
        entity_property_name = '.'.join(split_parameter[1:])
        if property_name not in entity_info.keys():
            continue
        entity_info = entity_info[property_name]

    if entity_property_name in entity_info.keys():
        result = entity_info[entity_property_name]
        if isinstance(result, str):
            result_lower = result.lower()
            if not result or result_lower == '0' or result_lower == 'none':
                return None
            else:
                return result
        else:
            return result or None


def sort_entities_by(entity_infos: List[EntityInfo], order_info: List[Tuple[str, Callable[[Any], Any], bool]]) -> List[EntityInfo]:
    """order_info is a list of tuples (property_name,transform_function,reverse)"""
    result = entity_infos
    if order_info:
        for i in range(len(order_info), 0, -1):
            property_name = order_info[i - 1][0]
            transform_function = order_info[i - 1][1]
            reverse = utils.convert.to_boolean(order_info[i - 1][2])
            if transform_function:
                result = sorted(result, key=lambda entity_info: transform_function(entity_info[property_name]), reverse=reverse)
            else:
                result = sorted(result, key=lambda entity_info: entity_info[property_name], reverse=reverse)
        return result
    else:
        return sorted(result)





# ---------- Legacy ----------

class LegacyEntityDetails(object):
    def __init__(self, name: str = None, description: str = None, details_long: List[Tuple[str, str]] = None, details_short: List[Tuple[str, str, bool]] = None, hyperlink: str = None) -> None:
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


    def get_details_as_embed(self) -> Embed:
        return LegacyEntityDetails._get_details_as_embed(self.name, self.description, self.details_long, self.link)


    def get_details_as_text_long(self) -> List[str]:
        return LegacyEntityDetails._get_details_as_text_long(self.name, self.description, self.details_long, self.link)


    def get_details_as_text_short(self) -> List[str]:
        return LegacyEntityDetails._get_details_as_text_short(self.name, self.details_short)


    @staticmethod
    def _get_details_as_embed(title: str, description: str, details: List[Tuple[str, str]], link: str) -> Embed:
        result = Embed()
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





# ---------- Initialization ----------

NO_PROPERTY = EntityDetailProperty(None, False)