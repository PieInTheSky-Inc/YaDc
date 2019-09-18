#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from cache import PssCache
import pss_core as core
import pss_lookups as lookups


# ---------- Constants ----------

ROOM_DESIGN_BASE_PATH = 'RoomService/ListRoomDesigns2?languageKey=en'
ROOM_DESIGN_KEY_NAME = 'RoomDesignId'
ROOM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'RoomName'



# ---------- Initilization ----------

__room_designs_cache = PssCache(
    ROOM_DESIGN_BASE_PATH,
    'RoomDesigns',
    ROOM_DESIGN_KEY_NAME)





# ---------- Helper functions ----------


def get_room_details_from_id_as_text(room_id: str, room_designs_data: dict = None) -> list:
    if not room_designs_data:
        room_designs_data = __room_designs_cache.get_data_dict3()

    room_info = room_designs_data[room_id]
    return get_room_details_from_data_as_text(room_info)


def get_room_details_from_data_as_text(room_info: dict) -> list:

    pass


def get_room_details_short_from_id_as_text(room_id: str, room_designs_data: dict = None) -> list:
    if not room_designs_data:
        room_designs_data = __room_designs_cache.get_data_dict3()

    room_info = room_designs_data[room_id]
    return get_room_details_short_from_data_as_text(room_info)


def get_room_details_short_from_data_as_text(room_info: dict) -> list:

    pass





# ---------- Room info ----------