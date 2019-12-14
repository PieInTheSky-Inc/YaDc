#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
from datetime import datetime
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
import settings
import utility as util


DB_CONN: psycopg2.extensions.connection = None


# ---------- Constants ----------

LATEST_SETTINGS_BASE_URL = 'https://api.pixelstarships.com/SettingService/GetLatestVersion3?deviceType=DeviceTypeAndroid&languageKey='


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
    time_diff = utc_now - datetime.fromtimestamp(modify_date)
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
                        if len(txt) > settings.MAXIMUM_CHARACTERS:
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
def list_to_text(lst, max_chars=settings.MAXIMUM_CHARACTERS):
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


# ---------- Get Production Server ----------

def get_latest_settings(language_key: str = 'en') -> dict:
    if not language_key:
        language_key = 'en'
    url = f'{LATEST_SETTINGS_BASE_URL}{language_key}'
    raw_text = get_data_from_url(url)
    result = xmltree_to_dict3(raw_text)
    return result


def get_production_server(language_key: str = 'en'):
    latest_settings = get_latest_settings(language_key=language_key)
    return latest_settings['ProductionServer']


def get_base_url():
    production_server = get_production_server()
    result = f'https://{production_server}/'
    return result


# ----- Links -----
def read_links_file():
    result = []
    links = {}
    for pss_links_file in settings.PSS_LINKS_FILES:
        try:
            with open(pss_links_file) as f:
                links = json.load(f)
            break
        except:
            pass
    for category, hyperlinks in links.items():
        result.append(settings.EMPTY_LINE)
        result.append(f'**{category}**')
        for (description, hyperlink) in hyperlinks:
            result.append(f'{description}: <{hyperlink}>')
    if len(result) > 1:
        result = result[1:]
    return result


def read_about_file():
    txt = ''
    for pss_about_file in settings.PSS_ABOUT_FILES:
        try:
            with open(pss_about_file) as f:
                txt = f.read()
            break
        except:
            pass
    return txt


# ---------- DataBase ----------
def init_db():
    success_settings = db_try_create_table('settings', [
        ('settingname', 'TEXT', True, True),
        ('modifydate', 'TIMESTAMPTZ', False, True),
        ('settingboolean', 'BOOLEAN', False, False),
        ('settingfloat', 'FLOAT', False, False),
        ('settingint', 'INT', False, False),
        ('settingtext', 'TEXT', False, False),
        ('settingtimestamp', 'TIMESTAMPTZ', False, False)
    ])
    if not success_settings:
        print('[init_db] DB initialization failed upon creating the table \'settings\'.')
        return

    success_update_1_2_2_0 = db_update_schema_v_1_2_2_0()
    if not success_update_1_2_2_0:
        print('[init_db] DB initialization failed upon upgrading the DB schema to version 1.2.2.0.')
        return

    success_update_1_2_4_0 = db_update_schema_v_1_2_4_0()
    if not success_update_1_2_4_0:
        print('[init_db] DB initialization failed upon upgrading the DB schema to version 1.2.4.0.')
        return

    success_serversettings = db_try_create_table('serversettings', [
        ('guildid', 'TEXT', True, True),
        ('dailychannelid', 'TEXT', False, False),
        ('dailycanpost', 'BOOLEAN', False, False),
        ('dailylatestmessageid', 'TEXT', False, False),
        ('usepagination', 'BOOLEAN', False, False),
        ('prefix', 'TEXT', False, False)
    ])
    if not success_serversettings:
        print('[init_db] DB initialization failed upon creating the table \'serversettings\'.')
        return

    print('[init_db] DB initialization succeeded')



def db_update_schema_v_1_2_4_0():
    column_definitions = [
        ('dailydeleteonchange', 'BOOLEAN', False, False, util.db_convert_boolean(False))
    ]

    schema_version = db_get_schema_version()
    if schema_version:
        compare_1240 = util.compare_versions(schema_version, '1.2.4.0')
        compare_1220 = util.compare_versions(schema_version, '1.2.2.0')
        if compare_1240 <= 0:
            return True
        elif compare_1220 > 0:
            return False

    query_lines = []
    for (column_name, column_type, column_is_primary, column_not_null, column_default) in column_definitions:
        column_definition = util.db_get_column_definition(column_name, column_type, is_primary=column_is_primary, not_null=column_not_null, default=column_default)
        query_lines.append(f'ALTER TABLE serversettings ADD COLUMN IF NOT EXISTS {column_definition}')

    query = '\n'.join(query_lines)
    success = db_try_execute(query)
    if success:
        success = db_try_set_schema_version('1.2.4.0')
    return success


