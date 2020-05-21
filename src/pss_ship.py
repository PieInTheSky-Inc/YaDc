#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import re

import pss_assert
from cache import PssCache
import pss_core as core
import pss_login as login
import pss_lookups as lookups
import settings
import utility as util


# ---------- Constants ----------

SHIP_DESIGN_BASE_PATH = 'ShipService/ListAllShipDesigns2?languageKey=en'
SHIP_DESIGN_KEY_NAME = 'ShipDesignId'
SHIP_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ShipDesignName'










# ---------- Initilization ----------

__ship_designs_cache = PssCache(
    SHIP_DESIGN_BASE_PATH,
    'ShipDesigns',
    SHIP_DESIGN_KEY_NAME,
    update_interval=60)









# ---------- Helper functions ----------

async def get_inspect_ship_for_user(user_id: str) -> (dict, dict):
    inspect_ship_path = await _get_inspect_ship_base_path(user_id)
    inspect_ship_data = await core.get_data_from_path(inspect_ship_path)
    result = core.xmltree_to_dict2(inspect_ship_data)
    return result.get('User', None), result.get('Ship', None)


async def get_ship_level(ship_info: dict, ship_design_data: dict = None) -> str:
    if not ship_info:
        return None
    if not ship_design_data:
        ship_design_data = await __ship_designs_cache.get_data_dict3()
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


async def _get_inspect_ship_base_path(user_id: str) -> str:
    access_token = await login.DEVICES.get_access_token()
    result = f'ShipService/InspectShip2?accessToken={access_token}&userId={user_id}'
    return result
