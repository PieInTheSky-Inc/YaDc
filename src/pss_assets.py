
from datetime import datetime
import json
import urllib.request
import xml.etree.ElementTree

import pss_core as core
import utility as util


BASE_URL = f'http://{core.get_production_server()}'
ASSET_DOWNLOAD_BASE_URL = 'http://datxcu1rnppcg.cloudfront.net/'
SPRITES_URL = f'{BASE_URL}/FileService/ListSprites2'
FILES_URL = f'{BASE_URL}/FileService/ListFiles3?deviceType=DeviceTypeIPhone'
SPRITES_SHEET_FILE_NAME = 'sprites.xml'
SPRITES_DICT_FILE_NAME = 'sprites.json'
FILES_SHEET_FILE_NAME = 'files.xml'
FILES_DICT_FILE_NAME = 'files.json'


# ---------- Sprite handling ----------
def request_sprites_sheet():
    print('+ called request_sprites_sheet()')
    print(f'[request_sprites_sheet] calling core.load_data_from_url({SPRITES_SHEET_FILE_NAME}, {SPRITES_URL})')
    result = core.load_data_from_url(SPRITES_SHEET_FILE_NAME, SPRITES_URL)
    print(f'[request_sprites_sheet] retrieved {len(result)} bytes')
    print('- exiting request_sprites_sheet()')
    return result


def request_sprites_dict():
    print('+ called request_sprites_dict()')
    raw_text = request_sprites_sheet()
    print('[request_sprites_dict] retrieved raw_text')
    result = core.convert_3_level_xml_to_dict(raw_text, 'SpriteId', 'Sprite')
    print(f'[request_sprites_dict] converted raw_text to dict with {len(result)} rows')
    if len(result) > 0:
        print(f'[request_sprites_dict] saving result to file: {SPRITES_DICT_FILE_NAME}')
        core.save_json_to_file(result, SPRITES_DICT_FILE_NAME)
        print('[request_sprites_dict] stored file')
    print('- exiting request_sprites_dict()')
    return result


def read_sprites_dict():
    print('+ called read_sprites_dict()')
    print(f'[read_sprites_dict] reading sprites dict from file: {SPRITES_DICT_FILE_NAME}')
    result = core.read_json_from_file(SPRITES_DICT_FILE_NAME)
    print(f'[read_sprites_dict] retrieved {len(result)} rows from file: {SPRITES_DICT_FILE_NAME}')
    print('- exiting read_sprites_dict()')
    return result


def get_sprites_dict():
    result = {}
    if core.is_old_file(SPRITES_DICT_FILE_NAME):
        print('[get_sprites_dict] Requesting new sprites dictionary')
        result = request_sprites_dict()
    else:
        print('[get_sprites_dict] Reading cached sprites dictionary')
        result = read_sprites_dict()
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
    if file is None:
        return None
    file_name = file['AwsFilename']
    result = f'{ASSET_DOWNLOAD_BASE_URL}{file_name}'
    return result


# ---------- File handling ----------
def request_files_sheet():
    print('+ called request_files_sheet()')
    print(f'[request_files_sheet] calling core.load_data_from_url({FILES_SHEET_FILE_NAME}, {FILES_URL})')
    result = core.load_data_from_url(FILES_SHEET_FILE_NAME, FILES_URL)
    print(f'[request_files_sheet] retrieved {len(result)} bytes')
    print('- exiting request_files_sheet()')
    return result


def request_files_dict():
    print('+ called request_files_dict()')
    raw_text = request_files_sheet()
    print('[request_files_dict] retrieved raw_text')
    result = core.convert_3_level_xml_to_dict(raw_text, 'Id', 'File')
    print(f'[request_files_dict] converted raw_text to dict with {len(result)} rows')
    print(f'[request_files_dict] isinstance(result, dict): {isinstance(result, dict)}')
    if len(result) > 0:
        print(f'[request_files_dict] saving result to file: {FILES_DICT_FILE_NAME}')
        core.save_json_to_file(result, FILES_DICT_FILE_NAME)
        print('[request_files_dict] stored file')
    print('- exiting request_files_dict()')
    return result


def read_files_dict():
    result = core.read_json_from_file(FILES_DICT_FILE_NAME)
    return result


def get_files_dict():
    result = {}
    if core.is_old_file(FILES_DICT_FILE_NAME):
        print('[get_files_dict] Requesting new files dictionary')
        result = request_files_dict()
    else:
        print('[get_files_dict] Reading cached files dictionary')
        result = read_files_dict()
    return result


def get_file_from_id(file_id):
    print(f'+ called get_file_from_id({file_id})')
    files = get_files_dict()
    print(f'[get_file_from_id] isinstance(files, dict): {isinstance(files, dict)}')
    print(f'[get_file_from_id] retrieved files dict with {len(files)} rows')
    result = None
    print(f'[get_file_from_id] checking if key is in dict: {file_id}')
    if file_id in files.keys():
        result = files[file_id]
        print(f'[get_file_from_id] key found with value: {files[file_id]}')
    else:
        print(f'[get_file_from_id] could not find key: {file_id}')
    print(f'- exiting get_file_from_id with result: {result}')
    return result
