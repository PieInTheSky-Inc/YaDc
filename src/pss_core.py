#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
import csv
import datetime
from enum import Enum
import json
import os
import psycopg2
from psycopg2 import errors as db_error
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree

import utility as util


PSS_CHARS_FILE = 'pss-chars.txt'
PSS_CHARS_RAW_FILE = 'pss-chars-raw.txt'
PSS_LINKS_FILE = 'src/data/links.csv'
PSS_ABOUT_FILE = 'src/data/about.txt'
MAXIMUM_CHARACTERS = 1900

DATABASE_URL = os.environ['DATABASE_URL']
DB_CONN = None
SETTINGS_TABLE_NAME = 'settings'
SETTINGS_TYPES = ['boolean','float','int','text','timestamputc']


# ----- Utilities --------------------------------
def get_data_from_url(url):
    data = urllib.request.urlopen(url).read()
    return data.decode('utf-8')


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
            json.dumps(obj, f)
    except:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dumps(obj, f)
        
        
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
    utc_now = util.get_utcnow(True)
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


def xmltree_to_dict3(raw_text, key):
    root = xml.etree.ElementTree.fromstring(raw_text)
    d = {}
    for c in root:
        for cc in c:
            for ccc in cc:
                d[ccc.attrib[key]] = ccc.attrib
    return d


def convert_3_level_xml_to_dict(raw_text, key_name, tag):
    root = xml.etree.ElementTree.fromstring(raw_text)
    result = {}
    for c in root:
        for cc in c:
            for ccc in cc:
                if ccc.tag != tag:
                    continue
                key = ccc.attrib[key_name]
                result[key] = ccc.attrib
    return result


def xmltree_to_dict2(raw_text, key=None):
    root = xml.etree.ElementTree.fromstring(raw_text)
    for c in root:
        d = {}
        for cc in c:
            if key is None:
                d = cc.attrib
            else:
                d[cc.attrib[key]] = cc.attrib
    return d


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
    url = 'http://api.pixelstarships.com/SettingService/GetLatestVersion2?languageKey=en'
    raw_text = get_data_from_url(url)
    d = xmltree_to_dict2(raw_text, key=None)
    return d['ProductionServer']


# ----- Character Sheets -----
def save_char_brief(d, filename=PSS_CHARS_FILE):
    with open(filename, 'w') as f:
        for key in d.keys():
            entry = d[key]
            f.write('{},{},{}\n'.format(
                key,
                d[key]['CharacterDesignName'],
                d[key]['Rarity']))


def load_char_brief(filename=PSS_CHARS_FILE):
    with open(filename, 'r') as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        tbl, rtbl, rarity = {}, {}, {}
        for row in readCSV:
            char_id, char_dn, rarity[char_dn] = row
            tbl[char_id] = char_dn
            rtbl[char_dn] = char_id
    return tbl, rtbl, rarity


def get_extra_tables(d):
    rtbl, rarity = {}, {}
    for key in d.keys():
        name = d[key]['CharacterDesignName']
        rtbl[name] = key
        rarity[name] = d[key]['Rarity']
    return rtbl, rarity


def load_char_brief_cache(url, filename=PSS_CHARS_FILE, raw_file=PSS_CHARS_RAW_FILE):
    if is_old_file(filename, max_seconds=3600, verbose=False):
        raw_text = load_data_from_url(raw_file, url, refresh='auto')
        tbl = xmltree_to_dict3(raw_text, 'CharacterDesignId')
        rtbl, rarity = get_extra_tables(tbl)
        save_char_sheet(tbl, filename)
    else:
        tbl, rtbl, rarity = load_char_brief(filename)
    return tbl, rtbl, rarity


# ----- Links -----
def read_links_file():
    with open(PSS_LINKS_FILE) as f:
        csv_file = csv.reader(f, delimiter=',')
        txt = '**Links**'
        for row in csv_file:
            title, url = row
            txt += '\n{}: <{}>'.format(title, url.strip())
    return txt


# ----- About -----
#def read_about_file():
#    with open(PSS_ABOUT_FILE) as f:
#        csv_file = csv.reader(f, delimiter=',')
#        txt = '**About**'
#        for row in csv_file:
#            title, url = row
#            txt += '\n{}: <{}>'.format(title, url.strip())
#    return txt


class SettingType(Enum):
    Boolean = 1
    Float = 2
    Integer = 3
    Text = 4
    Timestamp = 5
    
    def __new__(cls, value):
        member = object.__new__(cls)
        member._value_ = value
        return member

    def __int__(self):
        return self.value


def get_setting(setting_name, setting_type):
    setting_name = util.db_convert_text(setting_name)
    column_name = ''
    where = util.db_get_where_string('settingname', setting_name, True)
    column_number = int(setting_type) + 1
        
    result = db_select_first_from_where(SETTINGS_TABLE_NAME, where)
    if result is None:
        return None
    else:
        result = result[column_number]
        if setting_type == SettingType.Boolean:
            result = util.db_convert_to_boolean(result)
        elif is_float == SettingType.Float:
            result = util.db_convert_to_float(result)
        elif is_int == SettingType.Integer:
            result = util.db_convert_to_int(result)
        elif is_text == SettingType.Text:
            result = result
        elif is_timestamp_utc == SettingType.Timestamp:
            result = util.db_convert_to_datetime(result)
        return result
    
    
