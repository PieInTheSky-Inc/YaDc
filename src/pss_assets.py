
from datetime import datetime, timezone
import json
from threading import Thread, Lock
import urllib.request
import xml.etree.ElementTree

import pss_core as core
import utility as util


BASE_URL = f'http://{core.get_production_server()}'
ASSET_DOWNLOAD_BASE_URL = 'http://datxcu1rnppcg.cloudfront.net/'


# ---------- Sprite handling ----------
SPRITES_URL = f'{BASE_URL}/FileService/ListSprites2'
SPRITES_DOWNLOAD_URL = f'{BASE_URL}/FileService/DownloadSprite?spriteId='

SPRITES_DICT_CACHE = None
SPRITES_DICT_CACHE_RETRIEVEDDATE = datetime(1, 1, 1)

SPRITES_SHEET_FILE_NAME = 'sprites.xml'
SPRITES_DICT_FILE_NAME = 'sprites.json'

MUTEX_SPRITE_SHEET = Lock()
MUTEX_SPRITE_DICT = Lock()


def get_sprites_sheet():
    MUTEX_SPRITE_SHEET.acquire()
    result = core.load_data_from_url(SPRITES_SHEET_FILE_NAME, SPRITES_URL)
    MUTEX_SPRITE_SHEET.release()
    return result


def request_sprites_dict():
    raw_text = get_sprites_sheet()
    utc_now = util.get_utcnow()
    result = core.convert_3_level_xml_to_dict(raw_text, 'SpriteId', 'Sprite')
    if len(result) > 0:
        global SPRITES_DICT_CHACHE
        global SPRITES_DICT_CACHE_RETRIEVEDDATE
        SPRITES_DICT_CHACHE = result
        SPRITES_DICT_CACHE_RETRIEVEDDATE = utc_now
    return result


def read_sprites_dict():
    result = core.read_json_from_file(SPRITES_DICT_FILE_NAME)
    return result


def get_sprites_dict():
    result = {}
    MUTEX_SPRITE_DICT.acquire()
    if SPRITES_DICT_CACHE is None or util.is_older_than(SPRITES_DICT_CACHE_RETRIEVEDDATE, hours=1):
        print('[get_sprites_dict] Requesting new sprites dictionary')
        result = request_sprites_dict()
    else:
        print('[get_sprites_dict] Reading cached sprites dictionary')
        result = SPRITES_DICT_CACHE
    MUTEX_SPRITE_DICT.release()
    return result


def get_sprite_from_id(sprite_id):
    sprites = get_sprites_dict()
    result = None
    if sprite_id in sprites.keys():
        result = sprites[sprite_id]
    return result


def get_file_from_sprite_id(sprite_id):
    sprite = get_sprite_from_id(sprite_id)
    file_id = sprite['ImageFileId']
    result = get_file_from_id(file_id)
    return result


def get_download_url_for_sprite_id(sprite_id, use_endpoint):
    file = get_file_from_sprite_id(sprite_id)
    if file is not None:
        if use_endpoint:
            result = f'{SPRITES_DOWNLOAD_URL}{sprite_id}'
        else:
            file_name = file['AwsFilename']
            result = f'{ASSET_DOWNLOAD_BASE_URL}{file_name}'
    return result


# ---------- File handling ----------
FILES_URL = f'{BASE_URL}/FileService/ListFiles3?deviceType=DeviceTypeIPhone'

FILES_DICT_CHACHE = None
FILES_DICT_CACHE_MODIFYDATE = datetime(1, 1, 1)

FILES_SHEET_FILE_NAME = 'files.xml'
FILES_DICT_FILE_NAME = 'files.json'

MUTEX_FILES_SHEET = Lock()
MUTEX_FILES_DICT = Lock()


def get_files_sheet():
    MUTEX_FILES_SHEET.acquire()
    result = core.load_data_from_url(FILES_SHEET_FILE_NAME, FILES_URL)
    MUTEX_FILES_SHEET.release()
    return result


def request_files_dict():
    raw_text = get_files_sheet()
    utc_now = util.get_utcnow()
    result = core.convert_3_level_xml_to_dict(raw_text, 'Id', 'File')
    if len(result) > 0:
        global FILES_DICT_CHACHE
        global FILES_DICT_CACHE_RETRIEVEDDATE
        FILES_DICT_CHACHE = result
        FILES_DICT_CACHE_RETRIEVEDDATE = utc_now
    return result


def read_files_dict():
    result = core.read_json_from_file(FILES_DICT_FILE_NAME)
    return result


def get_files_dict():
    result = {}
    MUTEX_FILES_DICT.acquire()
    if FILES_DICT_CHACHE is None or util.is_older_than(FILES_DICT_CACHE_RETRIEVEDDATE, hours=1):
        print('[get_files_dict] Requesting new files dictionary')
        result = request_files_dict()
    else:
        print('[get_files_dict] Reading cached files dictionary')
        result = FILES_DICT_CHACHE
    MUTEX_FILES_DICT.release()
    return result


def get_file_from_id(file_id):
    files = get_files_dict()
    result = None
    if file_id in files.keys():
        result = files[file_id]
    return result
