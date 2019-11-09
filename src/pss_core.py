#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
import datetime
import json
import os
import psycopg2
from psycopg2 import errors as db_error
import re
import sys
from typing import Callable
import urllib.parse
import urllib.request
import xml.etree.ElementTree

import data
import utility as util


DATABASE_URL = os.environ['DATABASE_URL']
PSS_LINKS_FILES = ['src/data/links.json', 'data/links.json']
PSS_ABOUT_FILES = ['src/data/about.txt', 'data/about.txt']
MAXIMUM_CHARACTERS = 1900
DB_CONN = None
EMPTY_LINE = '\u200b'

DATABASE_URL = os.environ['DATABASE_URL']
DB_CONN = None
SETTINGS_TABLE_NAME = 'settings'
SETTINGS_TYPES = ['boolean','float','int','text','timestamputc']


# ----- Utilities --------------------------------
def get_data_from_url(url):
    data = urllib.request.urlopen(url).read()
    return data.decode('utf-8')


def get_data_from_path(path):
    if path:
        path = path.strip('/')
    base_url = get_base_url()
    url = f'{base_url}{path}'
    return get_data_from_url(url)



def save_raw_text(raw_text, filename):
    try:
        with open(filename, 'w') as f:
            f.write(raw_text)
    except:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(raw_text)


def read_raw_text(filename):
    try:
        with open(filename, 'r') as f:
            result = f.read()
            return result
    except:
        with open(filename, 'r', encoding='utf-8') as f:
            result = f.read()
            return result


def save_json_to_file(obj, filename):
    try:
        with open(filename, 'w') as f:
            json.dump(obj, f)
    except:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(obj, f)


def read_json_from_file(filename):
    result = None
    try:
        with open(filename, 'r') as f:
            result = json.load(f)
    except:
        with open(filename, 'r', encoding='utf-8') as f:
            result = json.load(f)
    return result


def is_old_file(filename, max_days=0, max_seconds=3600, verbose=True):
    """Returns true if the file modification date > max_days / max_seconds ago
    or if the file does not exist"""
    if not os.path.isfile(filename):
        return True
    file_stats = os.stat(filename)
    modify_date = file_stats.st_mtime
    utc_now = util.get_utcnow()
    time_diff = utc_now - datetime.datetime.fromtimestamp(modify_date)
    if verbose:
        print('Time since file {} creation: {}'.format(filename, time_diff))
    return (time_diff.days > max_days) or time_diff.seconds > max_seconds


def load_data_from_url(filename, url, refresh='auto'):
    if os.path.isfile(filename) and refresh != 'true':
        if refresh == 'auto':
            if is_old_file(filename, max_seconds=3600, verbose=False):
                raw_text = get_data_from_url(url)
                save_raw_text(raw_text, filename)
                return raw_text
        with open(filename, 'r') as f:
            raw_text = f.read()
    else:
        raw_text = get_data_from_url(url)
        save_raw_text(raw_text, filename)
    return raw_text


def xmltree_to_dict3(raw_text):
    root = convert_raw_xml_to_dict(raw_text)
    for c in root.values():
        if isinstance(c, dict):
            for cc in c.values():
                if isinstance(cc, dict):
                    for ccc in cc.values():
                        if isinstance(ccc, dict):
                            return ccc
    return {}


def xmltree_to_dict2(raw_text):
    root = convert_raw_xml_to_dict(raw_text)
    for c in root.values():
        if isinstance(c, dict):
            for cc in c.values():
                if isinstance(cc, dict):
                    return cc
    return {}





def convert_raw_xml_to_dict(raw_xml: str, include_root: bool = True) -> dict:
    root = xml.etree.ElementTree.fromstring(raw_xml)
    # Create an empty dictionary
    result = convert_xml_to_dict(root, include_root)
    return result


def convert_xml_to_dict(root: xml.etree.ElementTree.Element, include_root: bool = True) -> dict:
    if root is None:
        return None

    result = {}
    if root.attrib:
        if include_root:
            result[root.tag] = fix_attrib(root.attrib)
        else:
            result = fix_attrib(root.attrib)
    elif include_root:
        result[root.tag] = {}

    # Retrieve all distinct names of sub tags
    tag_count = get_child_tag_count(root)

    for child in root:
        tag = child.tag
        key = None
        if tag_count[tag] < 1:
            continue
        elif tag_count[tag] >= 1:
            if tag in data.ID_NAMES_INFO.keys():
                id_attr_names = data.ID_NAMES_INFO[tag]
                if id_attr_names:
                    key = ''
                    id_attr_values = []
                    for id_attr_name in id_attr_names:
                        id_attr_values.append(child.attrib[id_attr_name])
                    id_attr_values = sorted(id_attr_values)
                    key = '.'.join(id_attr_values)

        if not key:
            key = tag

        child_dict = convert_xml_to_dict(child, False)
        if include_root:
            if key not in result[root.tag].keys():
                result[root.tag][key] = child_dict
        else:
            if key not in result.keys():
                result[key] = child_dict

    return result


