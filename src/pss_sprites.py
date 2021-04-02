import aiohttp
import aiofiles
import os
from typing import Optional

from PIL.Image import Image

import pss_core as core
import pss_entity as entity
import settings
from typehints import EntitiesData, EntityInfo


# ---------- Constants ----------

PWD: str

SPRITES_BASE_PATH: str = 'FileService/DownloadSprite?spriteId='
SPRITES_CACHE_PATH: str





# ---------- Sprites ----------

async def download_sprite(sprite_id: str) -> str:
    target_path = os.path.join(PWD, sprite_id, '.png')
    if not os.path.isfile(target_path):
        download_url = await get_download_sprite_link(sprite_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                async with aiofiles.open(target_path, 'wb') as f:
                    await f.write(await response.read())
    return target_path


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


async def load_sprite(sprite_id: str) -> Image:
    sprite_path = await download_sprite(sprite_id)
    result = Image.open(sprite_path).convert('RGBA')
    return result





# ---------- Initialization ----------

async def init():
    global PWD
    PWD = os.getcwd()
    sprites_cache_path = os.path.join(PWD, settings.SPRITE_CACHE_SUB_PATH)
    if not os.path.isdir(sprites_cache_path):
        os.makedirs(settings.SPRITE_CACHE_SUB_PATH)
    global SPRITES_CACHE_PATH
    SPRITES_CACHE_PATH = sprites_cache_path