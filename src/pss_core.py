#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import aiohttp
import asyncio
import asyncpg
from datetime import datetime
import discord
import json
import psycopg2
from psycopg2 import errors as db_error
import re
from typing import Callable, Dict, List, Tuple, Union
import xml.etree.ElementTree

import data
import pss_daily as daily
import pss_lookups as lookups
import settings
import utility as util


DB_CONN: asyncpg.Connection = None
DB_CONN_LOCK: asyncio.Lock = asyncio.Lock()


# ---------- Constants ----------










# ----- Utilities --------------------------------

async def get_data_from_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.text(encoding='utf-8')
    return data


async def get_data_from_path(path):
    if path:
        path = path.strip('/')
    base_url = await get_base_url()
    url = f'{base_url}{path}'
    return await get_data_from_url(url)


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
    result = _convert_xml_to_dict(root, include_root)
    return result


def _convert_xml_to_dict(root: xml.etree.ElementTree.Element, include_root: bool = True) -> dict:
    if root is None:
        return None

    result = {}
    if root.attrib:
        if include_root:
            result[root.tag] = _fix_attrib(root.attrib)
        else:
            result = _fix_attrib(root.attrib)
    elif include_root:
        result[root.tag] = {}

    # Retrieve all distinct names of sub tags
    tag_count = _get_child_tag_count(root)

    for child in root:
        tag = child.tag
        key = None
        if tag_count[tag] < 1:
            continue
        elif tag_count[tag] > 1:
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

        child_dict = _convert_xml_to_dict(child, False)
        if include_root:
            if key not in result[root.tag].keys():
                result[root.tag][key] = child_dict
        else:
            if key not in result.keys():
                result[key] = child_dict

    return result


def _get_child_tag_count(root: xml.etree.ElementTree.Element) -> dict:
    if root is None:
        return None

    child_tags = list(set([child_node.tag for child_node in root]))
    result = {}
    for child_tag in child_tags:
        result[child_tag] = sum(1 for child_node in root if child_node.tag == child_tag)

    return result


def _fix_attrib(attrib: dict) -> dict:
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


__rx_property_fix_replace = re.compile(r'[^a-z0-9]', re.IGNORECASE)
__rx_allowed_candidate_fix_replace = re.compile(r'(\(.*?\)|[^a-z0-9 ])', re.IGNORECASE)

def _fix_property_value(property_value: str) -> str:
    result = property_value.lower()
    result = result.strip()
    result = __rx_property_fix_replace.sub('', result)
    return result


def fix_allowed_value_candidate(candidate: str) -> str:
    result = candidate.strip()
    result = __rx_allowed_candidate_fix_replace.sub('', result)
    return result


def get_ids_from_property_value(data: dict, property_name: str, property_value: str, fix_data_delegate: Callable = None, match_exact: bool = False) -> list:
    # data structure: {id: content}
    # fixed_data structure: {description: id}
    if not data or not property_name or not property_value:
        print(f'- get_ids_from_property_value: invalid data or property info. Return empty list.')
        return []

    if not fix_data_delegate:
        fix_data_delegate = _fix_property_value

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
        if not match_exact or (match_exact is True and similarity_value.is_integer()):
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


def convert_iap_options_mask(iap_options_mask: int) -> str:
    result = []
    for flag in lookups.IAP_OPTIONS_MASK_LOOKUP.keys():
        if (iap_options_mask & flag) != 0:
            item, value = lookups.IAP_OPTIONS_MASK_LOOKUP[flag]
            result.append(f'_{item}_ ({value})')
    if result:
        if len(result) > 1:
            return f'{", ".join(result[:-1])} or {result[-1]}'
        else:
            return result[0]
    else:
        return ''










# ---------- Get Production Server ----------

async def get_latest_settings(language_key: str = 'en', use_base_production_server: bool = False) -> dict:
    if not language_key:
        language_key = 'en'
    if use_base_production_server:
        base_url = f'{settings.LATEST_SETTINGS_BASE_URL}{settings.LATEST_SETTINGS_BASE_PATH}'
    else:
        base_url = f'{await get_base_url()}{settings.LATEST_SETTINGS_BASE_PATH}'
    url = f'{base_url}{language_key}'
    raw_text = await get_data_from_url(url)
    result = xmltree_to_dict3(raw_text)
    return result