def get_child_tag_count(root: xml.etree.ElementTree.Element) -> dict:
    if root is None:
        return None

    child_tags = list(set([child_node.tag for child_node in root]))
    result = {}
    for child_tag in child_tags:
        result[child_tag] = sum(1 for child_node in root if child_node.tag == child_tag)

    return result


def fix_attrib(attrib: dict) -> dict:
    if not attrib:
        return None

    result = {}

    for (key, value) in attrib.items():
        if key.endswith('Xml') and value:
            raw_xml = value
            #raw_xml = html.unescape(value)
            fixed_value = convert_raw_xml_to_dict(raw_xml)
            result[key[:-3]] = fixed_value

        result[key] = value

    return result


def convert_2_level_xml_to_dict(raw_text, key_name, tag):
    root = xml.etree.ElementTree.fromstring(raw_text)
    result = {}
    for c in root:
        for cc in c:
            if cc.tag != tag:
                continue
            key = cc.attrib[key_name]
            result[key] = cc.attrib
    return result


def create_reverse_lookup(d, new_key, new_value):
    """Creates a dictionary of the form:
    {'new_key': 'new_value'}"""
    rlookup = {}
    for key in d.keys():
        item = d[key]
        rlookup[item[new_key]] = item[new_value]
    return rlookup


def parse_links3(url):
    data = urllib.request.urlopen(url).read()
    root = xml.etree.ElementTree.fromstring(data.decode('utf-8'))

    txt_list = []
    txt = ''
    for c in root:
        if len(root) == 1:
            txt += f'{c.tag}'
        for cc in c:
            if len(c) == 1:
                txt += f'/{cc.tag}'
            for ccc in cc:
                if len(cc) == 1:
                    txt += f'/{ccc.tag}'
                if isinstance(ccc.attrib, dict):
                    for k,v in ccc.attrib.items():
                        txt += f'\n - {k}: {v}'
                        if len(txt) > MAXIMUM_CHARACTERS:
                            txt_list += [txt]
                            txt = ''
    return txt_list + [txt]


def parse_unicode(text, action):
    if text[0] == '"' and text[-1] == '"':
        text = text.strip('"')
    if text[0] == "'" and text[-1] == "'":
        text = text.strip("'")
    if text[0] == "“" and text[-1] == "“":
        text = text.strip("“")
    if action == 'quote':
        return urllib.parse.quote(text)
    elif action == 'unquote':
        return urllib.parse.unquote(text)


__rx_property_fix_replace = re.compile(r'[^a-z0-9]', re.IGNORECASE)
__rx_allowed_candidate_fix_replace = re.compile(r'(\(.*?\)|[^a-z0-9 ])', re.IGNORECASE)

def fix_property_value(property_value: str) -> str:
    result = property_value.lower()
    result = result.strip()
    result = __rx_property_fix_replace.sub('', result)
    return result


def fix_allowed_value_candidate(candidate: str) -> str:
    result = candidate.strip()
    result = __rx_allowed_candidate_fix_replace.sub('', result)
    return result



def get_ids_from_property_value(data: dict, property_name: str, property_value: str, fix_data_delegate: Callable = None) -> list:
    # data structure: {id: content}
    # fixed_data structure: {description: id}
    if not data or not property_name or not property_value:
        print(f'- get_ids_from_property_value: invalid data or property info. Return empty list.')
        return []

    if not fix_data_delegate:
        fix_data_delegate = fix_property_value

    fixed_value = fix_data_delegate(property_value)
    fixed_data = {entry_id: fix_data_delegate(entry_data[property_name]) for entry_id, entry_data in data.items() if entry_data[property_name]}

    similarity_map = {}
    for entry_id, entry_property in fixed_data.items():
        if entry_property.startswith(fixed_value) or fixed_value in entry_property:
            similarity_value = util.get_similarity(entry_property, fixed_value)
            if similarity_value in similarity_map.keys():
                similarity_map[similarity_value].append((entry_id, entry_property))
            else:
                similarity_map[similarity_value] = [(entry_id, entry_property)]
    for similarity_value, entries in similarity_map.items():
        similarity_map[similarity_value] = sorted(entries, key=lambda entry: entry[1])
    similarity_values = sorted(list(similarity_map.keys()), reverse=True)
    results = []
    for similarity_value in similarity_values:
        entry_ids = [entry_id for (entry_id, _) in similarity_map[similarity_value]]
        results.extend(entry_ids)

    return results


