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
from . import pss_item as _item
from . import pss_login as _login
from . import pss_sprites as _sprites
from . import settings as _settings
from . import utils as _utils
from .typehints import EntitiesData as _EntitiesData
from .typehints import EntityInfo as _EntityInfo


# ---------- Typehint definitions ----------





# ---------- Constants ----------

STAR_SYSTEM_MARKER_BASE_PATH: str = 'GalaxyService/ListStarSystemMarkers?accessToken='
STAR_SYSTEM_MARKER_DESCRIPTION_PROPERTY_NAME: str = 'Title'
STAR_SYSTEM_MARKER_KEY_NAME: str = 'StarSystemMarkerId'





# ---------- Classes ----------





# ---------- System Star Marker info ----------

async def get_trader_details(ctx: _Context, as_embed: bool = _settings.USE_EMBEDS) -> _Union[_List[_Embed], _List[str]]:
    items_data = await _item.items_designs_retriever.get_data_dict3()
    stars_systems_markers_data = await __get_stars_systems_markers_data()
    trader_details = get_trader_info(stars_systems_markers_data)

    if not trader_details:
        raise _NotFound('Could not find information on the trader ship. Please try again later.')

    contents = await __get_trader_offerings(trader_details.entity_info, items_data)

    if as_embed:
        pass
    else:
        pass


def get_star_system_marker_details_by_id(star_system_marker_id: str, stars_systems_markers_data: _EntitiesData) -> _entity.EntityDetails:
    if star_system_marker_id:
        if star_system_marker_id and star_system_marker_id in stars_systems_markers_data.keys():
            return __create_star_system_marker_details_from_info(stars_systems_markers_data[star_system_marker_id], stars_systems_markers_data)
    return None


def get_trader_info(stars_systems_markers_data: _EntitiesData) -> _entity.EntityDetails:
    for star_system_marker_id, star_system_marker_info in stars_systems_markers_data.items():
        if star_system_marker_info['MarkerType'] == 'MerchantShip':
            return get_star_system_marker_details_by_id(star_system_marker_id, stars_systems_markers_data)
    return None





# ---------- Transformation functions ----------

async def __get(entity_info: _EntityInfo, entities_data: _EntitiesData, **kwargs) -> _Optional[str]:
    pass


async def __get_sprite_download_path(star_system_marker_info: _EntityInfo, stars_systems_markers_data: _EntitiesData, **kwargs) -> _Optional[str]:
    result = _sprites.get_sprite_download_url(star_system_marker_info['SpriteId'])
    return result





# ---------- Helper functions ----------

async def __get_list_system_star_markers_base_path() -> str:
    access_token = await _login.DEVICES.get_access_token()
    result = f'{STAR_SYSTEM_MARKER_BASE_PATH}{access_token}'
    return result


async def __get_trader_offerings(trader_info: _EntityInfo, items_data: _EntitiesData) -> _List[_Tuple[_entity.EntityDetails, int, str]]:
    """
    Returns a list of tuples: EntityDetails, currency amount, currency type
    """
    rewards = _utils.parse.entity_multi_string(trader_info['RewardString'], '|')
    costs = _utils.parse.entity_multi_string(trader_info['CostString'], '|')
    result = []
    for i, (_, item_design_id, _, _) in enumerate(rewards):
        item_design_details = _item.get_item_details_by_id(item_design_id, items_data, None)
        currency_type = costs[i][0]
        currency_amount = costs[i][2]
        if currency_type == 'item':
            currency_item_design_id = costs[i][1]
            currency_item_design_details = _item.get_item_details_by_id(currency_item_design_id, items_data, None)
            result.append(
                (
                    item_design_details,
                    currency_amount,
                    currency_item_design_details.entity_info[_item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME],
                )
            )
        else:

            result.append(
                (
                    item_design_details,
                    currency_amount,
                    currency_type,
                )
            )
    return result



async def __get_stars_systems_markers_data() -> _EntitiesData:
    path = await __get_list_system_star_markers_base_path()
    raw_data = await _core.get_data_from_path(path)
    data = _utils.convert.xmltree_to_dict3(raw_data)
    return data



# ---------- Create entity.entity.EntityDetails ----------

def __create_star_system_marker_details_from_info(entity_info: _EntityInfo, entities_data: _EntitiesData) -> _entity.entity.EntityDetails:
    return _entity.entity.EntityDetails(entity_info, __properties['title'], __properties['description'], __properties['properties'], __properties['embed_settings'], entities_data)


def __create_stars_systems_markers_details_collection_from_infos(entities_designs_infos: _List[_EntityInfo], entities_data: _EntitiesData) -> _entity.EntityDetailsCollection:
    entities_details = [__create_star_system_marker_details_from_info(entity_info, entities_data) for entity_info in entities_designs_infos]
    result = _entity.EntityDetailsCollection(entities_details, big_set_threshold=3)





# ---------- DB ----------





# ---------- Mocks ----------





# ---------- Initilization ----------


__properties: _entity.EntityDetailsCreationPropertiesCollection = {
    'title': _entity.EntityDetailPropertyCollection(
        _entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=STAR_SYSTEM_MARKER_DESCRIPTION_PROPERTY_NAME, transform_function=None),
        property_short=_entity.NO_PROPERTY,
        property_mini=_entity.NO_PROPERTY
    ),
    'description': _entity.EntityDetailPropertyCollection(
        _entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='Description', transform_function=None),
        property_short=_entity.NO_PROPERTY,
        property_mini=_entity.NO_PROPERTY
    ),
    'properties': _entity.EntityDetailPropertyListCollection(
        [
            _entity.EntityDetailProperty('Name', True, entity_property_name='', transform_function=None),
        ],
        properties_short=[],
        properties_mini=[]
        ),
    'embed_settings': {
        'author_url': _entity.NO_PROPERTY,
        'color': _entity.NO_PROPERTY,
        'description': _entity.EntityDetailProperty('description', False, entity_property_name='Description'),
        'footer': _entity.NO_PROPERTY,
        'icon_url': _entity.NO_PROPERTY,
        'image_url': _entity.NO_PROPERTY,
        'thumbnail_url': _entity.EntityDetailProperty('icon_url', False, transform_function=__get_sprite_download_path),
        'timestamp': _entity.NO_PROPERTY,
        'title': _entity.EntityDetailProperty('title', False, entity_property_name=STAR_SYSTEM_MARKER_DESCRIPTION_PROPERTY_NAME),
    }
}





async def init() -> None:
    pass