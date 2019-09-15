#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
import csv
import datetime
import os
import psycopg2
from psycopg2 import errors as db_error
import re
from typing import Callable
import urllib.parse
import urllib.request
import xml.etree.ElementTree


DATABASE_URL = os.environ['DATABASE_URL']
PSS_CHARS_FILE = 'pss-chars.txt'
PSS_CHARS_RAW_FILE = 'pss-chars-raw.txt'
PSS_LINKS_FILE = 'src/data/links.csv'
PSS_ABOUT_FILE = 'src/data/about.txt'
MAXIMUM_CHARACTERS = 1900
DB_CONN = None


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


def is_old_file(filename, max_days=0, max_seconds=3600, verbose=True):
    """Returns true if the file modification date > max_days / max_seconds ago
    or if the file does not exist"""
    if os.path.isfile(filename) is not True:
        return True
    st = os.stat(filename)
    mtime = st.st_mtime
    now = datetime.datetime.now()
    time_diff = now - datetime.datetime.fromtimestamp(mtime)
    if verbose is True:
        print('Time since file {} creation: {}'.format(filename, time_diff))
    return (time_diff.days > max_days) or time_diff.seconds > max_seconds


def load_data_from_url(filename, url, refresh='auto'):
    if os.path.isfile(filename) and refresh != 'true':
        if refresh == 'auto':
            if is_old_file(filename, max_seconds=3600):
                raw_text = get_data_from_url(url)
                save_raw_text(raw_text, filename)
                return raw_text
        with open(filename, 'r') as f:
            raw_text = f.read()
    else:
        raw_text = get_data_from_url(url)
        save_raw_text(raw_text, filename)
    return raw_text


def xmltree_to_dict3(raw_text, key_name):
    root = xml.etree.ElementTree.fromstring(raw_text)
    key = 0
    d = {}
    for c in root:
        for cc in c:
            for ccc in cc:
                if key_name:
                    d[ccc.attrib[key_name]] = ccc.attrib
                else:
                    d[key] = ccc.attrib
                    key += 1
    return d


def xmltree_to_dict2(raw_text, key_name):
    root = xml.etree.ElementTree.fromstring(raw_text)
    key = 0
    d = {}
    for c in root:
        for cc in c:
            if key_name:
                d[cc.attrib[key_name]] = cc.attrib
            else:
                d[key] = cc.attrib
                key += 1
    return d


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

def fix_property_value(property_value: str) -> str:
    result = property_value.lower()
    result = result.strip()
    result = __rx_property_fix_replace.sub('', result)
    return result


def get_ids_from_property_value(data: dict, property_name: str, property_value: str, fix_data_delegate: Callable = None, return_on_first: bool = True) -> list:
    # data structure: {id: content}
    # fixed_data structure: {description: id}
    if not data or not property_name or not property_value:
        print(f'- get_ids_from_property_value: invalid data or property info. Return empty list.')
        return []

    fixed_value = fix_property_value(property_value)
    fixed_data = {fix_property_value(data[row_id][property_name]): row_id for row_id in data}

    if fix_data_delegate:
        fixed_value = fix_data_delegate(property_value)
        fixed_data = {fix_data_delegate(data[row_id][property_name]): row_id for row_id in data}

    if return_on_first and fixed_value in fixed_data.keys():
        return [fixed_data[fixed_value]]

    results = [fixed_data[description] for description in fixed_data.keys() if fixed_value in description]
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
            result = _filter_data_list(result, key, value, ignore_case, alphanumerical)
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
            if entry_value == value:
                result.append(entry)
        return result
    else:
        return data


def filter_data_dict(data: dict, by: dict, ignore_case: bool = False):
    """Parameter 'data':
       - A dict with entity ids as keys and entity info as values.
       Parameter 'by':
       - Keys are names of entity fields to filter by.
       - Values are values that each respective field should have."""
    result = data
    if by:
        for key, value in by.items():
            result = _filter_data_list(result, key, value)
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
            if entry_value == value:
                result[key] = entry
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
    d = xmltree_to_dict2(raw_text, key_name=None)
    return d[0]['ProductionServer']


def get_base_url():
    production_server = get_production_server()
    result = f'https://{production_server}/'
    return result


# ----- Links -----
def read_links_file():
    with open(PSS_LINKS_FILE) as f:
        csv_file = csv.reader(f, delimiter=',')
        txt = '**Links**'
        for row in csv_file:
            title, url = row
            txt += '\n{}: <{}>'.format(title, url.strip())
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
