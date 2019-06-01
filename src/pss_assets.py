

import urllib.request
import xml.etree.ElementTree

import pss_core as core
import utility as util

base_url = f'http://{core.get_production_server()}/'
ASSET_DOWNLOAD_URL = 'http://datxcu1rnppcg.cloudfront.net/'

# ---------- Sprite handling ----------
def request_new_sprites_sheet():
    print('+ called request_new_sprites_sheet()')
    get_sprites_url = f'{base_url}/FileService/ListSprites2'
    print(f'[request_new_sprites_sheet] retrieved url: {get_sprites_url}')
    data = urllib.request.urlopen(get_sprites_url).read()
    print(f'[request_new_sprites_sheet] retrieved raw data')
    print(f'- exiting request_new_sprites_sheet()')
    return data.decode()


def get_sprites_dict(raw_text):
    print('+ called get_sprites_dict(raw_text)')
    debug_i = 0
    result = {}
    root = xml.etree.ElementTree.fromstring(raw_text)
    for c in root:
        for cc in c:
            for ccc in cc:
                if ccc.tag != 'Sprite':
                    continue
                debug_i += 1
                sprite_id = ccc.attrib['SpriteId']
                result[sprite_id] = ccc.attrib
    print(f'[get_sprites_dict] retrieved {debug_i} sprite definitions')
    print(f'- exiting get_sprites_dict(raw_text)')
    return result


def request_new_sprites_dict():
    print('+ called request_new_sprites_dict()')
    raw_text = request_new_sprites_sheet()
    print(f'[request_new_sprites_dict] retrieved raw_text')
    result = get_sprites_dict(raw_text)
    print(f'[request_new_sprites_dict] retrieved dictionary of sprites')
    print(f'- exiting request_new_sprites_dict()')
    return result


def get_sprite_from_id(sprite_id):
    print(f'+ called get_sprite_from_id({sprite_id})')
    sprites = request_new_sprites_dict()
    print(f'[get_sprite_from_id] requested new dictionary of sprites')
    result = None
    if sprite_id in sprites.keys():
        print(f'[get_sprite_from_id] found sprite with SpriteId: {sprite_id}')
        result = sprites[sprite_id]
    print(f'- exiting get_sprite_from_id({sprite_id}) with result: {result}')
    return result


def get_file_from_sprite_id(sprite_id):
    print(f'+ called get_file_from_sprite_id({sprite_id})')
    sprite = get_sprite_from_id(sprite_id)
    print(f'[get_file_from_sprite_id] retrieved sprite from sprite_id: {sprite}')
    file_id = sprite['ImageFileId']
    print(f'[get_file_from_sprite_id] retrieved file_id from sprite: {file_id}')
    result = get_file_from_id(file_id)
    print(f'[get_file_from_sprite_id] retrieved file from file_id: {result}')
    print(f'- exiting get_file_from_sprite_id({sprite_id}) with result: {result}')
    return result


def get_download_url_for_sprite_id(sprite_id):
    print(f'+ called get_download_url_for_sprite_id({sprite_id})')
    file = get_file_from_sprite_id(sprite_id)
    print(f'[get_download_url_for_sprite_id] retrieved file from sprite_id: {file}')
    if file is None:
        print(f'- exiting get_download_url_for_sprite_id({sprite_id}) without result')
        return None
    file_name = file['AwsFilename']
    print(f'[get_download_url_for_sprite_id] retrieved AwsFilename from file: {file_name}')
    result = f'{ASSET_DOWNLOAD_URL}{file_name}'
    print(f'- exiting get_download_url_for_sprite_id({sprite_id}) with result: {result}')
    return result


# ---------- File handling ----------
def request_new_files_sheet():
    print('+ called request_new_files_sheet()')
    get_files_url = f'{base_url}/FileService/ListFiles3?deviceType=DeviceTypeIPhone'
    print(f'[request_new_files_sheet] retrieved url: {get_files_url}')
    data = urllib.request.urlopen(get_files_url).read()
    print(f'[request_new_files_sheet] retrieved raw data')
    print(f'- exiting request_new_files_sheet()')
    return data.decode()


def get_files_dict(raw_text):
    print('+ called get_files_dict(raw_text)')
    debug_i = 0
    result = {}
    root = xml.etree.ElementTree.fromstring(raw_text)
    for c in root:
        for cc in c:
            for ccc in cc:
                if ccc.tag != 'File':
                    continue
                    debug_i += 1
                file_id = ccc.attrib['Id']
                result[file_id] = ccc.attrib
    print(f'[get_files_dict] retrieved {debug_i} file definitions')
    print(f'- exiting get_files_dict(raw_text)')
    return result


def request_new_files_dict():
    print('+ called request_new_files_dict()')
    raw_text = request_new_files_sheet()
    print(f'[request_new_files_dict] retrieved raw_text')
    result = get_files_dict(raw_text)
    print(f'[request_new_files_dict] retrieved dictionary of files')
    print(f'- exiting request_new_files_dict()')
    return result


def get_file_from_id(file_id):
    print(f'+ called get_file_from_id({file_id})')
    files = request_new_files_dict()
    print(f'[get_file_from_id] requested new dictionary of files')
    result = None
    if file_id in files.keys():
        print(f'[get_file_from_id] found file with Id: {file_id}')
        result = files[file_id]
    print(f'- exiting get_file_from_id({file_id}) with result: {result}')
    return result
