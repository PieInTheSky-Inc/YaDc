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
from . import pss_lookups as _lookups
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

async def get_autotrader_details() -> _Tuple[_List[_Embed], _List[str]]:
    items_data = await _item.items_designs_retriever.get_data_dict3()
    stars_systems_markers_data = await __get_stars_systems_markers_data()
    trader_details = get_trader_info(stars_systems_markers_data)

    if not trader_details:
        raise _NotFound('Could not find information on the trader ship. Please try again later.')

    offerings = await __get_trader_offerings(trader_details.entity_info, items_data)

    trader_info = trader_details.entity_info
    trader_info['offerings'] = offerings
    trader_details.update_entity_info(trader_info)

    message = await trader_details.get_details_as_text(_entity.EntityDetailsType.LONG)

    trader_info['as_embed'] = True
    trader_details.update_entity_info(trader_info)
    embed = await trader_details.get_details_as_embed(None)

    return embed, message


async def get_trader_details(ctx: _Context, as_embed: bool = _settings.USE_EMBEDS) -> _Union[_List[_Embed], _List[str]]:
    items_data = await _item.items_designs_retriever.get_data_dict3()
    stars_systems_markers_data = await __get_stars_systems_markers_data()
    trader_details = get_trader_info(stars_systems_markers_data)

    if not trader_details:
        raise _NotFound('Could not find information on the trader ship. Please try again later.')

    offerings = await __get_trader_offerings(trader_details.entity_info, items_data)
    trader_info = trader_details.entity_info
    trader_info['offerings'] = offerings
    trader_info['as_embed'] = as_embed
    trader_details.update_entity_info(trader_info)

    if as_embed:
        result = [(await trader_details.get_details_as_embed(ctx))]
    else:
        result = await trader_details.get_details_as_text(_entity.EntityDetailsType.LONG)
    return result


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

async def __get_expiration_dates(star_system_marker_info: _EntityInfo, stars_systems_markers_data: _EntitiesData, **kwargs) -> _Optional[str]:
    expiration_date_1 = _utils.parse.pss_datetime(star_system_marker_info.get('StarSystemArrivalDate'))
    expiration_date_2 = _utils.parse.pss_datetime(star_system_marker_info.get('ExpiryDate'))
    result = [
        f'Offers 1 & 2 expire at: {_utils.datetime.get_discord_timestamp(expiration_date_1)} ({_utils.datetime.get_discord_timedelta(expiration_date_1)})',
        f'Offers 3 - 6 expire at: {_utils.datetime.get_discord_timestamp(expiration_date_2)} ({_utils.datetime.get_discord_timedelta(expiration_date_2)})',
    ]
    return '\n'.join(result)


async def __get_offer_details(star_system_marker_info: _EntityInfo, stars_systems_markers_data: _EntitiesData, **kwargs) -> _Optional[str]:
    offerings = star_system_marker_info.get('offerings')
    index = kwargs.get('index', -1)
    if offerings and index >= 0:
        as_embed = star_system_marker_info.get('as_embed')
        offer = offerings[index]

        item_details: _entity.EntityDetails = offer[0]
        currency_amount = offer[1]
        currency_type = offer[2]

        result = [
            '\n'.join(await item_details.get_details_as_text(_entity.EntityDetailsType.SHORT, for_embed=as_embed)),
            f'Cost: {currency_amount}x {currency_type}'
        ]
        return '\n'.join(result)
    return None





# ---------- Helper functions ----------

async def __get_list_system_star_markers_base_path() -> str:
    access_token = await _login.DEVICES.get_access_token()
    result = f'{STAR_SYSTEM_MARKER_BASE_PATH}{access_token}'
    return result


async def __get_trader_offerings(trader_info: _EntityInfo, items_data: _EntitiesData) -> _List[_Tuple[_entity.EntityDetails, int, str]]:
    """
    Returns a list of tuples: ItemDetails, currency amount, currency type
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
            currency_txt = _lookups.TRADER_CURRENCY_EMOJI_LOOKUP.get(int(currency_item_design_id))
            if not currency_txt:
                currency_item_design_details = _item.get_item_details_by_id(currency_item_design_id, items_data, None)
                currency_txt = currency_item_design_details.entity_info[_item.ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            result.append(
                (
                    item_design_details,
                    currency_amount,
                    currency_txt,
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
    if data:
        try:
            int(data.keys())
        except:
            data = {marker['StarSystemMarkerId']: marker for marker in data.values()}
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
    ),
    'description': _entity.EntityDetailPropertyCollection(
        _entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='Description', transform_function=None),
    ),
    'properties': _entity.EntityDetailPropertyListCollection(
        [
            _entity.EntityDetailProperty('Offer 1', True, transform_function=__get_offer_details, index=0, display_inline_for_embeds=False),
            _entity.EntityDetailProperty('Offer 2', True, transform_function=__get_offer_details, index=1, display_inline_for_embeds=False),
            _entity.EntityDetailProperty('Offer 3', True, transform_function=__get_offer_details, index=2, display_inline_for_embeds=False),
            _entity.EntityDetailProperty('Offer 4', True, transform_function=__get_offer_details, index=3, display_inline_for_embeds=False),
            _entity.EntityDetailProperty('Offer 5', True, transform_function=__get_offer_details, index=4, display_inline_for_embeds=False),
            _entity.EntityDetailProperty('Offer 6', True, transform_function=__get_offer_details, index=5, display_inline_for_embeds=False),
            _entity.EntityDetailProperty('Expiring at', True, transform_function=__get_expiration_dates, embed_only=True, display_inline_for_embeds=False),
            _entity.EntityDetailProperty('Expiring at', False, transform_function=__get_expiration_dates, text_only=True, display_inline_for_embeds=False),
        ],
        ),
    'embed_settings': {
        'author_url': _entity.NO_PROPERTY,
        'color': _entity.NO_PROPERTY,
        'description': _entity.EntityDetailProperty('description', False, entity_property_name='Description'),
        'footer': _entity.NO_PROPERTY,
        'icon_url': _entity.EntityDetailProperty('image_url', False, transform_function=_sprites.get_download_sprite_link_by_property, entity_property='12841'),
        'image_url': _entity.EntityDetailProperty('image_url', False, entity_property_name='SpriteId', transform_function=_sprites.get_download_sprite_link_by_property),
        'thumbnail_url': _entity.NO_PROPERTY,
        'timestamp': _entity.NO_PROPERTY,
        'title': _entity.EntityDetailProperty('title', False, entity_property_name=STAR_SYSTEM_MARKER_DESCRIPTION_PROPERTY_NAME),
    }
}





async def init() -> None:
    pass