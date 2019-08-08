#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import datetime
from threading import Thread, Lock
import time
import random

import pss_core as core
import utility



def update_data():
    base_url = core.get_base_url()
    old_character_designs = get_character_designs()
    update_character_designs_data(old_character_designs, base_url)
    old_room_designs = get_room_designs()
    update_room_designs_data(old_room_designs, base_url)


# ---------- Character Designs ----------

__character_designs = None
__character_designs_modify_date = None
__CHARACTER_DESIGNS_WRITE_LOCK = Lock()
__CHARACTER_DESIGNS_READ_LOCK = Lock()
__character_designs_write_request = False
__character_designs_reader_count = 0


def update_character_designs_data(old_data, base_url):
    url = f'{base_url}CharacterService/ListAllCharacterDesigns2?languageKey=en'
    raw_data = core.get_data_from_url(url)
    data = core.xmltree_to_dict3(raw_data, 'CharacterDesignId')
    data_changed = data != old_data
    if data_changed:
        __request_write_character_designs()
        can_write = False
        while not can_write:
            can_write = __get_character_design_reader_count() == 0
            if not can_write:
                time.sleep(random.random())
        __write_character_designs(data)
        __finish_write_character_designs()
        return True
    return False


def get_character_designs():
    can_read = False
    while not can_read:
        can_read = not __get_character_designs_write_request()
        if not can_read:
            time.sleep(random.random())
    __add_reader_character_designs()
    result = __read_character_designs()
    __remove_reader_character_designs()
    return result


def __get_character_design_reader_count():
    __CHARACTER_DESIGNS_READ_LOCK.acquire()
    result = __character_designs_reader_count
    __CHARACTER_DESIGNS_READ_LOCK.release()
    return result


def __get_character_designs_write_request():
    __CHARACTER_DESIGNS_WRITE_LOCK.acquire()
    result = __character_designs_write_request
    __CHARACTER_DESIGNS_WRITE_LOCK.release()
    return result


def __request_write_character_designs():
    global __character_designs_write_request
    __CHARACTER_DESIGNS_WRITE_LOCK.acquire()
    __character_designs_write_request = True
    __CHARACTER_DESIGNS_WRITE_LOCK.release()


def __finish_write_character_designs():
    global __character_designs_write_request
    __CHARACTER_DESIGNS_WRITE_LOCK.acquire()
    __character_designs_write_request = False
    __CHARACTER_DESIGNS_WRITE_LOCK.release()


def __write_character_designs(data):
    global __character_designs, __character_designs_modify_date
    __CHARACTER_DESIGNS_WRITE_LOCK.acquire()
    __character_designs = data
    __character_designs_modify_date = utility.get_utcnow()
    __CHARACTER_DESIGNS_WRITE_LOCK.release()


def __add_reader_character_designs():
    global __character_designs_reader_count
    __CHARACTER_DESIGNS_READ_LOCK.acquire()
    __character_designs_reader_count = __character_designs_reader_count + 1
    __CHARACTER_DESIGNS_READ_LOCK.release()


def __remove_reader_character_designs():
    global __character_designs_reader_count
    __CHARACTER_DESIGNS_READ_LOCK.acquire()
    __character_designs_reader_count = __character_designs_reader_count - 1
    __CHARACTER_DESIGNS_READ_LOCK.release()


def __read_character_designs():
    __CHARACTER_DESIGNS_WRITE_LOCK.acquire()
    result = __character_designs
    __CHARACTER_DESIGNS_WRITE_LOCK.release()
    return result


# ---------- Room Designs ----------

__room_designs = None
__room_designs_modify_date = None
__ROOM_DESIGNS_WRITE_LOCK = Lock()
__ROOM_DESIGNS_READ_LOCK = Lock()
__room_designs_write_request = False
__room_designs_reader_count = 0


def update_room_designs_data(old_data, base_url):
    url = f'{base_url}RoomService/ListRoomDesigns2?languageKey=en'
    raw_data = core.get_data_from_url(url)
    data = core.xmltree_to_dict3(raw_data, 'RoomDesignId')
    data_changed = data != old_data
    if data_changed:
        __request_write_room_designs()
        can_write = False
        while not can_write:
            can_write = __get_room_design_reader_count() == 0
            if not can_write:
                time.sleep(random.random())
        __write_room_designs(data)
        __finish_write_room_designs()
        return True
    return False


def get_room_designs():
    can_read = False
    while not can_read:
        can_read = not __get_room_designs_write_request()
        if not can_read:
            time.sleep(random.random())
    __add_reader_room_designs()
    result = __read_room_designs()
    __remove_reader_room_designs()
    return result


def __get_room_design_reader_count():
    __ROOM_DESIGNS_READ_LOCK.acquire()
    result = __room_designs_reader_count
    __ROOM_DESIGNS_READ_LOCK.release()
    return result


def __get_room_designs_write_request():
    __ROOM_DESIGNS_WRITE_LOCK.acquire()
    result = __room_designs_write_request
    __ROOM_DESIGNS_WRITE_LOCK.release()
    return result


def __request_write_room_designs():
    global __room_designs_write_request
    __ROOM_DESIGNS_WRITE_LOCK.acquire()
    __room_designs_write_request = True
    __ROOM_DESIGNS_WRITE_LOCK.release()


def __finish_write_room_designs():
    global __room_designs_write_request
    __ROOM_DESIGNS_WRITE_LOCK.acquire()
    __room_designs_write_request = False
    __ROOM_DESIGNS_WRITE_LOCK.release()


def __write_room_designs(data):
    global __room_designs, __room_designs_modify_date
    __ROOM_DESIGNS_WRITE_LOCK.acquire()
    __room_designs = data
    __room_designs_modify_date = utility.get_utcnow()
    __ROOM_DESIGNS_WRITE_LOCK.release()


def __add_reader_room_designs():
    global __room_designs_reader_count
    __ROOM_DESIGNS_READ_LOCK.acquire()
    __room_designs_reader_count = __room_designs_reader_count + 1
    __ROOM_DESIGNS_READ_LOCK.release()


def __remove_reader_room_designs():
    global __room_designs_reader_count
    __ROOM_DESIGNS_READ_LOCK.acquire()
    __room_designs_reader_count = __room_designs_reader_count - 1
    __ROOM_DESIGNS_READ_LOCK.release()


def __read_room_designs():
    __ROOM_DESIGNS_WRITE_LOCK.acquire()
    result = __room_designs
    __ROOM_DESIGNS_WRITE_LOCK.release()
    return result