#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Pixel Starships Prestige & Character Sheet API


# ----- Packages ------------------------------------------------------
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import argparse
import csv
import numpy as np
import os
import pandas as pd
import re
import sqlite3
import sys
import urllib.request
import xml.etree.ElementTree
from io import StringIO
from pss_core import *


# Discord limits messages to 2000 characters
MESSAGE_CHARACTER_LIMIT = 2000
RAW_CHARFILE = "raw/pss-chars-raw.txt"
RAW_COLLECTIONSFILE = 'raw/pss-collections-raw.txt'
DB_FILE = "pss.db"

base_url = 'http://{}/'.format(get_production_server())
next_target = {'Common': 'Elite',
               'Elite': 'Unique',
               'Unique': 'Epic',
               'Epic': 'Hero',
               'Hero': 'Legendary',
               'all': 'all'}

reqd_folders = ['raw', 'data']
for folder in reqd_folders:
    if os.path.isdir(folder) is not True:
        os.mkdir(folder)


# ----- Character Sheet -----------------------------------------------
def request_new_char_sheet():
    # Download Character Sheet from PSS Servers
    url = base_url + 'CharacterService/ListAllCharacterDesigns?languageKey=en'
    data = urllib.request.urlopen(url).read()
    return data.decode()


def save_char_sheet_raw(char_sheet):
    with open(RAW_CHARFILE, 'w') as f:
        f.write(char_sheet)


def load_char_sheet_raw(refresh=False):
    if os.path.isfile(RAW_CHARFILE) and refresh is False:
        with open(RAW_CHARFILE, 'r') as f:
            raw_text = f.read()
    else:
        raw_text = request_new_char_sheet()
        save_char_sheet_raw(raw_text)
    return raw_text


def save_char_sheet(char_sheet,
                    filename='pss-chars.txt'):
    # Process Character Sheet to CSV format
    tree = xml.etree.ElementTree.parse(StringIO(char_sheet))
    root = tree.getroot()
    tbl = {}
    rtbl = {}
    # rarity = {}
    for c in root.findall('ListAllCharacterDesigns'):
        for cc in c.findall('CharacterDesigns'):
            for ccc in cc.findall('CharacterDesign'):
                char_id = ccc.attrib['CharacterDesignId']
                char_dn = ccc.attrib['CharacterDesignName']
                # rarity = ccc.attrib['Rarity']
                tbl[char_id] = char_dn
                rtbl[char_dn] = char_id

    # Save Character Sheet to text file
    with open(filename, 'w') as f:
        for key in tbl.keys():
            f.write('{},{}\n'.format(key, tbl[key]))
    return tbl, rtbl


def load_char_sheet(filename='pss-chars.txt'):
    # Load character sheet from text file
    with open(filename, 'r') as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        tbl = {}
        rtbl = {}
        for row in readCSV:
            char_id = row[0]
            char_dn = row[1]
            tbl[char_id] = char_dn
            rtbl[char_dn] = char_id
    return tbl, rtbl


def get_char_sheet(refresh='auto'):
    url = base_url + 'CharacterService/ListAllCharacterDesigns?languageKey=en'
    raw_text = load_data_from_url(RAW_CHARFILE, url, refresh=refresh)
    ctbl = xmltree_to_dict3(raw_text, 'CharacterDesignId')
    tbl_i2n = create_reverse_lookup(ctbl, 'CharacterDesignId', 'CharacterDesignName')
    tbl_n2i = create_reverse_lookup(ctbl, 'CharacterDesignName', 'CharacterDesignId')
    rarity = create_reverse_lookup(ctbl, 'CharacterDesignName', 'Rarity')
    return ctbl, tbl_i2n, tbl_n2i, rarity


def charsheet_to_df(raw_text):
    df = pd.DataFrame()
    root = xml.etree.ElementTree.fromstring(raw_text)
    for c in root.findall('ListAllCharacterDesigns'):
        for cc in c.findall('CharacterDesigns'):
            for i, ccc in enumerate(cc.findall('CharacterDesign')):
                row = pd.DataFrame(ccc.attrib, index=[i])
                df = df.append(row)
    df['CharacterDesignId'] = df['CharacterDesignId'].astype(int)
    return df


# ----- Parsing -------------------------------------------------------
def fix_char(char):
    # Convert to lower case & non alpha-numeric
    char = re.sub('[^a-z0-9]', '', char.lower())
    char = re.sub("captain", "captn", char)
    char = re.sub("lolita", "lollita", char)
    return char


def parse_char_name(char, rtbl):
    char_original = list(rtbl.keys())
    char_lookup = [ fix_char(s) for s in char_original ]
    char_fixed  = fix_char(char)

    # 1. Look for an exact match
    if char_fixed in char_lookup:
        idx = char_lookup.index(char_fixed)
        return char_original[idx]

    # 2. Perform a search instead
    m = [ re.search(char_fixed, s) is not None for s in char_lookup ]
    if sum(m) > 0:
        # idx = m.index(True)  # forward search for match
        idx = len(m)-1 - m[::-1].index(True)  # reverse search
        return char_original[idx]
    return None


