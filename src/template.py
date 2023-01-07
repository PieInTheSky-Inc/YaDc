from typing import Dict as _Dict
from typing import List as _List
from typing import Optional as _Optional
from typing import Tuple as _Tuple
from typing import Union as _Union

from discord import Embed as _Embed
from discord.ext.commands import Context as _Context

from . import pss_assert as _assert
from . import pss_core as _core
from . import pss_entity as _entity
from .pss_exception import Error as _Error
from .pss_exception import NotFound as _NotFound
from . import settings as _settings
from . import utils as _utils
from .typehints import EntitiesData as _EntitiesData
from .typehints import EntityInfo as _EntityInfo


# ---------- Typehint definitions ----------





# ---------- Constants ----------

ENTITY_DESIGN_BASE_PATH: str = ''
ENTITY_DESIGN_DESCRIPTION_PROPERTY_NAME: str = ''
ENTITY_DESIGN_KEY_NAME: str = ''





# ---------- Classes ----------





# ---------- Entity info ----------

def get_entity_details_by_id(entity_design_id: str, entities_data: _EntitiesData) -> _entity.EntityDetails:
    if entity_design_id:
        if entity_design_id and entity_design_id in entities_data.keys():
            return __create_entity_details_from_info(entities_data[entity_design_id], entities_data)
    return None


async def get_entity_details_by_name(ctx: _Context, entity_name: str, as_embed: bool = _settings.USE_EMBEDS) -> _Union[_List[_Embed], _List[str]]:
    _assert.valid_entity_name(entity_name, 'entity_name')

    entities_data = await entities_designs_retriever.get_data_dict3()
    entity_info = await entities_designs_retriever.get_entity_info_by_name(entity_name, entities_data)

    if entity_info is None:
        raise _NotFound(f'Could not find an entity named `{entity_name}`.')
    else:
        entities_details_collection = __create_entities_details_collection_from_infos([entity_info], entities_data)
        if as_embed:
            return (await entities_details_collection.get_entities_details_as_embed(ctx))
        else:
            return (await entities_details_collection.get_entities_details_as_text())





# ---------- Transformation functions ----------

async def __get(entity_info: _EntityInfo, entities_data: _EntitiesData, **kwargs) -> _Optional[str]:
    pass





# ---------- Helper functions ----------





# ---------- Create entity.entity.EntityDetails ----------

def __create_entity_details_from_info(entity_info: _EntityInfo, entities_data: _EntitiesData) -> _entity.entity.EntityDetails:
    return _entity.entity.EntityDetails(entity_info, __properties['title'], __properties['description'], __properties['properties'], __properties['embed_settings'], entities_data)


def __create_entities_details_collection_from_infos(entities_designs_infos: _List[_EntityInfo], entities_data: _EntitiesData) -> _entity.EntityDetailsCollection:
    entities_details = [__create_entity_details_from_info(entity_info, entities_data) for entity_info in entities_designs_infos]
    result = _entity.EntityDetailsCollection(entities_details, big_set_threshold=3)





# ---------- DB ----------





# ---------- Mocks ----------





# ---------- Initilization ----------

entities_designs_retriever = _entity.EntityRetriever(
    ENTITY_DESIGN_BASE_PATH,
    ENTITY_DESIGN_KEY_NAME,
    ENTITY_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='EntityDesigns'
)


__properties: _entity.EntityDetailsCreationPropertiesCollection = {
    'title': _entity.EntityDetailPropertyCollection(
        _entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name='', transform_function=None),
        property_medium=_entity.NO_PROPERTY,
        property_short=_entity.NO_PROPERTY,
        property_mini=_entity.NO_PROPERTY
    ),
    'description': _entity.EntityDetailPropertyCollection(
        _entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='', transform_function=None),
        property_medium=_entity.NO_PROPERTY,
        property_short=_entity.NO_PROPERTY,
        property_mini=_entity.NO_PROPERTY
    ),
    'properties': _entity.EntityDetailPropertyListCollection(
        [
            _entity.EntityDetailProperty('Name', True, entity_property_name='', transform_function=None),
        ],
        properties_medium=[],
        properties_short=[],
        properties_mini=[]
        ),
    'embed_settings': {
        'author_url': _entity.NO_PROPERTY,
        'color': _entity.NO_PROPERTY,
        'description': _entity.NO_PROPERTY,
        'footer': _entity.NO_PROPERTY,
        'icon_url': _entity.NO_PROPERTY,
        'image_url': _entity.NO_PROPERTY,
        'thumbnail_url': _entity.NO_PROPERTY,
        'timestamp': _entity.NO_PROPERTY,
        'title': _entity.NO_PROPERTY,
    }
}





async def init() -> None:
    pass