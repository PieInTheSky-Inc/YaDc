#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Pixel Starships Market API


# ----- Packages ------------------------------------------------------
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import argparse
import datetime
import csv
import numpy as np
import os
import pandas as pd
import pss_core as core
import pss_prestige as p
import re
import urllib.request
import xml.etree.ElementTree


# Discord limits messages to 2000 characters
MESSAGE_CHARACTER_LIMIT = 2000
HOME = os.getenv('HOME')

base_url = 'http://{}/'.format(core.get_production_server())


# ----- Utilities -----------------------------------------------------
def save_raw_text(raw_text, filename):
    with open(filename, 'w') as f:
        f.write(raw_text)

def get_base_url(api_version=1, https=False):
    if https is True:
        prefix = 'https://'
    else:
        prefix = 'http://'

    if api_version==2:
        return prefix + 'api2.pixelstarships.com/'
    else:
        return prefix + 'api.pixelstarships.com/'


# ----- Get Latest Version --------------------------------------------
def get_latest_version():
    url= base_url + 'SettingService/GetLatestVersion?language=Key=en'
    data = urllib.request.urlopen(url).read()
    return data.decode()


# ----- Item Designs --------------------------------------------------
def get_item_designs():
    url = base_url + 'ItemService/ListItemDesigns2?languageKey=en'
    data = urllib.request.urlopen(url).read()
    return data.decode()


def save_item_design_raw(raw_text):
    now = datetime.datetime.now()
    filename = 'data/items-{}.txt'.format(now.strftime('%Y%m%d'))
    save_raw_text(raw_text, filename)


def load_item_design_raw(refresh=False):
    now = datetime.datetime.now()
    filename = 'data/items{}.txt'.format(now.strftime('%Y%m%d'))
    if os.path.isfile(filename) and refresh is False:
        with open(filename, 'r') as f:
            raw_text = f.read()
    else:
        raw_text = get_item_designs()
        save_item_design_raw(raw_text)
    return raw_text


def parse_item_designs(raw_text):
    d = {}
    # r_lookup = {}
    root = xml.etree.ElementTree.fromstring(raw_text)
    for c in root:
        # print(c.tag) # ListItemDesigns
        for cc in c:
            # print(cc.tag) # ItemDesigns
            for ccc in cc:
                # print(ccc.tag) # ItemDesign
                if ccc.tag != 'ItemDesign':
                    continue

                item_name = ccc.attrib['ItemDesignName']
                d[item_name] = ccc.attrib
                # r_lookup[int(ccc.attrib['ItemDesignId'])] = item_name
    return d


def xmltext_to_df(raw_text):
    df = pd.DataFrame()
    root = xml.etree.ElementTree.fromstring(raw_text)
    for c in root:
        for cc in c:
            for i, ccc in enumerate(cc):
                df = df.append(pd.DataFrame(ccc.attrib, index=[i]))
    return df


# ----- Lists ---------------------------------------------------------
def get_lists(df_items):
    item_rarities = list(df_items.Rarity.unique())
    item_enhancements = list(df_items.EnhancementType.unique())
    item_types = list(df_items.ItemType.unique())
    item_subtypes = list(df_items.ItemSubType.unique())
    return item_rarities, item_enhancements, item_types, item_subtypes


# ----- Parsing -------------------------------------------------------
def fix_item(item):
    # Convert to lower case & non alpha-numeric
    item = re.sub('[^a-z0-9]', '', item.lower())
    item = re.sub('anonmask', 'anonymousmask', item)
    item = re.sub('armour', 'armor', item)
    item = re.sub('bunny', 'rabbit', item)
    item = re.sub("(darkmatterrifle|dmr)(mark|mk)?(ii|2)", "dmrmarkii", item)
    item = re.sub('golden', 'gold', item)
    return item