def char2id(char, rtbl):
    if isinstance(char, str):
        char_name = parse_char_name(char, rtbl)
        if char_name is not None:
            return rtbl[char_name], char_name
        else:
            print("char2id(): could not find the character '{}'".format(char))
            return None, char
    else:
        return char, char


# ----- Prestige API --------------------------------------------------
def get_prestige_data_from_url(char_id, action):
    if action == 'to':
        url = base_url + 'CharacterService/PrestigeCharacterTo?characterDesignId={}'.format(char_id)
        attrib = 'PrestigeCharacterTo'
    elif action == 'from':
        url = base_url + 'CharacterService/PrestigeCharacterFrom?characterDesignId={}'.format(char_id)
        attrib = 'PrestigeCharacterFrom'
    else:
        print('action = "{}" is invalid'.format(action))
        return None
    txt = get_data_from_url(url)
    # print(txt)
    return txt, url


def prestigedata_to_df(raw_text):
    timestamp = None
    df = pd.DataFrame()
    root = xml.etree.ElementTree.fromstring(raw_text)
    for c in root.findall('PrestigeCharacterFrom'):
        timestamp = c.attrib
        for cc in c.findall('Prestiges'):
            for i, p in enumerate(cc.findall('Prestige')):
                row = pd.DataFrame(p.attrib, index=[i])
                df = df.append(row)
    if timestamp is not None:
        df['timestamp'] = timestamp['timestamp']
    return df


def request_prestige_data_multiple(char_ids):
    print('Downloading prestige data for the following ids:')
    df = pd.DataFrame()
    for char_id in char_ids:
        print('{} '.format(char_id), end='')
        sys.stdout.flush()
        data, _ = get_prestige_data_from_url(char_id, 'from')
        assert isinstance(data, str)
        row_df = prestigedata_to_df(data)
        df = df.append(row_df)
    print()

    df.CharacterDesignId1 = df.CharacterDesignId1.astype(int)
    df.CharacterDesignId2 = df.CharacterDesignId2.astype(int)
    df.ToCharacterDesignId = df.ToCharacterDesignId.astype(int)
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%dT%H:%M:%S')
    return df


def generate_prestige_data_filename():
    now = datetime.datetime.now()
    now = now.strftime('%Y%m%d')
    return 'data/prestige-{}.csv'.format(now)


def get_prestige_df_from_cache_or_cloud(refresh=False):
    filename = generate_prestige_data_filename()
    if os.path.isfile(filename) and refresh is not True:
        df = pd.read_csv(filename)
    else:
        # df = request_prestige_data_multiple(all_char_ids)
        df = request_prestige_data_multiple(tbl_i2n.keys())
        df.to_csv(filename)
    return df


def replace_value_in_table(df, row_index, col_index, new_value):
    conflicting_data = False
    old_value = df.loc[row_index, col_index]
    if old_value == '':
        df.loc[row_index, col_index] = new_value
    elif old_value != new_value:
        print('Conflicting data at row={}, col={}: {} -> {}'.format(
            row_index, col_index, old_value, new_value))
        conflicting_data = True
    return conflicting_data


def prestige_df_to_table(prestige_df, char_ids, char_lookup):
    if isinstance(char_ids[0], str):
        char_ids = [ int(i) for i in char_ids ]
    tbl = pd.DataFrame(columns=char_ids, index=char_ids)
    tbl.fillna('', inplace=True)

    conflicting_data = False
    for char_id in char_ids:
        rows = prestige_df[prestige_df.CharacterDesignId1 == char_id]
        for row in rows.iterrows():
            data = row[1]
            char_id1 = data['CharacterDesignId1']
            char_id2 = data['CharacterDesignId2']
            char_new = data['ToCharacterDesignId']
            char_new = char_lookup[str(char_new)]
            if ( (char_id1 in char_ids) and
                 (char_id2 in char_ids) ):
                c1 = replace_value_in_table(tbl, char_id1, char_id2, char_new)
                c2 = replace_value_in_table(tbl, char_id2, char_id1, char_new)
                conflicting_data = conflicting_data or (c1 or c2)

    tbl.columns = [ char_lookup[str(ii)] for ii in tbl.columns ]
    tbl.index = [ char_lookup[str(ii)] for ii in tbl.index ]
    return tbl


def remove_duplicates(x_arr):
    """Removes duplicates from a list of lists
    where the first 2 columns are interchangeable.
    Note that the first 2 entries of each row will be sorted."""
    if len(x_arr) == 0:
        return x_arr

    y_arr = [ sorted(x[:2]) + x[2:] for x in x_arr ]
    y_arr = pd.DataFrame(y_arr)  #, columns=[0,1,2])
    # y_arr.sort_values(by=0, inplace=True)
    try:
        y_arr.drop_duplicates(inplace=True)
    except Exception as e:
        print('Exception: {}'.format(e))
        print(y_arr)

    return y_arr.values.tolist()