def try_store_setting(setting_name, value, setting_type):
    success = False
    error = None
    existing_setting_value = get_setting(setting_name, setting_type)
    setting_name = util.db_convert_text(setting_name)
    column_name = ''
    
    if setting_type == SettingType.Boolean:
        column_name = 'settingboolean'
        value = util.db_convert_boolean(value)
    elif setting_type == SettingType.Float:
        column_name = 'settingfloat'
        value = value
    elif setting_type == SettingType.Integer:
        column_name = 'settingint'
        value = value
    elif setting_type == SettingType.Text:
        column_name = 'settingtext'
        value = util.db_convert_text(value)
    elif setting_type == SettingType.Timestamp:
        column_name = 'settingtimestamptz'
        value = util.db_convert_timestamp(value)
    
    utc_now = util.get_utcnow()
    modify_date = util.db_convert_timestamp(utc_now)
    values = ','.join([setting_name, modify_date, value])
    if existing_setting_value is None:
        query_insert = 'INSERT INTO {} (settingname, modifydate, {}) VALUES ({})'.format(SETTINGS_TABLE_NAME, column_name, values)
        success, error = db_try_execute(query_insert)
    else:
        query_update = 'UPDATE {} SET modifydate = {}, {} = {} WHERE settingname = {}'.format(SETTINGS_TABLE_NAME, modify_date, column_name, value, setting_name)
        success, error = db_try_execute(query_update)
    return success


# ---------- DataBase initilization ----------
def init_db(from_scratch=False):
    from pss_daily import DAILY_TABLE_NAME
    from pss_dropship import DROPSHIP_TEXT_TABLE_NAME
    error = None
    if from_scratch:
        deleted_table_daily, error = db_try_execute('DROP TABLE IF EXISTS {} CASCADE'.format(DAILY_TABLE_NAME))
        if deleted_table_daily:
            print('[init_db] dropped table {}'.format(DAILY_TABLE_NAME))
        else:
            print('[init_db] Could not drop table {}'.format(DAILY_TABLE_NAME))
        deleted_table_dropship, error = db_try_execute('DROP TABLE IF EXISTS {} CASCADE'.format(DROPSHIP_TEXT_TABLE_NAME))
        if deleted_table_dropship:
            print('[init_db] dropped table {}'.format(DROPSHIP_TEXT_TABLE_NAME))
        else:
            print('[init_db] Could not drop table {}'.format(DROPSHIP_TEXT_TABLE_NAME))
        deleted_table_settings, error = db_try_execute('DROP TABLE IF EXISTS {} CASCADE'.format(SETTINGS_TABLE_NAME))
        if deleted_table_settings:
            print('[init_db] dropped table {}'.format(SETTINGS_TABLE_NAME))
        else:
            print('[init_db] Could not drop table {}'.format(SETTINGS_TABLE_NAME))
    created_table_daily = try_create_table_daily()
    created_table_dropship = try_create_table_dropship_text()
    created_table_settings = try_create_table_settings()
    success = created_table_daily and created_table_dropship and created_table_settings
    if success:
        print('[init_db] db initialization succeeded')
    else:
        print('[init_db] db initialization failed')
        
        
def try_create_table_settings():
    column_definitions = []
    column_definitions.append(util.db_get_column_definition('settingname', 'text', is_primary=True, not_null=True))
    column_definitions.append(util.db_get_column_definition('modifydate', 'timestamptz', not_null=True))
    column_definitions.append(util.db_get_column_definition('settingboolean', 'boolean'))
    column_definitions.append(util.db_get_column_definition('settingfloat', 'double precision'))
    column_definitions.append(util.db_get_column_definition('settingint', 'integer'))
    column_definitions.append(util.db_get_column_definition('settingtext', 'text'))
    column_definitions.append(util.db_get_column_definition('settingtimestamptz', 'timestamptz'))
    success = db_try_create_table(SETTINGS_TABLE_NAME, column_definitions)
    return success
        
        
def try_create_table_daily():
    from pss_daily import DAILY_TABLE_NAME
    column_definitions = []
    column_definitions.append(util.db_get_column_definition('guildid', 'text', is_primary=True, not_null=True))
    column_definitions.append(util.db_get_column_definition('channelid', 'text', not_null=True))
    column_definitions.append(util.db_get_column_definition('canpost', 'boolean'))
    column_definitions.append(util.db_get_column_definition('latestmessageid', 'text'))
    success = db_try_create_table(DAILY_TABLE_NAME, column_definitions)
    return success
        
        
