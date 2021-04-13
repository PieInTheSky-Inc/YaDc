from typing import Dict, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

import pss_core as core
import pss_entity as entity
import pss_login as login
import pss_room as room
import pss_sprites as sprites
from typehints import EntitiesData, EntityInfo
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


async def get_ship_level(ship_info: EntityInfo, ship_design_data: EntitiesData = None) -> Optional[str]:
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





# ---------- Sprite helper functions ----------

async def make_ship_layout_sprite(file_name_prefix: str, user_ship_info: entity.EntityInfo, ship_design_info: entity.EntityInfo, rooms_designs_data: entity.EntitiesData, rooms_designs_sprites_ids: Dict[str, str]) -> str:
    user_id = user_ship_info['UserId']

    brightness_value = float(user_ship_info.get('BrightnessValue', '0'))
    hue_value = float(user_ship_info.get('HueValue', '0'))
    saturation_value = float(user_ship_info.get('SaturationValue', '0'))

    interior_sprite_id = ship_design_info['InteriorSpriteId']
    interior_sprite = await sprites.load_sprite(interior_sprite_id)
    interior_sprite = sprites.enhance_sprite(interior_sprite, brightness=brightness_value, hue=hue_value, saturation=saturation_value)

    interior_grid_sprite = await sprites.load_sprite_from_disk(interior_sprite_id, suffix='grids')
    if not interior_grid_sprite:
        interior_grid_sprite = make_interior_grid_sprite(ship_design_info, interior_sprite.width, interior_sprite.height)
    interior_sprite.paste(interior_grid_sprite, (0, 0), interior_grid_sprite)

    room_frame_sprite_id = ship_design_info.get('RoomFrameSpriteId')
    door_frame_left_sprite_id = ship_design_info.get('DoorFrameLeftSpriteId')
    door_frame_right_sprite_id = ship_design_info.get('DoorFrameRightSpriteId')

    rooms_sprites_cache = {}
    rooms_decorations_sprites_cache = {}
    for ship_room_info in user_ship_info['Rooms'].values():
        room_design_id = ship_room_info[room.ROOM_DESIGN_KEY_NAME]
        room_under_construction = 1 if ship_room_info.get('RoomStatus') == 'Upgrading' or entity.entity_property_has_value(ship_room_info.get('ConstructionStartDate')) else 0

        room_sprite = rooms_sprites_cache.get(room_design_id, {}).get(room_under_construction)

        if not room_sprite:
            room_design_info = rooms_designs_data[room_design_id]
            room_size = (int(room_design_info['Columns']), int(room_design_info['Rows']))

            if room_size == (1, 1):
                room_decoration_sprite = None
            else:
                room_decoration_sprite = rooms_decorations_sprites_cache.get(room_frame_sprite_id, {}).get(door_frame_left_sprite_id, {}).get(room_size)
                if not room_decoration_sprite:
                    room_decoration_sprite = await room.get_room_decoration_sprite(room_frame_sprite_id, door_frame_left_sprite_id, door_frame_right_sprite_id, room_size[0], room_size[1])
                    rooms_decorations_sprites_cache.setdefault(room_frame_sprite_id, {}).setdefault(door_frame_left_sprite_id, {}).setdefault(door_frame_right_sprite_id, {})[room_size] = room_decoration_sprite

            room_sprite_id = room.get_room_sprite_id(room_design_info, room_under_construction, room_decoration_sprite is not None, rooms_designs_sprites_ids)
            room_sprite = await room.create_room_sprite(room_sprite_id, room_decoration_sprite, room_design_info, brightness_value, hue_value, saturation_value)
            rooms_sprites_cache.setdefault(room_design_id, {})[room_under_construction] = room_sprite
        interior_sprite.paste(room_sprite, (int(ship_room_info['Column']) * sprites.TILE_SIZE, int(ship_room_info['Row']) * sprites.TILE_SIZE))

    file_path = sprites.save_sprite(interior_sprite, f'{file_name_prefix}_{user_id}_layout')
    return file_path

def make_interior_grid_sprite(ship_design_info: entity.EntityInfo, width: int, height: int) -> Image.Image:
    result = sprites.create_empty_sprite(width, height)
    interior_grid_draw: ImageDraw.ImageDraw = ImageDraw.Draw(result)
    ship_mask = ship_design_info['Mask']
    ship_height = int(ship_design_info['Rows'])
    ship_width = int(ship_design_info['Columns'])
    grid_mask = np.array([int(val) for val in ship_mask]).reshape((ship_height, ship_width))
    grids = np.where(grid_mask)
    for coordinates in list(zip(grids[1], grids[0])):
        shape = [
            coordinates[0] * sprites.TILE_SIZE,
            coordinates[1] * sprites.TILE_SIZE,
            (coordinates[0] + 1) * sprites.TILE_SIZE - 1,
            (coordinates[1] + 1) * sprites.TILE_SIZE - 1
        ]
        interior_grid_draw.rectangle(shape, fill=None, outline=(0, 0, 0), width=1)
    sprites.save_sprite(result, f'{ship_design_info["InteriorSpriteId"]}_grids')
    return result





# ---------- Initilization ----------

ships_designs_retriever = entity.EntityRetriever(
    SHIP_DESIGN_BASE_PATH,
    SHIP_DESIGN_KEY_NAME,
    SHIP_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='ShipDesigns',
    cache_update_interval=60
)