def xmltree_to_prestige_dict(raw_text):
    ptbl = []
    root = xml.etree.ElementTree.fromstring(raw_text)

    for c in root:
        for cc in c:
            for p in cc:
                char_id1 = p.attrib['CharacterDesignId1']
                char_id2 = p.attrib['CharacterDesignId2']
                char_new = p.attrib['ToCharacterDesignId']
                ptbl.append([char_id1, char_id2, char_new])
    return ptbl


def condense_txt_list(txt_list, MESSAGE_CHARACTER_LIMIT):
    txt = ''
    new_list = []
    for i, line in enumerate(txt_list):
        if i > 0:
            line = '\n' + line
        if len(txt+line) > MESSAGE_CHARACTER_LIMIT:
            new_list.append(txt)
            txt = line
        else:
            txt += line
    new_list.append(txt)
    return new_list


def prestige_tbl_to_txt(ptbl, tbl_i2n, direction):
    """Convert prestige table into a text list
    direction = to, from, or full (default)"""
    assert len(ptbl) > 0
    if direction == 'from':
        c1_original = ptbl[0][0]
        assert c1_original in tbl_i2n.keys()
        c1_original = tbl_i2n[c1_original]

    txt_list = []
    for row in ptbl:
        c1 = row[0]
        c2 = row[1]
        c3 = row[2]
        if c1 in tbl_i2n.keys():
            c1 = tbl_i2n[c1]
        if c2 in tbl_i2n.keys():
            c2 = tbl_i2n[c2]
        if c3 in tbl_i2n.keys():
            c3 = tbl_i2n[c3]

        if direction == "to":
            line = '{} + {}'.format(c1, c2)
        elif direction == "from":
            if c1 != c1_original:
                print('c1 = {} / {} (conflict)'.format(c1, c1_original))
                assert c1 == c1_original  # Force the code to quit
            line = '+ {} -> {}'.format(c2, c3)
        else:
            line = '{} + {} -> {}'.format(c1, c2, c3)
        txt_list.append(line)

    txt_list.sort()
    txt_list = condense_txt_list(txt_list, MESSAGE_CHARACTER_LIMIT)
    return txt_list


def get_prestige(char_input, direction, raw=False):
    ctbl, tbl_i2n, tbl_n2i, rarity = get_char_sheet()
    char_id, char_fixed = char2id(char_input, tbl_n2i)
    if char_id is None:
        return ["Character '{}' not found".format(char_fixed)], False

    raw_text, url = get_prestige_data_from_url(char_id, direction)
    debug_txt = '\n\n**Debugging Information**'
    debug_txt += '\nURL: {}'.format(url)
    debug_txt += '\nRaw data from server:'
    debug_txt = [ debug_txt,
                  '`{}`'.format(raw_text[:(MESSAGE_CHARACTER_LIMIT-5)]) ]

    ptbl = xmltree_to_prestige_dict(raw_text)
    if raw is False and direction != 'from':
        # Duplicate removal is no required if direction == 'from'
        ptbl = remove_duplicates(ptbl)

    if len(ptbl) == 0:
        prestige_txt = "No prestige combinations found for '{}'".format(char_fixed)
        crew_rarity = rarity[char_fixed]
        if crew_rarity == 'Special':
            prestige_txt += '\nNote that it is not possible to prestige to/from a crew of rarity "Special"'
        elif crew_rarity == 'Legendary' and direction == 'from':
            prestige_txt += '\nNote that crew of rarity "Legendary" cannot be prestiged any further'
        elif raw is True:
            prestige_txt += debug_txt
        return [prestige_txt], True

    if direction == "to":
        prestige_txt = ['**{}** can be prestiged from:'.format(char_fixed)]
    elif direction == "from":
        prestige_txt = ['**{}**'.format(char_fixed)]

    prestige_txt += prestige_tbl_to_txt(ptbl, tbl_i2n, direction)
    if raw is True:
        prestige_txt += debug_txt
    return prestige_txt, True


def show_new_chars(action='prestige'):
    tbl1, rtbl1 = load_char_sheet('pss-chars.txt')
    _, tbl2, rtbl2, _ = get_char_sheet()
    # ctbl, tbl_i2n, tbl_n2i, rarity = get_char_sheet()
    old_ids = tbl1.keys()
    new_ids = tbl2.keys()
    new_chars = False
    for ii in new_ids:
        if ii not in old_ids:
            if action == 'prestige':
                content, ptbl = get_prestige_data(
                    tbl2[ii], 'from', rtbl2)
                print_prestige_formulas(ptbl, tbl2)
            else:
                print('{}'.format(tbl2[ii]))
            new_chars = True
    return new_chars


# ----- Crew Database -------------------------------------------------
def init_database(filename):
    conn = sqlite3.connect(filename)
    c = conn.cursor()
    try:
        c.execute('CREATE TABLE chars (discord_id TEXT PRIMARY KEY, discord_name TEXT, current_crew TEXT, target_crew TEXT)')
    except sqlite3.OperationalError:
        print('SQLite table already exists')
    conn.commit()
    conn.close()


