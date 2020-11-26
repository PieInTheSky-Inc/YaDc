import pss_core as core
from pss_entity import EntitiesData, EntityInfo, entity_property_has_value





# ---------- Constants ----------

SPRITES_BASE_PATH = 'FileService/DownloadSprite?spriteId='










# ---------- Sprites ----------

async def get_download_sprite_link_by_property(entity_info: EntityInfo, *entities_data: EntitiesData, **kwargs) -> str:
    entity_property = kwargs.get('entity_property')
    return await get_download_sprite_link(entity_property)


async def get_download_sprite_link(sprite_id: str) -> str:
    if entity_property_has_value(sprite_id):
        base_url = await core.get_base_url()
        result = f'{base_url}FileService/DownloadSprite?spriteId={sprite_id}'
        return result
    else:
        return None


def get_sprite_download_url(sprite_id: int) -> str:
    return f'{SPRITES_BASE_PATH}{sprite_id}'