async def get_production_server(language_key: str = 'en'):
    latest_settings = await get_latest_settings(language_key=language_key, use_base_production_server=True)
    return latest_settings['ProductionServer']


async def get_base_url():
    production_server = await get_production_server()
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


def read_about_file() -> dict:
    result = {}
    for pss_about_file in settings.PSS_ABOUT_FILES:
        try:
            with open(pss_about_file) as f:
                result = json.load(f)
            break
        except:
            pass
    return result


def create_embed(title: str = None, description: str = None, fields: Union[List[Tuple[str, str]], Dict[str, str]] = None) -> discord.Embed:
    result = discord.Embed(title=title, description=description)
    if title is not None:
        result.title = title
    if description is not None:
        result.description = description
    if fields is not None:
        for name, value in fields:
            result.add_field(name=name, value=value)
    return result










# ---------- DataBase ----------

async def init_db():
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

    success_update_1_2_2_0 = await db_update_schema_v_1_2_2_0()
    if not success_update_1_2_2_0:
        print('[init_db] DB initialization failed upon upgrading the DB schema to version 1.2.2.0.')
        return

    success_update_1_2_4_0 = await db_update_schema_v_1_2_4_0()
    if not success_update_1_2_4_0:
        print('[init_db] DB initialization failed upon upgrading the DB schema to version 1.2.4.0.')
        return

    success_update_1_2_5_0 = await db_update_schema_v_1_2_5_0()
    if not success_update_1_2_5_0:
        print('[init_db] DB initialization failed upon upgrading the DB schema to version 1.2.5.0.')
        return

    success_update_1_2_6_0 = await db_update_schema_v_1_2_6_0()
    if not success_update_1_2_6_0:
        print('[init_db] DB initialization failed upon upgrading the DB schema to version 1.2.6.0.')
        return

    success_update_1_2_7_0 = await db_update_schema_v_1_2_7_0()
    if not success_update_1_2_7_0:
        print('[init_db] DB initialization failed upon upgrading the DB schema to version 1.2.7.0.')
        return

    success_serversettings = db_try_create_table('serversettings', [
        ('guildid', 'TEXT', True, True),
        ('dailychannelid', 'TEXT', False, False),
        ('dailycanpost', 'BOOLEAN', False, False),
        ('dailylatestmessageid', 'TEXT', False, False),
        ('usepagination', 'BOOLEAN', False, False),
        ('prefix', 'TEXT', False, False),
        ('dailydeleteonchange', 'BOOLEAN', False, False),
        ('dailynotifyid', 'TEXT', False, False),
        ('dailynotifytype', 'TEXT', False, False)
    ])
    if not success_serversettings:
        print('[init_db] DB initialization failed upon creating the table \'serversettings\'.')
        return

    print('[init_db] DB initialization succeeded')



async def db_update_schema_v_1_2_7_0():
    column_definitions_devices = [
        ('key', 'TEXT', True, True),
        ('checksum', 'TEXT', False, False),
        ('loginuntil', 'TIMESTAMPTZ', False, False)
    ]

    schema_version = await db_get_schema_version()
    if schema_version:
        compare_1270 = util.compare_versions(schema_version, '1.2.7.0')
        compare_1260 = util.compare_versions(schema_version, '1.2.6.0')
        if compare_1270 <= 0:
            return True
        elif compare_1260 > 0:
            return False

    success = await db_try_create_table('devices', column_definitions_devices)
    if success:
        success = await db_try_set_schema_version('1.2.7.0')
    return success


async def db_update_schema_v_1_2_6_0():
    column_definitions_serversettings = [
        ('dailylatestmessagecreatedate', 'TIMESTAMPTZ', False, False),
        ('dailylatestmessagemodifydate', 'TIMESTAMPTZ', False, False)
    ]

    schema_version = await db_get_schema_version()
    if schema_version:
        compare_1260 = util.compare_versions(schema_version, '1.2.6.0')
        compare_1250 = util.compare_versions(schema_version, '1.2.5.0')
        if compare_1260 <= 0:
            return True
        elif compare_1250 > 0:
            return False

    query_lines = []
    for (column_name, column_type, column_is_primary, column_not_null) in column_definitions_serversettings:
        column_definition = util.db_get_column_definition(column_name, column_type, is_primary=column_is_primary, not_null=column_not_null)
        query_lines.append(f'ALTER TABLE serversettings ADD COLUMN IF NOT EXISTS {column_definition};')

    query = '\n'.join(query_lines)
    success = await db_try_execute(query)
    if success:
        success = await db_try_set_schema_version('1.2.6.0')
    return success