def read_database(filename, discord_id: str):
    conn = sqlite3.connect(filename)
    c = conn.cursor()
    # sql_query = "SELECT * FROM chars WHERE discord_id='{}'".format(discord_id)
    sql_query = "SELECT * FROM chars WHERE discord_id=?"
    c.execute(sql_query, (discord_id,))
    rows = c.fetchall()
    for row in rows:
        print('{} | {} | {} | {}'.format(
            row[0], row[1], row[2], row[3]))
    conn.close()
    return rows


def extract_row_data(rows, column):
    if len(rows) > 0:
        row = rows[0]
        if column == 'current_crew':
            crew_ids = row[2]
        elif column == 'target_crew':
            crew_ids = row[3]

        # print('Column `{}` will be updated:'.format(column))
        # print('{} (id#{}): {} = {} (current)'.format(row[1], row[0], column, crew_ids))

        if crew_ids is None or crew_ids == '':
            return row, []
        else:
            return row, crew_ids.split(',')
    else:
        return None, []


def custom_sqlite_command(filename, command_str):
    conn = sqlite3.connect(filename)
    c = conn.cursor()
    c.execute(command_str)
    conn.commit()
    conn.close()


def insert_data(db_file, discord_id, discord_name, current_crew, target_crew):
    current_crew = ','.join(current_crew)
    target_crew = ','.join(target_crew)
    print('Crew IDs: current_crew={}, target_crew={}'.format(
        current_crew, target_crew))

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute('INSERT INTO chars VALUES ("{}", "{}", "{}", "{}")'.format(
        discord_id, discord_name, current_crew, target_crew))
    conn.commit()
    conn.close()


def update_data(db_file: str, discord_id: int, column: str, crew_list: list):
    # print('update_data()')
    # print(db_file, type(db_file))
    # print(discord_id, type(discord_id))
    # print(column, type(column))
    # print(crew_list, type(crew_list))

    crew_list = ','.join(crew_list)
    print('Crew IDs to be updated in column {}: {}'.format(
        column, crew_list))

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    sql_str = "UPDATE chars SET {}='{}' WHERE discord_id='{}'".format(
        column, crew_list, discord_id)
    # sql_data = ("{}".format(crew_list),)
    # print('c.execute("{}", {})'.format(sql_str, sql_data))
    print('c.execute("{}")'.format(sql_str))
    try:
        # c.execute(sql_str, data)
        c.execute(sql_str)
        conn.commit()
    except sqlite3.Error as e:
        print('Error: {}'.format(e))
        print('Error Message: {}'.format(e.message))
    except Exception as e:
        print('Exception: {}'.format(e))

    if conn.total_changes != 1:
        print('Number of rows changed for "{}" = {} (expected value = 1)'.format(
            sql_str, conn.total_changes))
    conn.close()
    # print('conn.close() completed')


def crewtxt_to_crewnames(crew_txt, prefix='Adding '):
    crew_names = crew_txt.split(',')

    txt = ''
    crew_ids = []
    for crew_name in crew_names:
        char_id, char_fixed = char2id(crew_name, tbl_n2i)
        assert isinstance(char_id, str)
        crew_ids += [ char_id ]
        txt += '{}crew "{}" (id={})\n'.format(prefix, char_fixed, char_id)
    txt = txt.strip()
    return crew_ids, txt


def add_crew(db_file, discord_id, discord_name, column, crew_txt):
    rows = read_database(db_file, discord_id)
    row, crew_ids = extract_row_data(rows, column)
    if row is not None:
        update_rows = True
    else:
        update_rows = False

    new_crew_ids, txt = crewtxt_to_crewnames(crew_txt)
    print('new_crew_ids = {} (to be added)'.format(new_crew_ids))
    crew_ids += new_crew_ids

    if update_rows is True:
        print('{} (id#{}): {} = {} (to attempt)'.format(discord_name, discord_id, column, crew_ids))
        update_data(db_file, discord_id, column, crew_ids)
    else:
        if column == 'current_crew':
            current_crew = crew_ids
            target_crew = []
        elif column == 'target_crew':
            current_crew = []
            target_crew = crew_ids
        insert_data(db_file, discord_id, discord_name, current_crew, target_crew)
        print('{} (id#{}): {} = {} (updated)'.format(discord_name, discord_id, column, crew_ids))
    return txt, crew_ids


def delete_crew(db_file, discord_id, column, crew_txt):
    rows = read_database(db_file, discord_id)
    row, old_crew_ids = extract_row_data(rows, column)
    if row is None:
        print('There are no crews to delete')
        return

    crew_ids_to_delete, txt = crewtxt_to_crewnames(crew_txt, prefix='Deleting ')

    crew_ids = []
    for old_crew_id in old_crew_ids:
        if old_crew_id in crew_ids_to_delete:
            crew_ids_to_delete.remove(old_crew_id)
            continue
        crew_ids += [old_crew_id]

    update_data(db_file, discord_id, column, crew_ids)
    return txt, crew_ids


def get_crew_id_list(filename, column, discord_id: str):
    # print('get_crew_id_list()')
    rows = read_database(filename, discord_id)
    row, crew_ids = extract_row_data(rows, column)
    # print('get_crew_ids(): crew_ids = {} (type = {})'.format(crew_ids, type(crew_ids)))
    assert isinstance(crew_ids, list)
    if row is None:
        return []
    return crew_ids


