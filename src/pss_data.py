#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import datetime
from threading import Thread, Lock
import time
import random

import cache
import pss_core as core
import utility as util


UPDATE_INTERVAL = datetime.timedelta(minutes=30)
character_designs = None
room_designs = None


def update_data():
    base_url = core.get_base_url()

    global character_designs
    if not character_designs:
        update_url = f'{base_url}CharacterService/ListAllCharacterDesigns2?languageKey=en'
        character_designs = cache.PssCache(update_url, 'CharacterDesigns', 'CharacterDesignId')
        character_designs.update_data(None)
    else:
        old_character_designs = character_designs.get_data()
        character_designs.update_data(old_character_designs)

    global room_designs
    if not room_designs:
        update_url = f'{base_url}RoomService/ListRoomDesigns2?languageKey=en'
        room_designs = cache.PssCache(update_url, 'RoomDesigns', 'RoomDesignId')
        room_designs.update_data(None)
    else:
        old_room_designs = room_designs.get_data()
        room_designs.update_data(old_room_designs)