import aiohttp
import colorsys
import os
from typing import Iterable, Optional

from PIL import Image, ImageEnhance, ImageFont
import numpy as np

import pss_core as core
import pss_entity as entity
import settings
from typehints import EntitiesData, EntityInfo


# ---------- Constants ----------

FUNC_HSV_TO_RGB = np.vectorize(colorsys.hsv_to_rgb)
FUNC_RGB_TO_HSV = np.vectorize(colorsys.rgb_to_hsv)


PIXELATED_FONT: ImageFont.ImageFont

POWER_BAR_COLOR = (55, 255, 142)
POWER_BAR_HEIGHT: int = 5
POWER_BAR_SPACING = 1
POWER_BAR_WIDTH: int = 3
POWER_BAR_Y_START: int = 3

PWD: str


SPRITES_BASE_PATH: str = 'FileService/DownloadSprite?spriteId='
SPRITES_CACHE_PATH: str


TILE_SIZE = 25





# ---------- Sprites ----------


def colorize(image: Image.Image, hue: float) -> Image.Image:
    """
    Colorize PIL image `original` with the given
    `hue` (hue within 0-360); returns another PIL image.
    """
    img = image.convert('RGBA')
    arr = np.array(np.asarray(img).astype('float'))
    new_img = Image.fromarray(shift_hue(arr, hue).astype('uint8'), 'RGBA')

    return new_img


def create_empty_room_sprite(room_width: int, room_height: int) -> Image.Image:
    return create_empty_sprite(room_width * TILE_SIZE, room_height * TILE_SIZE)


def create_empty_sprite(width: int, height: int) -> Image.Image:
    return Image.new('RGBA', (width, height), (255, 0, 0, 0))


async def download_sprite(sprite_id: str) -> str:
    """
    Returns a file path and whether the file already existed before.
    """
    target_path = os.path.join(SPRITES_CACHE_PATH, f'{sprite_id}.png')
    if not os.path.isfile(target_path):
        download_url = await get_download_sprite_link(sprite_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                with open(target_path, 'wb') as f:
                    f.write(await response.read())
    return target_path


def enhance_sprite(sprite: Image.Image, brightness: float = None, hue: float = None, saturation: float = None) -> Image.Image:
    if brightness:
        enhancer = ImageEnhance.Brightness(sprite)
        sprite = enhancer.enhance(brightness + 1)
    if hue:
        sprite = colorize(sprite, hue)
    if saturation:
        enhancer = ImageEnhance.Color(sprite)
        sprite = enhancer.enhance(saturation + 1)
    return sprite


def exists_in_cache(sprite_id: str, prefix: str = None, suffix: str = None) -> str:
    file_name = f'{prefix if prefix else ""}{sprite_id}{suffix if suffix else ""}'
    target_path = os.path.join(SPRITES_CACHE_PATH, f'{file_name}.png')
    if os.path.isfile(target_path):
        return target_path
    else:
        return None


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


def get_file_path(sprite_id: str, prefix: str = None, suffix: str = None) -> str:
    file_name_parts = []
    if prefix:
        file_name_parts.append(prefix)
    file_name_parts.append(sprite_id)
    if suffix:
        file_name_parts.append(suffix)
    return os.path.join(SPRITES_CACHE_PATH, '_'.join(file_name_parts) + '.png')


def get_sprite_download_url(sprite_id: int) -> str:
    return f'{SPRITES_BASE_PATH}{sprite_id}'


async def load_sprite(sprite_id: str) -> Image.Image:
    sprite_path = await download_sprite(sprite_id)
    result = Image.open(sprite_path).convert('RGBA')
    return result


async def load_sprite_from_disk(sprite_id: str, prefix: str = None, suffix: str = None) -> Optional[Image.Image]:
    file_path = get_file_path(sprite_id, prefix=prefix, suffix=suffix)
    try:
        return Image.open(file_path).convert('RGBA')
    except IOError:
        return None


def save_sprite(image: Image.Image, file_name_without_extension: str) -> str:
    target_file_path = os.path.join(SPRITES_CACHE_PATH, f'{file_name_without_extension}.png')
    image.save(target_file_path)
    return target_file_path


def shift_hue(arr: Iterable, hue_out: float) -> Iterable:
    r, g, b, a = np.rollaxis(arr, axis=-1)
    h, s, v = FUNC_RGB_TO_HSV(r, g, b)
    h = (h + hue_out) % 1
    r, g, b = FUNC_HSV_TO_RGB(h, s, v)
    arr = np.dstack((r, g, b, a))
    return arr






# ---------- Initialization ----------

async def init():
    global PWD
    PWD = os.getcwd()
    sprites_cache_path = os.path.join(PWD, settings.SPRITE_CACHE_SUB_PATH)
    if not os.path.isdir(sprites_cache_path):
        os.makedirs(settings.SPRITE_CACHE_SUB_PATH)
    global SPRITES_CACHE_PATH
    SPRITES_CACHE_PATH = sprites_cache_path
    global PIXELATED_FONT
    PIXELATED_FONT = ImageFont.truetype(os.path.join(PWD, 'fonts', 'PSSClone', 'PSSClone.ttf'), 10)