def try_create_table_dropship_text():
    from pss_dropship import DROPSHIP_TEXT_TABLE_NAME
    column_definitions = []
    column_definitions.append(util.db_get_column_definition('partid', 'text', is_primary=True, not_null=True))
    column_definitions.append(util.db_get_column_definition('oldvalue', 'text', not_null=True))
    column_definitions.append(util.db_get_column_definition('newvalue', 'text', not_null=True))
    column_definitions.append(util.db_get_column_definition('modifydate', 'timestamptz', not_null=True))
    success = db_try_create_table(DROPSHIP_TEXT_TABLE_NAME, column_definitions)
    return success


# ---------- DataBase functionality ----------
def db_close_cursor(cursor):
    if cursor is not None:
        cursor.close()
      

def db_connect():
    global DB_CONN
    if not db_is_connected(DB_CONN):
        try:
            DB_CONN = psycopg2.connect(DATABASE_URL, sslmode='require')
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


def db_fetchall(query):
    result = None
    error = None
    connected = db_connect()
    if connected:
        cursor = db_get_cursor()
        if cursor is not None:
            try:
                cursor.execute(query)
                result = cursor.fetchall()
            except (Exception, psycopg2.DatabaseError) as ex:
                ex_name = error.__class__.__name__
                error = f'{ex_name} while performing a query: {ex}'
                print(f'[db_fetchall] {error}')
            finally:
                db_close_cursor(cursor)
                db_disconnect()
        else:
            error = 'could not get cursor'
            print(f'[db_fetchall] {error}')
            db_disconnect()
    else:
        error = 'could not connect to db'
        print(f'[db_fetchall] {error}')
    return result, error


def db_fetchfirst(query):
    result = None
    error = None
    connected = db_connect()
    if connected:
        cursor = db_get_cursor()
        if cursor is not None:
            try:
                cursor.execute(query)
                result = cursor.fetchall()
            except (Exception, psycopg2.DatabaseError) as ex:
                ex_name = error.__class__.__name__
                error = f'{ex_name} while performing a query: {ex}'
                print(f'[db_fetchfirst] {error}')
            finally:
                db_close_cursor(cursor)
                db_disconnect()
        else:
            error = 'could not get cursor'
            print(f'[db_fetchfirst] {error}')
            db_disconnect()
    else:
        error = 'could not connect to db'
        print(f'[db_fetchfirst] {error}')
    if result and len(result) > 0:
        return result[0], error
    else:
        return None, error
        
        
def db_get_cursor():
    global DB_CONN
    connected = db_connect()
    if connected:
        return DB_CONN.cursor()
    else:
        print('[db_get_cursor] db is not connected')
    return None
    
    
def db_is_connected(connection):
    if connection:
        return connection.closed == 0
    return False


def db_select_any_from(table_name):
    query = 'SELECT * FROM {}'.format(table_name)
    result, error = db_fetchall(query)
    return result


def db_select_any_from_where(table_name, where=None):
    if where:
        query = 'SELECT * FROM {} WHERE {}'.format(table_name, where)
        result, error = db_fetchall(query)
        return result
    else:
        return db_select_any_from(table_name)


def db_select_any_from_where_and(table_name, where_collection):
    if where_collection:
        where = ' AND '.join(where_collection)
        return db_select_any_from_where(table_name, where)
    else:
        return db_select_any_from_where(table_name)


def db_select_any_from_where_or(table_name, where_collection):
    if where_collection:
        where = ' OR '.join(where_collection)
        return db_select_any_from_where(table_name, where)
    else:
        return db_select_any_from_where(table_name)


def db_select_first_from(table_name):
    print('+ called db_select_first_from({})'.format(table_name))
    query = 'SELECT * FROM {}'.format(table_name)
    result, error = db_fetchfirst(query)
    return result


def db_select_first_from_where(table_name, where=None):
    if where:
        query = 'SELECT * FROM {} WHERE {}'.format(table_name, where)
        result, error = db_fetchfirst(query)
        return result
    else:
        return db_select_first_from(table_name)


def db_select_first_from_where_and(table_name, where_collection):
    if where_collection:
        where = ' AND '.join(where_collection)
        return db_select_first_from_where(table_name, where)
    else:
        return db_select_first_from_where(table_name)


def db_select_first_from_where_or(table_name, where_collection):
    if where_collection:
        where = ' OR '.join(where_collection)
        return db_select_first_from_where_or(table_name, where)
    else:
        return db_select_first_from_where_or(table_name)
    
    
def db_try_commit():
    global DB_CONN
    connected = db_is_connected(DB_CONN)
    if connected:
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
        if cursor is not None:
            try:
                db_execute(query, cursor)
                print('[db_try_create_table] created table: {}'.format(table_name))
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
    error = None
    connected = db_connect()
    if connected:
        cursor = db_get_cursor()
        if cursor != None:
            try:
                db_execute(query, cursor)
                success = True
            except (Exception, psycopg2.DatabaseError) as ex:
                ex_name = ex.__class__.__name__
                error = f'{ex_name} while performing a query: {ex}'
                print(f'[db_try_execute] {error}')
            finally:
                db_close_cursor(cursor)
                db_disconnect()
        else:
            error = 'could not get cursor'
            print(f'[db_try_execute] {error}')
            db_disconnect()
    else:
        error = 'could not connect to db'
        print(f'[db_try_execute] {error}')
    return success, error