def crewids_to_name_list(crew_ids, sort=True):
    name_list = []
    for i, crew_id in enumerate(crew_ids):
        name_list += [tbl_i2n[crew_id]]
    if sort is True:
        name_list.sort()
    return name_list


def filter_crew_ids(crew_ids: list, table_rarity: str):
    if table_rarity == 'all':
        return crew_ids

    filtered_ids = []
    for crew_id in crew_ids:
        crew_name = tbl_i2n[crew_id]
        crew_rarity = rarity[crew_name]
        if crew_rarity == table_rarity:
            filtered_ids += [crew_id]
    return filtered_ids


def show_crewlist0(filename, discord_id, column, rarity_filter):
    crew_ids = get_crew_id_list(filename, column, discord_id)
    # print('crew_ids = {}'.format(crew_ids))
    filtered_ids = filter_crew_ids(crew_ids, rarity_filter)
    if len(filtered_ids) == 0:
        name_list = []
        txt = '(none)'
    else:
        name_list = crewids_to_name_list(filtered_ids)
        txt = ', '.join(name_list)
    return crew_ids, filtered_ids, name_list, txt


def show_crewlist(filename, discord_id, rarity_filter):
    # Current Crew
    crew_ids, filtered_ids, name_list, txt = show_crewlist0(
        filename, discord_id, 'current_crew', rarity_filter)
    if rarity_filter == 'all':
        crew_txt = '**Your Crew**\n'
    else:
        crew_txt = '**Your {} Crew**\n'.format(rarity_filter)
    crew_txt += txt
    print(crew_txt)

    # Target Crew
    if rarity_filter in next_target.keys():
        target_rarity = next_target[rarity_filter]

        _, target_ids, target_names, txt = show_crewlist0(
            filename, discord_id, 'target_crew', target_rarity)

        if len(target_ids) > 0:
            if rarity_filter == 'all':
                header = '\n\n**Target Crew**\n'
            else:
                header = '\n\n**Target {} Crew**\n'.format(target_rarity)
            crew_txt += header + txt

    return crew_ids, filtered_ids, name_list, crew_txt


def new_table(filename, discord_id, table_rarity, output_file):
    print('rarity = {}'.format(table_rarity))
    crew_ids, filtered_ids, name_list, txt = show_crewlist(
        filename, discord_id, table_rarity)
    print('filtered_ids = {}'.format(filtered_ids))

    if len(filtered_ids) == 0:
        print('show_table(): filtered_ids = {}'.format(filtered_ids))
        return None

    # For each filter_id, download prestige information
    prestige_df = request_prestige_data_multiple(filtered_ids)
    # prestige_df.to_csv('prestige_df.csv', index=False)
    tbl = prestige_df_to_table(prestige_df, filtered_ids, tbl_i2n)
    tbl.sort_index(axis=0, inplace=True)
    tbl.sort_index(axis=1, inplace=True)
    tbl.to_csv(output_file)

    if table_rarity in next_target.keys():
        target_rarity = next_target[table_rarity]

        crew_ids, filtered_ids, name_list, txt = show_crewlist0(
            filename, discord_id, 'target_crew', target_rarity)
        if len(name_list) == 0:
            return

        txt = '--**Achievable Prestige Targets**--'
        txt_list = []
        for crew_name in name_list:
            txt += '\n**{}**'.format(crew_name)
            recipes = find_target(tbl, table_rarity, crew_name)
            recipes = remove_duplicates(recipes)
            if len(recipes) > 0:
                recipe_txt = [ '{} + {}'.format(r[0], r[1])
                               for r in recipes ]
                recipe_txt.sort()
                txt_list += [txt] + recipe_txt
            else:
                txt_list += [txt + '\n(no prestige recipes found)' ]
            txt = ''
    txt_list = condense_txt_list(txt_list, MESSAGE_CHARACTER_LIMIT)
    return txt_list


def show_table(filename, discord_id, table_rarity):
    output_file = '{}_prestige.csv'.format(table_rarity.lower())
    txt_list = new_table(filename, discord_id, table_rarity, output_file)
    return txt_list, output_file


def load_table(table_rarity):
    csv_file = '{}_prestige.csv'.format(table_rarity.lower())
    df = pd.read_csv(csv_file)
    return df


def find_target(df, table_rarity, target_crew):
    table = df.where(df == target_crew).fillna(0)
    row_indices, col_indices = np.where(table)

    recipes = []
    for i, row_index in enumerate(row_indices):
        col_index = col_indices[i]
        recipe = [df.index[row_index], df.columns[col_index]]
        # print('{}: {}'.format(i, recipe))
        recipes += [recipe]
    return recipes


# ----- Stats Conversion ----------------------------------------------
specials_lookup = {
    'AddReload': 'Rush Command',
    'DamageToCurrentEnemy': 'Critical Strike',
    'DamageToRoom': 'Ultra Dismantle',
    'DamageToSameRoomCharacters': 'Poison Gas',
    'DeductReload': 'System Hack',
    'FireWalk': 'Fire Walk',
    'Freeze': 'Freeze',
    'HealRoomHp': 'Urgent Repair',
    'HealSameRoomCharacters': 'Healing Rain',
    'HealSelfHp': 'First Aid',
    'SetFire': 'Arson'}