def filter_data_list(data: list, by: dict, ignore_case: bool = False):
    """Parameter 'data':
       - A list of entity dicts
       Parameter 'by':
       - Keys are names of entity fields to filter by.
       - Values are values that each respective field should have."""
    result = data
    if by:
        for key, value in by.items():
            result = _filter_data_list(result, key, value, ignore_case)
    return result


def _filter_data_list(data: list, by_key, by_value, ignore_case: bool):
    """Parameter 'data':
       - A list of entity dicts """
    if data:
        result = []
        for entry in data:
            entry_value = entry[by_key]
            value = by_value
            if ignore_case:
                entry_value = str(entry_value).lower()
                value = str(value).lower()
            if isinstance(by_value, list):
                if entry_value in value:
                    result.append(entry)
            elif entry_value == value:
                    result.append(entry)
        return result
    else:
        return data


def filter_data_dict(data: dict, by: dict, ignore_case: bool = False):
    """Parameter 'data':
       - A dict with entity ids as keys and entity info as values.
       Parameter 'by':
       - Keys are names of entity fields to filter by.
       - Values are values that each respective field should have. """
    result = data
    if by:
        for key, value in by.items():
            result = _filter_data_dict(result, key, value, ignore_case)
    return result


def _filter_data_dict(data: dict, by_key, by_value, ignore_case: bool):
    """Parameter 'data':
       - A dict with entity ids as keys and entity info as values. """
    if data:
        result = {}
        for key, entry in data.items():
            entry_value = entry[by_key]
            value = by_value
            if ignore_case:
                entry_value = str(entry_value).lower()
                value = str(value).lower()
            if isinstance(by_value, list):
                if entry_value in value:
                    result[key] = entry
            elif entry_value == value:
                    result[key] = entry
        return result
    else:
        return data


def group_data_list(data: list, by_key, ignore_case: bool = False):
    """Parameter 'data':
       - A dict with entity ids as keys and entity info as values. """
    if data:
        result = {}
        for entry in data:
            entry_value = entry[by_key]
            if ignore_case:
                entry_value = str(entry_value).lower()
            if entry_value in result.keys():
                result[entry_value].append(entry)
            else:
                result[entry_value] = [entry]
        return result
    else:
        return data


def group_data_dict(data: dict, by_key, ignore_case: bool = False):
    """Parameter 'data':
       - A dict with entity ids as keys and entity info as values. """
    if data:
        result = {}
        for key, entry in data.items():
            entry_value = entry[by_key]
            if ignore_case:
                entry_value = str(entry_value).lower()
            if entry_value in result.keys():
                result[entry_value][key] = entry
            else:
                new_group = {key: entry}
                result[entry_value] = new_group
        return result
    else:
        return data


# ----- Display -----
def list_to_text(lst, max_chars=MAXIMUM_CHARACTERS):
    txt_list = []
    txt = ''
    for i, item in enumerate(lst):
        if i == 0:
            txt = item
        else:
            new_text = txt + ', ' + item
            if len(new_text) > max_chars:
                txt_list += [txt]
                txt = item
            else:
                txt += ', ' + item
    txt_list += [txt]
    return txt_list


# ----- Search -----
def fix_search_text(search_text):
    # Convert to lower case & non alpha-numeric
    new_txt = re.sub('[^a-z0-9]', '', search_text.lower())
    return new_txt


def get_real_name(search_str, lst_original):
    lst_lookup = [ fix_search_text(s) for s in lst_original ]
    txt_fixed = fix_search_text(search_str)
    try:
        idx = lst_lookup.index(txt_fixed)
        return lst_original[idx]
    except:
        m = [re.search(txt_fixed, t) is not None for t in lst_lookup]
        if sum(m) > 0:
            return [txt for (txt, found) in zip(lst_original, m) if found][0]
        else:
            return None


# ----- Get Production Server -----
def get_production_server():
    url = 'https://api.pixelstarships.com/SettingService/GetLatestVersion3?languageKey=en&deviceType=DeviceTypeAndroid'
    raw_text = get_data_from_url(url)
    d = xmltree_to_dict3(raw_text)
    return d['ProductionServer']