def db_update_schema_v_1_2_2_0():
    query_lines = []
    rename_columns = {
        'channelid': 'dailychannelid',
        'canpost': 'dailycanpost'
    }
    column_definitions = [
        ('guildid', 'TEXT', True, True),
        ('dailychannelid', 'TEXT', False, False),
        ('dailycanpost', 'BOOLEAN', False, False),
        ('dailylatestmessageid', 'TEXT', False, False),
        ('usepagination', 'BOOLEAN', False, False),
        ('prefix', 'TEXT', False, False)
    ]

    schema_version = db_get_schema_version()
    if schema_version and util.compare_versions(schema_version, '1.2.2.0') <= 0:
        return True

    db_try_execute('ALTER TABLE IF EXISTS daily RENAME TO serversettings')

    column_names = db_get_column_names('serversettings')
    column_names = [column_name.lower() for column_name in column_names]
    for name_from, name_to in rename_columns.items():
        if name_from in column_names:
            query_lines.append(f'ALTER TABLE IF EXISTS serversettings RENAME COLUMN {name_from} TO {name_to};')

    for (column_name, column_type, column_is_primary, column_not_null) in column_definitions:
        if column_name in rename_columns.values() or column_name in column_names:
            query_lines.append(f'ALTER TABLE IF EXISTS serversettings ALTER COLUMN {column_name} TYPE {column_type};')
            if column_not_null:
                not_null_toggle = 'SET'
            else:
                not_null_toggle = 'DROP'
            query_lines.append(f'ALTER TABLE IF EXISTS serversettings ALTER COLUMN {column_name} {not_null_toggle} NOT NULL;')

    query = '\n'.join(query_lines)
    if query:
        success = db_try_execute(query)
    else:
        success = True
    if success:
        query_lines = []
        column_names = db_get_column_names('serversettings')
        column_names = [column_name.lower() for column_name in column_names]
        for (column_name, column_type, column_is_primary, column_not_null) in column_definitions:
            if column_name not in column_names:
                query_lines.append(f'ALTER TABLE IF EXISTS serversettings ADD COLUMN IF NOT EXISTS {util.db_get_column_definition(column_name, column_type, column_is_primary, column_not_null)};')
        query = '\n'.join(query_lines)
        if query:
            success = db_try_execute(query)
        else:
            success = True
        if success:
            success = db_try_set_schema_version('1.2.2.0')
    return success


def db_close_cursor(cursor: psycopg2.extensions.cursor) -> None:
    if cursor is not None:
        cursor.close()


def db_connect() -> bool:
    global DB_CONN
    if db_is_connected(DB_CONN) == False:
        try:
            DB_CONN = psycopg2.connect(settings.DATABASE_URL, sslmode='prefer')
            return True
        except Exception as error:
            error_name = error.__class__.__name__
            print(f'[db_connect] {error_name} occurred while establishing connection: {error}')
            return False
    else:
        return True


def db_disconnect() -> None:
    global DB_CONN
    if db_is_connected(DB_CONN):
        DB_CONN.close()


def db_execute(query: str, cursor: psycopg2.extensions.cursor) -> None:
    cursor.execute(query)


def db_fetchall(query: str) -> list:
    result = None
    connected = db_connect()
    if connected:
        cursor = db_get_cursor()
        if cursor is not None:
            try:
                cursor.execute(query)
                result = cursor.fetchall()
            except (Exception, psycopg2.DatabaseError) as error:
                error_name = error.__class__.__name__
                print(f'[db_fetchall] {error_name} while performing a query: {error}')
            finally:
                db_close_cursor(cursor)
                db_disconnect()
        else:
            print('[db_fetchall] could not get cursor')
            db_disconnect()
    else:
        print('[db_fetchall] could not connect to db')
    return result


def db_get_column_list(column_definitions: list) -> str:
    result = []
    for column_definition in column_definitions:
        result.append(util.db_get_column_definition(*column_definition))
    return ', '.join(result)


def db_get_column_names(table_name: str, cursor: psycopg2.extensions.cursor=None) -> list:
    created_cursor = False
    if cursor is None:
        cursor = db_get_cursor()
        created_cursor = True
    result = None
    query = f'SELECT * FROM {table_name} LIMIT 0'
    success = db_try_execute(query, cursor)
    if success:
        result = [desc.name for desc in cursor.description]
    if created_cursor:
        db_close_cursor(cursor)
        db_disconnect()
    return result


def db_get_cursor() -> psycopg2.extensions.cursor:
    global DB_CONN
    connected = db_is_connected(DB_CONN)
    if not connected:
        connected = db_connect()
    if connected:
        return DB_CONN.cursor()
    else:
        print('[db_get_cursor] db is not connected')
    return None


def db_get_schema_version() -> str:
    where_string = util.db_get_where_string('settingname', 'schema_version', is_text_type=True)
    query = f'SELECT * FROM settings WHERE {where_string}'
    try:
        results = db_fetchall(query)
    except:
        results = []
    if results:
        return results[0][5]
    else:
        return ''


def db_is_connected(connection: psycopg2.extensions.connection) -> bool:
    if connection:
        if connection.closed == 0:
            return True
    return False