equipment_lookup = {
    1: 'head',
    2: 'body',
    4: 'leg',
    8: 'weapon',
    16: 'accessory'}


gas_cost_normal = [0, 0, 17, 33, 65, 130, 325, 650, 1300, 3200, 6500, 9700, 13000, 19500, 26000, 35700, 43800, 52000, 61700, 71500, 84500, 104000, 117000, 130000, 156000, 175000, 201000, 227000, 253000, 279000, 312000, 351000, 383000, 422000, 468000, 507000, 552000, 604000, 650000, 715000]
gas_cost_legendary = [0, 130000, 162500, 195000, 227500, 260000, 292500, 325000, 357500, 390000, 422500, 455000, 487500, 520000, 552500, 585000, 617500, 650000, 682500, 715000, 747500, 780000, 812500, 845000, 877500, 910000, 942000, 975000, 1007500, 1040000, 1072500, 1105000, 1137500, 1170000, 1202500, 1235000, 1267500, 1300000, 1332500, 1365000]
xp_cost_normal = [0, 90, 270, 450, 630, 810, 1020, 1230, 1440, 1650, 1860, 2130, 2400, 2670, 2940, 3210, 3540, 3870, 4200, 4530, 4860, 5220, 5580, 5940, 6300, 6660, 7050, 7440, 7830, 8220, 8610, 9030, 9450, 9870, 10290, 10710, 11160, 11610, 12060, 12510]
xp_cost_legendary = [0, 0, 810, 1350, 1890, 2430, 3060, 3690, 4320, 4950, 5580, 6360, 7090, 7840, 8610, 9400, 10210, 11040, 11890, 12760, 13650, 14560, 15490, 16440, 17410, 18400, 19410, 20440, 21490, 24660, 23650, 24760, 25890, 27040, 28210, 29400, 30610, 31840, 33090, 34360]


def convert_eqpt_mask(eqpt_mask):
    eqpt_list = []
    for k in equipment_lookup.keys():
        if (eqpt_mask & k) != 0:
            eqpt_list = eqpt_list + [equipment_lookup[k]]
    if len(eqpt_list) == 0:
        return 'nil'
    else:
        return ', '.join(eqpt_list)


# ----- Stats API -----------------------------------------------------
def stats2dict(raw_text):
    d = {}
    root = xml.etree.ElementTree.fromstring(raw_text)
    for c in root:
        for cc in c:
            for ccc in cc:
                if ccc.tag != 'CharacterDesign':
                    continue
                char_name = ccc.attrib['CharacterDesignName']
                d[char_name] = ccc.attrib
    return d


def get_stats(char_name, embed=False):
    raw_text = load_char_sheet_raw()
    d = stats2dict(raw_text)
    if embed is True:
        return embed_stats(d, char_name)
    else:
        return print_stats(d, char_name)


def print_stats(d, char_input):
    char_name = parse_char_name(char_input, tbl_n2i)
    if char_name is None:
        return None

    stats = d[char_name]
    special = stats['SpecialAbilityType']
    if special in specials_lookup.keys():
        special = specials_lookup[special]
    eqpt_mask = convert_eqpt_mask(int(stats['EquipmentMask']))
    coll_id   = stats['CollectionDesignId']
    if coll_id in collections.keys():
        coll_name = collections[coll_id]['CollectionName']
    else:
        coll_name = 'None'

    txt = '**{}** ({})\n'.format(char_name, stats['Rarity'])
    txt += '{}\n'.format(stats['CharacterDesignDescription'])

    txt += 'Race: {}, Collection: {}, Gender: {}\n'.format(
        stats['RaceType'], coll_name, stats['GenderType'])
    txt += 'ability = {} ({})\n'.format(stats['SpecialAbilityFinalArgument'], special)
    txt += 'hp = {}\n'.format(stats['FinalHp'])
    txt += 'attack = {}\n'.format(stats['FinalAttack'])
    txt += 'repair = {}\n'.format(stats['FinalRepair'])
    txt += 'pilot = {}\n'.format(stats['FinalPilot'])
    txt += 'science = {}\n'.format(stats['FinalScience'])
    txt += 'weapon = {}\n'.format(stats['FinalWeapon'])
    txt += 'engine = {}\n'.format(stats['FinalEngine'])
    txt += 'walk/run speed = {}/{}\n'.format(stats['WalkingSpeed'], stats['RunSpeed'])
    txt += 'fire resist = {}\n'.format(stats['FireResistance'])
    txt += 'training capacity = {}\n'.format(stats['TrainingCapacity'])
    txt += 'equipment = {}'.format(eqpt_mask)
    return txt


