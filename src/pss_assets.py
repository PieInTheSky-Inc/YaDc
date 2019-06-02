
from datetime import datetime
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

SPRITES_SHEET_FILE_NAME = 'sprites.xml'
SPRITES_DICT_FILE_NAME = 'sprites.json'

MUTEX_SPRITE_SHEET = Lock()
MUTEX_SPRITE_DICT = Lock()


def get_sprites_sheet():
    MUTEX_SPRITE_SHEET.aquire()
    result = core.load_data_from_url(SPRITES_SHEET_FILE_NAME, SPRITES_URL)
    MUTEX_SPRITE_SHEET.release()
    return result


def request_sprites_dict():
    raw_text = get_sprites_sheet()
    result = core.convert_3_level_xml_to_dict(raw_text, 'SpriteId', 'Sprite')
    if len(result) > 0:
        core.save_json_to_file(result, SPRITES_DICT_FILE_NAME)
    return result


def read_sprites_dict():
    result = core.read_json_from_file(SPRITES_DICT_FILE_NAME)
    return result


def get_sprites_dict():
    result = {}
    MUTEX_SPRITE_DICT.aquire()
    if core.is_old_file(SPRITES_DICT_FILE_NAME):
        print('[get_sprites_dict] Requesting new sprites dictionary')
        result = request_sprites_dict()
    else:
        print('[get_sprites_dict] Reading cached sprites dictionary')
        result = read_sprites_dict()
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


def get_download_url_for_sprite_id(sprite_id):
    file = get_file_from_sprite_id(sprite_id)
    if file is not None:
        file_name = file['AwsFilename']
        result = f'{ASSET_DOWNLOAD_BASE_URL}{file_name}'
    return result


# ---------- File handling ----------
FILES_URL = f'{BASE_URL}/FileService/ListFiles3?deviceType=DeviceTypeIPhone'

FILES_SHEET_FILE_NAME = 'files.xml'
FILES_DICT_FILE_NAME = 'files.json'

MUTEX_FILES_SHEET = Lock()
MUTEX_FILES_DICT = Lock()


def get_files_sheet():
    MUTEX_FILES_SHEET.aquire()
    result = core.load_data_from_url(FILES_SHEET_FILE_NAME, FILES_URL)
    MUTEX_FILES_SHEET.release()
    return result


def request_files_dict():
    raw_text = get_files_sheet()
    result = core.convert_3_level_xml_to_dict(raw_text, 'Id', 'File')
    if len(result) > 0:
        core.save_json_to_file(result, FILES_DICT_FILE_NAME)
    return result


def read_files_dict():
    result = core.read_json_from_file(FILES_DICT_FILE_NAME)
    return result


def get_files_dict():
    result = {}
    MUTEX_FILES_DICT.aquire()
    if core.is_old_file(FILES_DICT_FILE_NAME):
        print('[get_files_dict] Requesting new files dictionary')
        result = request_files_dict()
    else:
        print('[get_files_dict] Reading cached files dictionary')
        result = read_files_dict()
    MUTEX_FILES_DICT.release()
    return result


def get_file_from_id(file_id):
    files = get_files_dict()
    result = None
    if file_id in files.keys():
        result = files[file_id]
    return result
