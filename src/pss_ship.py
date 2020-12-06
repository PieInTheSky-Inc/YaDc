from typing import Dict, Optional, Tuple

import pss_core as core
import pss_entity as entity
import pss_login as login
import utils


# ---------- Constants ----------

SHIP_DESIGN_BASE_PATH: str = 'ShipService/ListAllShipDesigns2?languageKey=en'
SHIP_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'ShipDesignName'
SHIP_DESIGN_KEY_NAME: str = 'ShipDesignId'





# ---------- Helper functions ----------

async def get_inspect_ship_for_user(user_id: str) -> Tuple[Dict, Dict]:
    inspect_ship_path = await __get_inspect_ship_base_path(user_id)
    inspect_ship_data = await core.get_data_from_path(inspect_ship_path)
    result = utils.convert.xmltree_to_dict2(inspect_ship_data)
    return result.get('User', None), result.get('Ship', None)


async def get_ship_level(ship_info: entity.EntityInfo, ship_design_data: entity.EntitiesData = None) -> Optional[str]:
    if not ship_info:
        return None
    if not ship_design_data:
        ship_design_data = await ships_designs_retriever.get_data_dict3()
    ship_design_id = ship_info['ShipDesignId']
    result = ship_design_data[ship_design_id]['ShipLevel']
    return result


async def get_ship_level_for_user(user_id: str) -> str:
    inspect_ship_info = await get_inspect_ship_for_user(user_id)
    result = await get_ship_level(inspect_ship_info)
    return result


async def get_ship_status_for_user(user_id: str) -> str:
    inspect_ship_info = await get_inspect_ship_for_user(user_id)
    result = inspect_ship_info['Ship']['ShipStatus']
    return result


async def __get_inspect_ship_base_path(user_id: str) -> str:
    access_token = await login.DEVICES.get_access_token()
    result = f'ShipService/InspectShip2?accessToken={access_token}&userId={user_id}'
    return result





# ---------- Initilization ----------

ships_designs_retriever = entity.EntityRetriever(
    SHIP_DESIGN_BASE_PATH,
    SHIP_DESIGN_KEY_NAME,
    SHIP_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='ShipDesigns',
    cache_update_interval=60
)