def filter_item_designs(search_str, rtbl, filter):
    item_original = list(rtbl.keys())
    item_lookup = [ fix_item(s) for s in item_original ]
    item_fixed  = fix_item(search_str)

    txt = ''
    for i, item_name in enumerate(item_lookup):

        m = re.search(item_fixed, item_name)
        if m is not None:
            item_name  = item_original[i]
            d = rtbl[item_name]

            # Filter out items
            if (item_name == 'Gas'            or
                item_name == 'Mineral'        or
                d['MissileDesignId']   != '0' or
                d['CraftDesignId']     != '0' or
                d['CharacterDesignId'] != '0'):
                continue

            # Process
            # item_price = d['FairPrice']
            item_price = d['MarketPrice']
            item_slot  = re.sub('Equipment', '', d['ItemSubType'])
            item_stat  = d['EnhancementType']
            item_stat_value = d['EnhancementValue']

            if filter == 'price':
                if item_price == '0':
                    item_price = 'NA'
                txt += '{}: {}\n'.format(item_name, item_price)
            elif filter == 'stats':
                if item_stat == 'None':
                    continue
                txt += '{}: {} +{} ({})\n'.format(item_name,
                    item_stat, item_stat_value, item_slot)
            else:
                print('Invalid filter')
                quit()

    if len(txt) == 0:
        return None
    else:
        return txt.strip('\n')


def get_real_name(search_str, rtbl):
    item_original = list(rtbl.keys())
    item_lookup = [ fix_item(s) for s in item_original ]
    item_fixed  = fix_item(search_str)

    try:
        # Attempt to find an exact match
        idx = item_lookup.index(item_fixed)
        return item_original[idx]
    except:
        # Perform search if the exact match failed
        m = [ re.search(item_fixed, n) is not None for n in item_lookup ]
        item = pd.Series(item_original)[m]
        if len(item) > 0:
            return item.iloc[0]
        else:
            return None


# ----- Item Stats ----------------------------------------------------
def get_item_stats(item_name):
    raw_text = load_item_design_raw()
    item_lookup = parse_item_designs(raw_text)
    market_txt = filter_item_designs(item_name, item_lookup, filter='stats')
    if market_txt is not None:
        market_txt = '**Item Stats**\n' + market_txt
    return market_txt


# ----- Best Items ----------------------------------------------------
def rtbl2items(rtbl):
    df_rtbl = pd.DataFrame(rtbl).T
    m1 = df_rtbl.EnhancementType != 'None'
    m2 = df_rtbl.ItemSubType.str.contains('Equipment')
    df_items = df_rtbl[m1 & m2].copy()
    df_items.ItemSubType = df_items.ItemSubType.str.replace('Equipment', '')
    df_items.ItemSubType = df_items.ItemSubType.str.lower()
    df_items.EnhancementType = df_items.EnhancementType.str.lower()
    df_items.EnhancementValue = df_items.EnhancementValue.astype(float)
    return df_items


def filter_item(df_items, slot, enhancement, cols=None):
    slot = slot.lower()
    enhancement = enhancement.lower()
    m1 = df_items.ItemSubType == slot
    m2 = df_items.EnhancementType == enhancement
    if cols is None:
        return df_items[m1 & m2].sort_values(
            'EnhancementValue', ascending=False).copy()
    else:
        return df_items.loc[m1 & m2, cols].sort_values(
            'EnhancementValue', ascending=False).copy()


def itemfilter2txt(df_filter):
    if len(df_filter) == 0:
        return None

    txt = ''
    for row in df_filter.iterrows():
        data = row[1]
        mprice = data['MarketPrice']
        if mprice == '0':
            mprice = 'NA'
        txt += '{}: {} ({} bux)\n'.format(data[0], data[1], mprice)
    return txt


# ----- Item Ingredients ----------------------------------------------
def get_item_rlookup(df):
    item_rlookup = {}
    for row in df.iterrows():
        data = row[1]
        item_rlookup[data['ItemDesignId']] = data['ItemDesignName']
    return item_rlookup


def get_recipe(df, item_rlookup, item_name):
    ingredients = df.loc[df['ItemDesignName'] == item_name, 'Ingredients']
    if len(ingredients) == 1:
        ingredients = ingredients.values[0]
        if len(ingredients) == 0:
            return None
        ingredients = ingredients.split('|')
        recipe = {}
        for ingredient in ingredients:
            item_id, item_qty = ingredient.split('x')
            recipe[item_rlookup[item_id]] = int(item_qty)
        return recipe
    else:
        return None


def print_recipe(recipe, df_items):
    txt = ''
    total = 0
    for ingredient in recipe.keys():
        qty = recipe[ingredient]
        fprice = df_items.loc[df_items['ItemDesignName'] == ingredient, 'FairPrice'].iloc[0]
        mprice = df_items.loc[df_items['ItemDesignName'] == ingredient, 'MarketPrice'].iloc[0]
        if mprice == '0':
            mprice = np.nan
            txt += '{} x {} (price: NA)\n'.format(qty, ingredient)
        else:
            mprice = int(mprice)
            txt += '{} x {} ({} bux): {} bux\n'.format(qty, ingredient, mprice, qty*mprice)
        total += qty*mprice
    if np.isnan(total):
        txt += 'Crafting Cost: NA'
    else:
        txt += 'Crafting Cost: {} bux'.format(total)
    return txt