# def embed_stats(d, char):
#     char_name = parse_char_name(char, rtbl)
#     if char_name is None:
#         return None
#
#     stats = d[char_name]
#     special = stats['SpecialAbilityType']
#     if special in specials_lookup.keys():
#         special = specials_lookup[special]
#     eqpt_mask = convert_eqpt_mask(int(stats['EquipmentMask']))
#
#     embed = discord.Embed(
#         title='**{}** ({})\n'.format(char_name, stats['Rarity']),
#         description=stats['CharacterDesignDescription'], color=0x00ff00)
#     embed.add_field(name="Race", value=stats['RaceType'], inline=False)
#     embed.add_field(name="Gender", value=stats['GenderType'], inline=False)
#     embed.add_field(name="hp", value=stats['FinalHp'], inline=False)
#     embed.add_field(name="attack", value=stats['FinalAttack'], inline=False)
#     embed.add_field(name="repair", value=stats['FinalRepair'], inline=False)
#     embed.add_field(name="ability", value=stats['SpecialAbilityFinalArgument'], inline=False)
#     embed.add_field(name="pilot", value=stats['FinalPilot'], inline=False)
#     embed.add_field(name="shield", value=stats['FinalShield'], inline=False)
#     embed.add_field(name="weapon", value=stats['FinalWeapon'], inline=False)
#     embed.add_field(name="engine", value=stats['FinalEngine'], inline=False)
#     embed.add_field(name="run speed", value=stats['RunSpeed'], inline=False)
#     embed.add_field(name="fire resist", value=stats['FireResistance'], inline=False)
#     embed.add_field(name="special", value=special, inline=False)
#     embed.add_field(name="equipment", value=eqpt_mask, inline=False)
#     return embed


# ----- Collections ---------------------------------------------------
def get_collections():
    url = base_url + 'CollectionService/ListAllCollectionDesigns'
    raw_text = load_data_from_url(RAW_COLLECTIONSFILE, url, refresh='auto')
    collections = xmltree_to_dict3(raw_text, 'CollectionDesignId')
    collection_names = create_reverse_lookup(collections, 'CollectionDesignId', 'CollectionName')
    return collections, collection_names


def get_characters_in_collection(collection_id):
    url = base_url + 'CharacterService/ListAllCharacterDesigns?languageKey=en'
    raw_text = load_data_from_url(RAW_CHARFILE, url, refresh='auto')
    tbl = xmltree_to_dict3(raw_text, 'CharacterDesignId')

    chars_in_collection = []
    for k in tbl.keys():
        c = tbl[k]
        if int(c['CollectionDesignId']) == int(collection_id):
            char_name = c['CharacterDesignName']
            chars_in_collection.append(char_name)
    return chars_in_collection


def show_collection(search_str):
    url = base_url + 'CollectionService/ListAllCollectionDesigns'
    raw_text = load_data_from_url(RAW_COLLECTIONSFILE, url, refresh='auto')
    collections = xmltree_to_dict3(raw_text, 'CollectionDesignId')
    collection_names = create_reverse_lookup(collections, 'CollectionDesignId', 'CollectionName') #id2names
    collection_ids = create_reverse_lookup(collections, 'CollectionName', 'CollectionDesignId') #names2id

    real_name = get_real_name(search_str, list(collection_ids.keys()))
    idx = collection_ids[real_name]
    chars_in_collection = get_characters_in_collection(idx)

    c = collections[idx]
    txt = ''
    txt += '**{}** ({})\n'.format(c['CollectionName'], c['CollectionType'])
    txt += '{}\n'.format(c['CollectionDescription'])
    txt += 'Combo Min/Max: {}...{}\n'.format(c['MinCombo'], c['MaxCombo'])
    txt += '{}: '.format(c['EnhancementType'])
    txt += '{} (Base), {} (Step)\n'.format(c['BaseEnhancementValue'], c['StepEnhancementValue'])
    txt += 'Characters: {}'.format(', '.join(chars_in_collection))
    return txt


# ----- List ----------------------------------------------------------
def get_char_list(action):
    if action in ['newchars', 'chars', 'newcrew', 'crew']:
        char_sheet_raw = load_char_sheet_raw(refresh=True)
        char_df = charsheet_to_df(char_sheet_raw)
        char_df = char_df.sort_values('CharacterDesignId', ascending=True)

    if action in ['newchars', 'newcrew']:
        cols = ['CharacterDesignId', 'CharacterDesignName']
        char_df['CharacterDesignId'] = char_df['CharacterDesignId'].astype(int)
        # new_chars = char_df.loc[char_df['CharacterDesignId'] > last_char, cols]
        new_chars = char_df.iloc[-15:,:][cols]

        txt = ''
        for i, row in enumerate(new_chars.iterrows()):
            data = row[1]
            txt += '{:3}: {}\n'.format(data['CharacterDesignId'], data['CharacterDesignName'])
        return [txt]

    elif action in ['chars', 'crew']:
        names = list(char_df['CharacterDesignName'].values)
        print('List of characters: ' + ', '.join(names))
        txt_list = list_to_text(names)
        return txt_list


def print_costs(initial_level, final_level, gas_cost, xp_cost):
    if xp_cost != 0:
        cost_txt = '{:,} xp'.format(xp_cost)
    else:
        cost_txt = 'zero xp'
    if gas_cost != 0:
        cost_txt += ' and {:,} gas'.format(gas_cost)
    return '\nGetting from levels {} to {} requires {}'.format(
            initial_level, final_level, cost_txt)


