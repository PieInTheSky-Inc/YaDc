#!/usr/bin/env python
# -*- coding: UTF-8 -*-





# ---------- Constants ----------

SPRITES_BASE_PATH = 'FileService/DownloadSprite?spriteId='










# ---------- Sprites ----------

def get_sprite_download_url(sprite_id: int) -> str:
    return f'{SPRITES_BASE_PATH}{sprite_id}'