def db_try_set_schema_version(version: str) -> bool:
    prior_version = db_get_schema_version()
    utc_now = util.get_utcnow()
    modify_date_for_db = util.db_convert_timestamp(utc_now)
    version_for_db = util.db_convert_text(version)
    if prior_version == '':
        query = f'INSERT INTO settings (settingname, modifydate, settingtext) VALUES (\'schema_version\', {modify_date_for_db}, {version_for_db})'
    else:
        where_string = util.db_get_where_string('settingname', 'schema_version', is_text_type=True)
        query = f'UPDATE settings SET settingtext = {version_for_db}, modifydate = {modify_date_for_db} WHERE {where_string}'
    success = db_try_execute(query)
    return success


def _db_try_rename_daily_table() -> bool:
    query_rename = 'ALTER TABLE IF EXISTS daily RENAME TO serversettings;'
    result = db_try_execute(query_rename)
    return result


def db_try_commit() -> bool:
    global DB_CONN
    if db_is_connected(DB_CONN):
        try:
            DB_CONN.commit()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            error_name = error.__class__.__name__
            print(f'[db_try_commit] {error_name} while committing: {error}')
            return False
    else:
        print('[db_try_commit] db is not connected')
        return False


def db_try_create_table(table_name: str, column_definitions: list) -> bool:
    column_list = db_get_column_list(column_definitions)
    query_create = f'CREATE TABLE {table_name} ({column_list});'
    success = False
    connected = db_connect()
    if connected:
        cursor = db_get_cursor()
        if cursor is not None:
            try:
                db_execute(query_create, cursor)
                success = db_try_commit()
            except db_error.lookup('42P07'):  # DuplicateTable
                db_try_rollback()
                success = True
            except (Exception, psycopg2.DatabaseError) as error:
                error_name = error.__class__.__name__
                print(f'[db_try_create_table] {error_name} while performing the query \'{query_create}\': {error}')

            db_close_cursor(cursor)
            db_disconnect()
        else:
            print('[db_try_create_table] could not get cursor')
            db_disconnect()
    else:
        print('[db_try_create_table] could not connect to db')
    return success


def db_try_execute(query: str, cursor: psycopg2.extensions.cursor = None) -> bool:
    if query and query[-1] != ';':
        query += ';'
    success = False
    connected = db_connect()
    if connected:
        if cursor is None:
            cursor = db_get_cursor()
        if cursor is not None:
            try:
                db_execute(query, cursor)
                db_try_commit()
                success = True
            except (Exception, psycopg2.DatabaseError) as error:
                db_try_rollback()
                error_name = error.__class__.__name__
                print(f'[db_try_execute] {error_name} while performing the query \'{query}\': {error}')
            finally:
                db_close_cursor(cursor)
                db_disconnect()
        else:
            print('[db_try_execute] could not get cursor')
            db_disconnect()
    else:
        print('[db_try_execute] could not connect to db')
    return success


def db_try_rollback() -> None:
    if db_is_connected(DB_CONN):
        try:
            DB_CONN.rollback()
            return True
        except (Exception, psycopg2.DatabaseError) as error:
            error_name = error.__class__.__name__
            print(f'[db_try_rollback] {error_name} while rolling back: {error}')
            return False
    else:
        print('[db_try_rollback] db is not connected')
        return False


def db_get_setting(setting_name: str) -> (object, datetime):
    where_string = util.db_get_where_string('settingname', setting_name, is_text_type=True)
    query = f'SELECT * FROM settings WHERE {where_string}'
    try:
        results = db_fetchall(query)
    except:
        results = []
    if results:
        result = results[0]
        modify_date = util.db_convert_to_datetime(result[1])
        if result[2]:
            return (util.db_convert_to_boolean(result[2]), modify_date)
        elif result[3]:
            return (util.db_convert_to_float(result[3]), modify_date)
        elif result[4]:
            return (util.db_convert_to_int(result[4]), modify_date)
        elif result[5]:
            return (str(result[5]), modify_date)
        elif result[6]:
            return (util.db_convert_to_datetime(result[6]), modify_date)
        else:
            return (None, modify_date)
    else:
        return (None, None)


def db_set_setting(setting_name: str, value: object) -> bool:
    column_name = None
    if isinstance(value, bool):
        db_value = util.db_convert_boolean(value)
        column_name = 'settingboolean'
    elif isinstance(value, int):
        db_value = util.db_convert_to_int(value)
        column_name = 'settingint'
    elif isinstance(value, float):
        db_value = util.db_convert_to_float(value)
        column_name = 'settingfloat'
    elif isinstance(value, datetime):
        db_value = util.db_convert_to_datetime(value)
        column_name = 'settingtimestamptz'
    else:
        db_value = util.db_convert_text(value)
        column_name = 'settingtext'

    setting = db_get_setting(setting_name)
    utc_now = util.get_utcnow()
    modify_date = util.db_convert_timestamp(utc_now)
    if setting is None:
        query = f'INSERT INTO settings (settingname, modifydate, {column_name}) VALUES ({util.db_convert_text(setting_name)}, {modify_date}, {db_value})'
    elif setting != value:
        where_string = util.db_get_where_string('settingname', setting_name, is_text_type=True)
        query = f'UPDATE settings SET {column_name} = {db_value}, modifydate = {modify_date} WHERE {where_string}'
    success = db_try_execute(query)
    return success
