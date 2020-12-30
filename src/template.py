from typing import Dict, List, Optional, Tuple, Union

from discord import Embed
from discord.ext.commands import Context

import pss_assert
import pss_entity as entity
from pss_exception import Error, NotFound
import settings
from typehints import EntitiesData, EntityInfo


# ---------- Typehint definitions ----------





# ---------- Constants ----------

ENTITY_DESIGN_BASE_PATH: str = ''
ENTITY_DESIGN_DESCRIPTION_PROPERTY_NAME: str = ''
ENTITY_DESIGN_KEY_NAME: str = ''





# ---------- Classes ----------





# ---------- Entity info ----------

def get_entity_details_by_id(entity_design_id: str, entities_data: EntitiesData) -> entity.EntityDetails:
    if entity_design_id:
        if entity_design_id and entity_design_id in entities_data.keys():
            return __create_entity_details_from_info(entities_data[entity_design_id], entities_data)
    return None


async def get_entity_details_by_name(ctx: Context, entity_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(entity_name, 'entity_name')

    entities_data = await entities_designs_retriever.get_data_dict3()
    entity_info = await entities_designs_retriever.get_entity_info_by_name(entity_name, entities_data)

    if entity_info is None:
        raise NotFound(f'Could not find an entity named `{entity_name}`.')
    else:
        entities_details_collection = __create_entities_details_collection_from_infos([entity_info], entities_data)
        if as_embed:
            return (await entities_details_collection.get_entities_details_as_embed(ctx))
        else:
            return (await entities_details_collection.get_entities_details_as_text())





# ---------- Transformation functions ----------

async def __get(entity_info: EntityInfo, entities_data: EntitiesData, **kwargs) -> Optional[str]:
    pass





# ---------- Helper functions ----------





# ---------- Create entity.entity.EntityDetails ----------

def __create_entity_details_from_info(entity_info: EntityInfo, entities_data: EntitiesData) -> entity.entity.EntityDetails:
    return entity.entity.EntityDetails(entity_info, __properties['title'], __properties['description'], __properties['properties'], __properties['embed_settings'], entities_data)


def __create_entities_details_collection_from_infos(entities_designs_infos: List[EntityInfo], entities_data: EntitiesData) -> entity.EntityDetailsCollection:
    entities_details = [__create_entity_details_from_info(entity_info, entities_data) for entity_info in entities_designs_infos]
    result = entity.EntityDetailsCollection(entities_details, big_set_threshold=3)





# ---------- DB ----------





# ---------- Mocks ----------





# ---------- Initilization ----------

entities_designs_retriever = entity.EntityRetriever(
    ENTITY_DESIGN_BASE_PATH,
    ENTITY_DESIGN_KEY_NAME,
    ENTITY_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='EntityDesigns'
)


__properties: entity.EntityDetailsCreationPropertiesCollection = {
    'title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name='', transform_function=None),
        property_long=entity.NO_PROPERTY,
        property_short=entity.NO_PROPERTY,
        property_mini=entity.NO_PROPERTY
    ),
    'description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='', transform_function=None),
        property_long=entity.NO_PROPERTY,
        property_short=entity.NO_PROPERTY,
        property_mini=entity.NO_PROPERTY
    ),
    'properties': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Name', True, entity_property_name='', transform_function=None),
        ],
        properties_long=[],
        properties_short=[],
        properties_mini=[]
        ),
    'embed_settings': {
        'author_url': entity.NO_PROPERTY,
        'color': entity.NO_PROPERTY,
        'description': entity.NO_PROPERTY,
        'footer': entity.NO_PROPERTY,
        'icon_url': entity.NO_PROPERTY,
        'image_url': entity.NO_PROPERTY,
        'thumbnail_url': entity.NO_PROPERTY,
        'timestamp': entity.NO_PROPERTY,
        'title': entity.NO_PROPERTY,
    }
}





async def init() -> None:
    pass