async def db_update_schema_v_1_2_5_0():
    column_definitions = [
        ('dailynotifyid', 'TEXT', False, False),
        ('dailynotifytype', 'TEXT', False, False)
    ]

    schema_version = await db_get_schema_version()
    if schema_version:
        compare_1250 = util.compare_versions(schema_version, '1.2.5.0')
        compare_1240 = util.compare_versions(schema_version, '1.2.4.0')
        if compare_1250 <= 0:
            return True
        elif compare_1240 > 0:
            return False

    query_lines = []
    for (column_name, column_type, column_is_primary, column_not_null) in column_definitions:
        column_definition = util.db_get_column_definition(column_name, column_type, is_primary=column_is_primary, not_null=column_not_null)
        query_lines.append(f'ALTER TABLE serversettings ADD COLUMN IF NOT EXISTS {column_definition};')

    query = '\n'.join(query_lines)
    success = await db_try_execute(query)
    if success:
        success = await db_try_set_schema_version('1.2.5.0')
    return success


async def db_update_schema_v_1_2_4_0():
    column_definitions = [
        ('dailydeleteonchange', 'BOOLEAN', False, False, None)
    ]

    schema_version = await db_get_schema_version()
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
    success = await db_try_execute(query)
    if success:
        utc_now = util.get_utcnow()
        daily_info = await daily.get_daily_info()
        success = await daily.db_set_daily_info(daily_info, utc_now)
        if success:
            success = await db_try_set_schema_version('1.2.4.0')
    return success


async def db_update_schema_v_1_2_2_0():
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

    schema_version = await db_get_schema_version()
    if schema_version and util.compare_versions(schema_version, '1.2.2.0') <= 0:
        return True

    db_try_execute('ALTER TABLE IF EXISTS daily RENAME TO serversettings')

    column_names = await db_get_column_names('serversettings')
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
        success = await db_try_execute(query)
    else:
        success = True
    if success:
        query_lines = []
        column_names = await db_get_column_names('serversettings')
        column_names = [column_name.lower() for column_name in column_names]
        for (column_name, column_type, column_is_primary, column_not_null) in column_definitions:
            if column_name not in column_names:
                query_lines.append(f'ALTER TABLE IF EXISTS serversettings ADD COLUMN IF NOT EXISTS {util.db_get_column_definition(column_name, column_type, column_is_primary, column_not_null)};')
        query = '\n'.join(query_lines)
        if query:
            success = await db_try_execute(query)
        else:
            success = True
        if success:
            success = await db_try_set_schema_version('1.2.2.0')
    return success










async def db_connect() -> bool:
    global DB_CONN
    if db_is_connected(DB_CONN) is False:
        try:
            async with DB_CONN_LOCK:
                DB_CONN = await asyncpg.connect(dsn=settings.DATABASE_URL)
                return True
        except Exception as error:
            error_name = error.__class__.__name__
            print(f'[db_connect] {error_name} occurred while establishing connection: {error}')
            return False
    else:
        return True


async def db_disconnect() -> None:
    global DB_CONN
    if db_is_connected(DB_CONN):
        async with DB_CONN_LOCK:
            await DB_CONN.close()


async def db_execute(query: str) -> bool:
    async with DB_CONN_LOCK:
        try:
            DB_CONN.execute(query)
            return True
        except:
            return False


async def db_fetchall(query: str) -> list:
    result = None
    if await db_connect():
        try:
            async with DB_CONN_LOCK:
                result = await DB_CONN.fetch(query)
        except Exception as error:
            error_name = error.__class__.__name__
            print(f'[db_fetchall] {error_name} while performing a query: {error}')
    else:
        print('[db_fetchall] could not connect to db')
    return result


def db_get_column_list(column_definitions: list) -> str:
    result = []
    for column_definition in column_definitions:
        result.append(util.db_get_column_definition(*column_definition))
    return ', '.join(result)


async def db_get_column_names(table_name: str) -> List[str]:
    result = None
    query = f'SELECT column_name FROM information_schema.columns WHERE table_name = {util.db_convert_text(table_name)}'
    if await db_connect():
        try:
            result = await db_fetchall(query)
        except Exception as error:
            error_name = error.__class__.__name__
            print(f'[db_fetchall] {error_name} while performing a query: {error}')
    else:
        print('[db_fetchall] could not connect to db')
    if result:
        result = [record[0] for record in result]
    return result