def collapse_recipe(recipe, df_items, item_rlookup):
    collapse = False
    sub_recipe = {}
    for ingredient in recipe.keys():
        qty = recipe[ingredient]
        sub_ingredients = get_recipe(df_items, item_rlookup, ingredient)
        if sub_ingredients is None:
            if ingredient in sub_recipe.keys():
                sub_recipe[ingredient] += recipe[ingredient]
            else:
                sub_recipe[ingredient] = recipe[ingredient]
        else:
            for sub_ingredient in sub_ingredients:
                if sub_ingredient in sub_recipe.keys():
                    sub_recipe[sub_ingredient] += qty * sub_ingredients[sub_ingredient]
                else:
                    sub_recipe[sub_ingredient] = qty * sub_ingredients[sub_ingredient]
            collapse = True
        # print('{} x {}: {}'.format(qty, ingredient, sub_ingredients))
    if collapse is True:
        return sub_recipe
    else:
        return None


def get_multi_recipe(name, levels=1):
    raw_text = load_item_design_raw()
    item_lookup = parse_item_designs(raw_text)
    real_name = get_real_name(name, item_lookup)

    df_items = xmltext_to_df(raw_text)
    item_rlookup = get_item_rlookup(df_items)
    recipe = get_recipe(df_items, item_rlookup, real_name)

    txt = ''
    level = 1
    while recipe is not None:
        txt += print_recipe(recipe, df_items)
        recipe = collapse_recipe(recipe, df_items, item_rlookup)
        level += 1
        if level > levels:
            break
        if recipe is not None:
            txt += '\n\n'
    return txt


def get_item_recipe(name, levels=5):
    raw_text = load_item_design_raw()
    item_lookup = parse_item_designs(raw_text)
    # print('name = {}'.format(name))
    real_name = get_real_name(name, item_lookup)
    # print('real_name = {}'.format(real_name))
    if real_name is not None:
        content = get_multi_recipe(real_name, levels)
    return content, real_name


# ----- Lists ---------------------------------------------------------
def get_item_list():
    raw_text = load_item_design_raw()
    df_items = xmltext_to_df(raw_text)
    items = list(df_items['ItemDesignName'])
    # print('List of items: ' + ', '.join(items))
    return core.list_to_text(items)


# ----- Main ----------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=
        'Pixel Starships Market API')
    parser.add_argument('--market', action='store_true',
        help='Get Market Data')
    parser.add_argument('--subtype', default='None',
        help='Subtype for market data')
    parser.add_argument('--rarity', default='None',
        help='Rarity for market data')
    parser.add_argument('--stats', default=None,
        help='Get Stats on Item')
    parser.add_argument('--recipe', default=None,
        help='Get Recipe for Item')
    parser.add_argument('--price', default=None,
        help='Get Price on Item')
    parser.add_argument('--list', action='store_true',
        help='Get List of items')
    args = parser.parse_args()

    if args.list is True:
        # python3 pss_market.py --list
        txt_list = get_item_list()
        for txt in txt_list:
            print(txt)
    elif args.stats is not None:
        # python3 pss_market.py --stats 'assault armor'
        pass
    elif args.recipe is not None:
        name = args.recipe
        content, real_name = get_item_recipe(name, levels=5)
        if real_name is not None:
            content = '**Recipe for {}**\n'.format(real_name) + content
            content = content + '\n\nNote: bux prices listed here may not always be accurate due to transfers between alts/friends or other reasons'
        print(content)
    elif args.price is not None:
        # python3 pss_market.py --price 'assault armor'
        item_name = args.price
        raw_text = load_item_design_raw()
        rtbl = parse_item_designs(raw_text)
        real_name = get_real_name(item_name, rtbl)

        if real_name is not None:
            print('Getting the price of {}'.format(real_name))
            mkt_text = filter_item_designs(real_name, rtbl, filter='price')
            print(mkt_text)
        else:
            print('{} not found'.format(item_name))
    else:
        print('Problem parsing argument list')
        print('args.stats = {}'.format(args.stats))
        print('args.price = {}'.format(args.price))