def print_crew_costs(level, gas_cost_array, xp_cost_array):
    gas_cost = gas_cost_array[level-1]
    total_gas_cost = sum(gas_cost_array[:level])
    xp_cost = xp_cost_array[level-1]
    total_xp_cost = sum(xp_cost_array[:level])
    txt  = print_costs(level-1, level, gas_cost, xp_cost)
    txt += print_costs(1, level, total_gas_cost, total_xp_cost)
    return txt


def get_level_cost(level):
    level = int(level)
    if level < 2 or level > 40:
        return 'Please enter a level between 2 and 40'

    txt = '**Level costs** (non-legendary crew, max research)'
    txt += print_crew_costs(level, gas_cost_normal, xp_cost_normal)
    txt += '\n\n**Level costs** (legendary crew, max research)'
    txt += print_crew_costs(level, gas_cost_legendary, xp_cost_legendary)
    return txt


# ----- Setup ---------------------------------------------------------
ctbl, tbl_i2n, tbl_n2i, rarity = get_char_sheet()
collections, collection_names = get_collections()
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
DISCORD_BOT_OWNER = os.getenv("DISCORD_BOT_OWNER")
DISCORD_BOT_OWNER_ID = os.getenv("DISCORD_BOT_OWNER_ID")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=
        'Pixel Starships Prestige & Character Sheet API')
    parser.add_argument('prestige',
        choices=['to', 'from', 'stats', 'refresh', 'collection',
                 'list', 'gas', 'init', 'showcrew', 'addcrew', 'addtarget',
                 'deletecrew', 'deletetarget', 'table'],
        help='Prestige direction (to/from character)')
    parser.add_argument('character', help='Character to prestige')
    parser.add_argument('--raw', action='store_true',
        help='Raw output (for to/from option only)')
    args = parser.parse_args()

    if args.prestige == 'refresh':
        ctbl, tbl_i2n, tbl_n2i, rarity = get_char_sheet()
    elif args.prestige == 'stats':
        # python3 pss_prestige.py stats "Ron"
        result = get_stats(args.character, embed=False)
        print(result)
        # print_stats(rtbl, args.character)
    elif args.prestige == 'collection':
        txt = show_collection(args.character)
        print(txt)
    elif args.prestige == 'list':
        # python3 pss_prestige.py list chars
        # python3 pss_prestige.py list newchars
        txt_list = get_char_list(action=args.character)
        for txt in txt_list:
            print(txt)
    elif args.prestige == 'gas':
        level = args.character
        txt = get_level_cost(level)
        print(txt)
    elif args.prestige == 'addcrew':
        # python3 pss_prestige.py addcrew "MaleN, Verun"
        txt, crew_list = add_crew(
            DB_FILE, DISCORD_BOT_OWNER_ID, DISCORD_BOT_OWNER,
            'current_crew', args.character)
        print(txt)
    elif args.prestige == 'addtarget':
        # python3 pss_prestige.py addtarget "Xin, Lollita"
        # python3 pss_prestige.py addtarget "King Dong"
        txt, crew_list = add_crew(
            DB_FILE, DISCORD_BOT_OWNER_ID, DISCORD_BOT_OWNER,
            'target_crew', args.character)
        print(txt)
    elif args.prestige == 'deletecrew':
        # python3 pss_prestige.py deletecrew "Sie"
        txt, crew_list = delete_crew(
            DB_FILE, DISCORD_BOT_OWNER_ID,
            'current_crew', args.character)
        print(txt)
    elif args.prestige == 'deletetarget':
        # python3 pss_prestige.py deletetarget "Sie"
        txt, crew_list = delete_crew(
            DB_FILE, DISCORD_BOT_OWNER_ID,
            'target_crew', args.character)
        print(txt)
    elif args.prestige == 'init':
        # python3 pss_prestige.py init db
        init_database(DB_FILE)
    elif args.prestige == 'showcrew':
        # python3 pss_prestige.py showcrew all
        crew_ids, filtered_ids, name_list, txt = show_crewlist(
            DB_FILE, DISCORD_BOT_OWNER_ID, args.character)
        print(txt)
    elif args.prestige == 'table':
        # python3 pss_prestige.py table Unique
        # python3 pss_prestige.py table Epic
        table_rarity = args.character
        txt_list, output_file = show_table(DB_FILE, DISCORD_BOT_OWNER_ID, table_rarity)
        for txt in txt_list:
            print(txt)
    else:
        # python3 pss_prestige.py from "Admiral"
        # python3 pss_prestige.py from "Stove Tops"
        # python3 pss_prestige.py to 'Alien Queen'
        # python3 pss_prestige.py --raw to 'Alien Queen'
        # python3 pss_prestige.py --raw to 'Xin'
        prestige_txt, success = get_prestige(
            args.character, args.prestige, tbl_i2n, tbl_n2i, args.raw)
        if success is True:
            for txt in prestige_txt:
                print(txt)
        else:
            for txt in prestige_txt:
                print(txt)