async def db_get_schema_version() -> str:
    where_string = util.db_get_where_string('settingname', 'schema_version', is_text_type=True)
    query = f'SELECT * FROM settings WHERE {where_string}'
    try:
        results = await db_fetchall(query)
    except:
        results = []
    if results:
        return results[0][5]
    else:
        return ''


def db_is_connected(connection: asyncpg.Connection) -> bool:
    if connection:
        return not connection.is_closed()
    return False


async def db_try_set_schema_version(version: str) -> bool:
    prior_version = await db_get_schema_version()
    utc_now = util.get_utcnow()
    modify_date_for_db = util.db_convert_timestamp(utc_now)
    version_for_db = util.db_convert_text(version)
    if prior_version == '':
        query = f'INSERT INTO settings (settingname, modifydate, settingtext) VALUES (\'schema_version\', {modify_date_for_db}, {version_for_db})'
    else:
        where_string = util.db_get_where_string('settingname', 'schema_version', is_text_type=True)
        query = f'UPDATE settings SET settingtext = {version_for_db}, modifydate = {modify_date_for_db} WHERE {where_string}'
    success = await db_try_execute(query)
    return success


async def _db_try_rename_daily_table() -> bool:
    query_rename = 'ALTER TABLE IF EXISTS daily RENAME TO serversettings;'
    result = await db_try_execute(query_rename)
    return result


async def db_try_commit() -> bool:
    global DB_CONN
    if db_is_connected(DB_CONN):
        try:
            async with DB_CONN_LOCK:
                await DB_CONN.commit()
                return True
        except (Exception, psycopg2.DatabaseError) as error:
            error_name = error.__class__.__name__
            print(f'[db_try_commit] {error_name} while committing: {error}')
            return False
    else:
        print('[db_try_commit] db is not connected')
        return False


async def db_try_create_table(table_name: str, column_definitions: list) -> bool:
    column_list = db_get_column_list(column_definitions)
    query_create = f'CREATE TABLE {table_name} ({column_list});'
    success = False
    if await db_connect():
        try:
            success = await db_execute(query_create)
        except asyncpg.exceptions.DuplicateTableError:
            success = True
        except (Exception) as error:
            error_name = error.__class__.__name__
            print(f'[db_try_create_table] {error_name} while performing the query \'{query_create}\': {error}')
    else:
        print('[db_try_create_table] could not connect to db')
    return success


async def db_try_execute(query: str) -> bool:
    if query and query[-1] != ';':
        query += ';'
    success = False
    if await db_connect():
        try:
            success = await db_execute(query)
        except (Exception, psycopg2.DatabaseError) as error:
            error_name = error.__class__.__name__
            print(f'[db_try_execute] {error_name} while performing the query \'{query}\': {error}')
    else:
        print('[db_try_execute] could not connect to db')
    return success


async def db_get_setting(setting_name: str) -> (object, datetime):
    modify_date: datetime = None
    where_string = util.db_get_where_string('settingname', setting_name, is_text_type=True)
    query = f'SELECT * FROM settings WHERE {where_string}'
    try:
        records = await db_fetchall(query)
    except:
        records = []
    if records:
        result = records[0]
        modify_date = result[1]
        for field in result[2:]:
            if field:
                return (field, modify_date)
        return (None, modify_date)
    else:
        return (None, modify_date)


async def db_set_setting(setting_name: str, value: object, utc_now: datetime = None) -> bool:
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

    setting, modify_date = db_get_setting(setting_name)
    if utc_now is None:
        utc_now = util.get_utcnow()
    modify_date = util.db_convert_timestamp(utc_now)
    query = ''
    if setting is None and modify_date is None:
        query = f'INSERT INTO settings (settingname, modifydate, {column_name}) VALUES ({util.db_convert_text(setting_name)}, {modify_date}, {db_value})'
    elif setting != value:
        where_string = util.db_get_where_string('settingname', setting_name, is_text_type=True)
        query = f'UPDATE settings SET {column_name} = {db_value}, modifydate = {modify_date} WHERE {where_string}'
    success = not query or await db_try_execute(query)
    return success










# ---------- Initialization ----------

async def init():
    await db_connect()