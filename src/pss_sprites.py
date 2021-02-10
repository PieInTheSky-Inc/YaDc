import os
from typing import Optional

import pss_core as core
import pss_entity as entity
from typehints import EntitiesData, EntityInfo

import settings


# ---------- Constants ----------

SPRITES_CACHE_PATH: str

SPRITES_BASE_PATH: str = 'FileService/DownloadSprite?spriteId='





# ---------- Sprites ----------

async def download_sprite(sprite_id: str) -> str:
    download_url = get_download_sprite_link(sprite_id)



async def get_download_sprite_link(sprite_id: str) -> Optional[str]:
    if entity.entity_property_has_value(sprite_id):
        base_url = await core.get_base_url()
        result = f'{base_url}FileService/DownloadSprite?spriteId={sprite_id}'
        return result
    else:
        return None


async def get_download_sprite_link_by_property(entity_info: EntityInfo, *entities_data: EntitiesData, **kwargs) -> str:
    entity_property = kwargs.get('entity_property')
    return await get_download_sprite_link(entity_property)


def get_sprite_download_url(sprite_id: int) -> str:
    return f'{SPRITES_BASE_PATH}{sprite_id}'





# ---------- Initialization ----------

async def init():
    PWD: str = os.getcwd()
    sprites_cache_path = os.path.join(PWD, settings.SPRITE_CACHE_SUB_PATH)
    if not os.path.isdir(sprites_cache_path):
        os.makedirs(settings.SPRITE_CACHE_SUB_PATH)
    global SPRITES_CACHE_PATH
    SPRITES_CACHE_PATH = sprites_cache_path