def get_base_url():
    production_server = get_production_server()
    result = f'https://{production_server}/'
    return result


# ----- Links -----
def read_links_file():
    result = []
    links = {}
    for pss_links_file in PSS_LINKS_FILES:
        try:
            with open(pss_links_file) as f:
                links = json.load(f)
            break
        except:
            pass
    for category, hyperlinks in links.items():
        result.append(EMPTY_LINE)
        result.append(f'**{category}**')
        for (description, hyperlink) in hyperlinks:
            result.append(f'{description}: <{hyperlink}>')
    if len(result) > 1:
        result = result[1:]
    return result


def read_about_file():
    txt = ''
    for pss_about_file in PSS_ABOUT_FILES:
        try:
            with open(pss_about_file) as f:
                txt = f.read()
            break
        except:
            pass
    return txt


# ---------- DataBase ----------
def init_db():
    success = db_try_create_table('DAILY', ['GUILDID TEXT PRIMARY KEY NOT NULL', 'CHANNELID TEXT NOT NULL', 'CANPOST BOOLEAN'])
    if success:
        print('[init_db] db initialization succeeded')
    else:
        print('[init_db] db initialization failed')


def db_close_cursor(cursor):
    if cursor != None:
        cursor.close()


def db_connect():
    global DB_CONN
    if db_is_connected(DB_CONN) == False:
        try:
            DB_CONN = psycopg2.connect(DATABASE_URL, sslmode='prefer')
            return True
        except Exception as error:
            error_name = error.__class__.__name__
            print('[db_connect] {} occurred while establishing connection: {}'.format(error_name, error))
            return False
    else:
        return True


def db_disconnect():
    global DB_CONN
    if db_is_connected(DB_CONN):
        DB_CONN.close()


def db_execute(query, cursor):
    cursor.execute(query)
    success = db_try_commit()
    return success


def db_fetchall(query):
    result = None
    connected = db_connect()
    if connected:
        cursor = db_get_cursor()
        if cursor != None:
            try:
                cursor.execute(query)
                result = cursor.fetchall()
            except (Exception, psycopg2.DatabaseError) as error:
                error_name = error.__class__.__name__
                print('[db_fetchall] {} while performing a query: {}'.format(error_name, error))
            finally:
                db_close_cursor(cursor)
                db_disconnect()
        else:
            print('[db_fetchall] could not get cursor')
            db_disconnect()
    else:
        print('[db_fetchall] could not connect to db')
    return result


def db_get_cursor():
    global DB_CONN
    if db_is_connected(DB_CONN) == False:
        db_connect()
    if db_is_connected(DB_CONN):
        return DB_CONN.cursor()
    else:
        print('[db_get_cursor] db is not connected')
    return None


def db_is_connected(connection):
    if connection:
        if connection.closed == 0:
            return True
    return False


def db_try_commit():
    global DB_CONN
    if db_is_connected(DB_CONN):
        try:
            DB_CONN.commit()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            error_name = error.__class__.__name__
            print('[db_try_commit] {} while committing: {}'.format(error_name, error))
            return False
    else:
        print('[db_try_commit] db is not connected')
        return False


def db_try_create_table(table_name, columns):
    column_list = ', '.join(columns)
    query = 'CREATE TABLE {} ({});'.format(table_name, column_list)
    success = False
    connected = db_connect()
    if connected:
        cursor = db_get_cursor()
        if cursor != None:
            try:
                db_execute(query, cursor)
                success = True
            except db_error.DuplicateTable:
                success = True
            except (Exception, psycopg2.DatabaseError) as error:
                error_name = error.__class__.__name__
                print('[db_try_create_table] {} while performing a query: {}'.format(error_name, error))
            finally:
                db_close_cursor(cursor)
                db_disconnect()
        else:
            print('[db_try_create_table] could not get cursor')
            db_disconnect()
    else:
        print('[db_try_create_table] could not connect to db')
    return success


def db_try_execute(query):
    success = False
    connected = db_connect()
    if connected:
        cursor = db_get_cursor()
        if cursor != None:
            try:
                db_execute(query, cursor)
                success = True
            except (Exception, psycopg2.DatabaseError) as error:
                error_name = error.__class__.__name__
                print('[db_try_execute] {} while performing a query: {}'.format(error_name, error))
            finally:
                db_close_cursor(cursor)
                db_disconnect()
        else:
            print('[db_try_execute] could not get cursor')
            db_disconnect()
    else:
        print('[db_try_execute] could not connect to db')
    return success
