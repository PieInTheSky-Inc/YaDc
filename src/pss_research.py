#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Pixel Starships Research API


# ----- Packages ------------------------------------------------------
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import argparse
import datetime
import re
import os
import pandas as pd
import urllib.request
import uuid
import xml.etree.ElementTree

from pss_core import *

HOME = os.getenv('HOME')
base_url = 'https://{}/'.format(get_production_server())


# ----- Utilities -----------------------------------------------------
def xmltext_to_df(raw_text):
    df = pd.DataFrame()
    root = xml.etree.ElementTree.fromstring(raw_text)
    for c in root:
        for cc in c:
            for i, ccc in enumerate(cc):
                df = df.append(pd.DataFrame(ccc.attrib, index=[i]))
    return df


def seconds_to_str(sec):
    rt = datetime.timedelta(seconds=int(sec))
    if sec % (24*3600) == 0:
        return '{} days'.format(rt.days)
    else:
        return str(rt)


# ----- Text Conversion -----------------------------------------------
def convert_cost(data):
    cost = []
    if data['GasCost'] > 0:
        cost += ['{}k gas'.format(data['GasCost']//1000)]
    if data['StarbuxCost'] > 0:
        cost += ['{} bux'.format(data['StarbuxCost'])]
    return ', '.join(cost)


def research_to_txt(df):
    if len(df) == 0:
        return None
    elif len(df) == 1:
        data = df.iloc[0, :]
        txt = '{}\n'.format(data['ResearchName'])
        txt += '{}\n'.format(data['ResearchDescription'])
        txt += 'Cost: {}\n'.format(convert_cost(data))
        txt += 'Time: {}\n'.format(seconds_to_str(data['ResearchTime']))
        txt += 'Reqd Lab Lvl: {}'.format(data['RequiredLabLevel'])
        return txt

    txt = ''
    for row in df.iterrows():
        idx, data = row
        rtim = seconds_to_str(data['ResearchTime'])
        txt += '{}: t={}, cost={}\n'.format(
            data['ResearchName'], rtim, convert_cost(data))
    return txt


def filter_researchdf(df, search_str):
    research_lookup = df['ResearchName'].str.lower()
    df_subset = df[research_lookup == search_str.lower()]
    if len(df_subset) == 1:
        return df_subset.copy()
    m = [re.search(search_str.lower(), str(s)) is not None for s in research_lookup ]
    return df[m].copy()


def get_research_designs(format='df'):
    raw_file = 'raw/research-designs-raw.txt'
    url = base_url + 'ResearchService/ListAllResearchDesigns2?languageKey=en'
    raw_text = load_data_from_url(raw_file, url, refresh='auto')
    if format == 'df':
        df_research_designs = xmltext_to_df(raw_text)
        cols = ['Argument', 'GasCost', 'ImageSpriteId', 'LogoSpriteId', 'RequiredItemDesignId',
                'RequiredLabLevel', 'RequiredResearchDesignId', 'ResearchDesignId', 'ResearchTime',
                'StarbuxCost']
        df_research_designs[cols] = df_research_designs[cols].astype(int)
        return df_research_designs
    else:
        return xmltree_to_dict3(raw_text, 'ResearchName')


def get_research_names():
    research = get_research_designs(format='dict')
    research_names = list(research.keys())
    return list_to_text(research_names)


# ----- Rooms ---------------------------------------------------------
def get_room_designs():
    path = 'RoomService/ListRoomDesigns2?languageKey=en'
    raw_data = get_data_from_path(path)
    return xmltree_to_dict3(raw_data, 'RoomName')


def get_room_names():
    rooms = get_room_designs()
    room_names = list(rooms.keys())
    return list_to_text(room_names)


def room_to_txt_description(room, id2roomname):
    # Title
    txt = 'ROOM DESCRIPTIONS BETA (this command is under testing, USE IT AT YOUR OWN RISK)\n\n**{} / {}** (Enhancement: {})'.format(
        room['RoomName'], room['RoomShortName'], room['EnhancementType'])
    txt += '\n{}'.format(room['RoomDescription'])
    txt += '\nCategory: {}, Type: {}, Size: {}x{}, Grid Type(s): {}'.format(
        room['CategoryType'], room['RoomType'],
        room['Columns'], room['Rows'], room['SupportedGridTypes'])

    # Power & Reload
    if 'MaxPowerGenerated' in room.keys():
        power = int(room['MaxPowerGenerated'])
        if power > 0:
            txt += '\nMax Power Generated: {}'.format(power)
    if 'MaxSystemPower' in room.keys():
        power = int(room['MaxSystemPower'])
        if power > 0:
            txt += '\nMax Power Used: {}'.format(power)
    if 'ReloadTime' in room.keys():
        reload_time = int(room['ReloadTime'])
        if reload_time > 0:
            txt += '\nReload Time: {} ticks ({} sec)'.format(
                reload_time, int(reload_time)/40.0)
    if 'CooldownTime' in room.keys():
        cooldown_time = int(room['CooldownTime'])
        if cooldown_time > 0:
            txt += '\nCooldown Time: {} ticks ({} sec)'.format(
                cooldown_time, int(cooldown_time)/40.0)

    # Capacity
    if 'Capacity' in room.keys():
        capacity = int(room['Capacity'])
        if capacity > 0:
            txt += '\nCapacity: {}'.format(capacity)

    # Manufacture Capacity & Rate
    if 'RefillUnitCost' in room.keys():
        refill_cost = int(room['RefillUnitCost'])
        if refill_cost > 0:
            txt += '\nRefill Unit Cost: {}'.format(refill_cost)
    if 'ManufactureCapacity' in room.keys():
        capacity = int(room['ManufactureCapacity'])
        if capacity > 0:
            txt += '\nManufacture Capacity: {}'.format(capacity)
    if 'ManufactureRate' in room.keys():
        rate = float(room['ManufactureRate'])
        if rate > 0:
            txt += '\nManufacture Rate: {}'.format(rate)

    # Defense Bonus
    txt += '\nDefense Bonus: {}'.format(room['DefaultDefenceBonus'])

    # Room Construction
    cost = []
    if room['MineralCost'] != '0':
        cost += ['{:,} minerals'.format(int(room['MineralCost']))]
    if room['GasCost'] != '0':
        cost += ['{:,} gas'.format(int(room['GasCost']))]
    price = room['PriceString'].split(':')
    if len(price) > 1:
        unit, price = price
        price = '{:,}'.format(int(price))
    else:
        price = 'NA'
        unit = ''

    construction_time = int(room['ConstructionTime'])
    construction_time = seconds_to_str(construction_time)
    txt += '\nConstruction: {}, Cost: {} {}'.format(
        construction_time, price, unit)

    txt_room_requirement = ''
    if 'UpgradeFromRoomDesignId' in room.keys():
        if room['UpgradeFromRoomDesignId'] != '0':
            upgrade_from = room['UpgradeFromRoomDesignId']
            if upgrade_from in id2roomname.keys():
                upgrade_from = id2roomname[upgrade_from]
            else:
                upgrade_from = 'Room ID {}'.format(upgrade_from)
            txt_room_requirement = ', {}'.format(upgrade_from)
    txt += '\nRequires: lvl {} ship{}'.format(room['MinShipLevel'], txt_room_requirement)

    return txt


def get_room_description(room_name):
    rooms = get_room_designs()
    id2roomname = create_reverse_lookup(rooms, 'RoomDesignId', 'RoomName')
    shortname_lookup = create_reverse_lookup(rooms, 'RoomShortName', 'RoomName')

    raw_description = False
    if room_name[0] == '*':
        room_name = room_name[1:]
        raw_description = True
    if room_name in shortname_lookup.keys():
        room_name = shortname_lookup[room_name]
    if room_name in rooms.keys():
        room = rooms[room_name]
        if raw_description is True:
            return str(room)
        else:
            txt = room_to_txt_description(room, id2roomname)

        if 'MissileDesignId' in room.keys():
            missile_id = room['MissileDesignId']

            missiles = get_missile_designs()
            id2missilename = create_reverse_lookup(missiles, 'MissileDesignId', 'MissileDesignName')

            if missile_id != '0' and missile_id in id2missilename.keys():
                missile=missiles[id2missilename[missile_id]]
                missile_txt = missile_to_txt_description(missile, id2missilename)
                txt += f'\n\n{missile_txt}'
    return txt


# ----- Missiles ------------------------------------------------------
def get_missile_designs(index='MissileDesignName'):
    raw_file = 'raw/missile-designs-raw.txt'
    url = base_url + 'RoomService/ListMissileDesigns'
    raw_text = load_data_from_url(raw_file, url, refresh='auto')
    return xmltree_to_dict3(raw_text, index)


def get_missile_names():
    missiles = get_missile_designs()
    missile_names = list(missiles.keys())
    return list_to_text(missile_names)


def split_camel_case(txt):
    m = re.search('[a-z][A-Z]', txt)
    while m is not None:
        x = m.start()+1
        txt = f'{txt[:x]} {txt[x:]}'
        m = re.search('[a-z][A-Z]', txt)
    return txt


def missile_to_txt_description(missile, id2missilename):
    txt = 'MISSILE DESCRIPTIONS BETA (this command is under testing, USE IT AT YOUR OWN RISK)\n'
    txt += '\n**{MissileDesignName}** (Type: {MissileType})'.format(**missile)

    attributes = ['SystemDamage', 'HullDamage', 'StunLength', 'EMPLength', 'CharacterDamage',
                  'FireLength', 'BreachChance', 'FlightType', 'ExplosionType', 'ExplosionRadius',
                  'Speed', 'Volley', 'VolleyDelay', 'HullPercentageDamage', 'DirectSystemDamage',
                  'ShieldDamage']
    for k, v in missile.items():
        if k in attributes:
            if v != '0':
                txt += f'\n{split_camel_case(k)}: {v}'
    return txt


def get_missile_description(missile_name):
    missiles = get_missile_designs()
    id2missilename = create_reverse_lookup(missiles, 'MissileDesignId', 'MissileDesignName')

    raw_description = False
    if missile_name[0] == '*':
        missile_name = missile_name[1:]
        raw_description = True
    if missile_name in missiles.keys():
        if raw_description is True:
            txt = missiles[missile_name]
        else:
            txt = missile_to_txt_description(missiles[missile_name], id2missilename)
    else:
        txt = f'Missile name {missile_name} not found'
    return txt


# ----- Main ----------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=
        'Pixel Starships Research API')
    parser.add_argument('--list', default=None,
        help='List all [research|rooms]')
    parser.add_argument('--research', default=None,
        help='Get Research Data')
    parser.add_argument('--rooms', default=None,
        help='Get Room Data')
    parser.add_argument('--missile', default=None,
        help='Get Missile Data')
    args = parser.parse_args()

    if args.list is not None:
        if args.list == 'research':
            # python3 pss_research.py --list research
            txt_list = get_research_names()
            for txt in txt_list:
                print(txt)
        elif args.list == 'rooms':
            # python3 pss_research.py --list rooms
            txt_list = get_room_names()
            for txt in txt_list:
                print(txt)
    if args.research is not None:
        # python3 pss_research.py --research "Ion Charge Lv2"
        research_str = args.research
        df_research_designs = get_research_designs()
        df_selected = filter_researchdf(df_research_designs, research_str)
        txt = research_to_txt(df_selected)
        print(txt)
    if args.rooms is not None:
        # The following have been tested
        # python3 pss_research.py --rooms "Android Studio Lv10"
        # python3 pss_research.py --rooms "Armor Lv1"
        # python3 pss_research.py --rooms "Armor Lv12"
        # python3 pss_research.py --rooms "Bedroom Lv1"
        # python3 pss_research.py --rooms "Bio Recycling Lv5"
        # python3 pss_research.py --rooms "Bridge Lv1"
        # python3 pss_research.py --rooms "Bridge Lv11"
        # python3 pss_research.py --rooms "Cloak Generator Lv4"
        # python3 pss_research.py --rooms "Command Center Lv9"
        # python3 pss_research.py --rooms "Fleet Council Lv5"
        # python3 pss_research.py --rooms "Fusion Reactor Lv8"
        # python3 pss_research.py --rooms "Gas Storage Lv13"
        # python3 pss_research.py --rooms "GYM Lv9"
        # python3 pss_research.py --rooms "Hangar Lv1"
        # python3 pss_research.py --rooms "Hangar Lv9"
        # python3 pss_research.py --rooms "Ion Cannon Lv3"
        # python3 pss_research.py --rooms "Laboratory Lv1"
        # python3 pss_research.py --rooms "Laboratory Lv10"
        # python3 pss_research.py --rooms "Lift Lv14"
        # python3 pss_research.py --rooms "Missile Launcher Lv13"
        # python3 pss_research.py --rooms "Photon Disruptor Lv5"
        # python3 pss_research.py --rooms "Plasma Phaser Lv5"
        # python3 pss_research.py --rooms "Radar Lv5"
        # python3 pss_research.py --rooms "Security Gate Lv8"
        # python3 pss_research.py --rooms "Shield Battery Lv7"
        # python3 pss_research.py --rooms "Small Reactor Lv6"
        # python3 pss_research.py --rooms "Teleport Lv8"
        # python3 pss_research.py --rooms "Zaki Tentacle Garden Lv1"

        # python3 pss_research.py --rooms "Service Vent Lv1"
        # python3 pss_research.py --rooms
        txt = get_room_description(args.rooms)
        print(txt)
        # room_str = args.rooms
        # print(room_str)
    if args.missile is not None:
        # python3 pss_research.py --missile "Mining Beam"
        txt = get_missile_description(args.missile)
        print(txt)
