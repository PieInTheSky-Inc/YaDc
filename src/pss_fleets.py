#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import datetime
import os
import pandas as pd
import re
import urllib.request
import uuid
import xml.etree.ElementTree

import pss_core as core


base_url = 'http://{}/'.format(core.get_production_server())


def alliancetxt_to_df(raw_text):
    df = pd.DataFrame()
    root = xml.etree.ElementTree.fromstring(raw_text)
    for i, c in enumerate(root):
        # print('{}: {}'.format(i, c.tag)) # ListAlliancesByRanking
        for ii, cc in enumerate(c):
            # print('  {}: {}'.format(ii, cc.tag)) # Alliances
            for iii, ccc in enumerate(cc):
                # print(ccc.tag) # Alliance
                row = pd.DataFrame(ccc.attrib, index=[iii])
                df = df.append(row)
    df['DivisionDesignId'] = df['DivisionDesignId'].astype(int)
    df['NumberOfApprovedMembers'] = df['NumberOfApprovedMembers'].astype(int)
    df['Score'] = df['Score'].astype(int)
    df['Trophy'] = df['Trophy'].astype(int)
    return df


def download_top_100_raw():
    url = base_url + 'AllianceService/ListAlliancesByRanking?skip=0&take=100'
    return core.get_data_from_url(url)


def download_tournament_participants_raw():
    url = f'{base_url}AllianceService/ListAlliancesWithDivision'
    return core.get_data_from_url(url)


def download_top_100():
    raw_text = download_top_100_raw()
    df_alliances = alliancetxt_to_df(raw_text)
    return df_alliances


def download_tournament_participants():
    raw_text = download_tournament_participants_raw()
    df_alliances = alliancetxt_to_df(raw_text)
    return df_alliances


def fleet_df_to_scores(df, division_id):
    # Note: division_id is int because
    # alliancetxt_to_df converts it
    if 'Score' in df.columns:
        col = 'Score'
    elif 'Trophy' in df.columns:
        col = 'Trophy'
    else:
        txt = 'Score / Trophy columns are not found in the table\n'
        txt += 'Columns: {}'.format(df.columns)
        return txt

    df = df[df.DivisionDesignId == division_id].sort_values(
        by=col, ascending=False)

    txt = ''
    for i, row in enumerate(df.iterrows()):
        position = i+1
        data = row[1]
        if col == 'Score':
            row_txt = '**{:d}.** {}⭐ {} ({} 🏆)'.format(position, data[col], data['AllianceName'], data['Trophy'])
        elif col == 'Trophy':
            row_txt = '**{:d}.** {}🏆 {}'.format(position, data[col], data['AllianceName'])
        if i == 0:
            txt += row_txt
        else:
            txt += '\n{}'.format(row_txt)
    return txt


def get_division_stars(division):
    if division is None:
        return get_all_division_stars()
    df_alliances = download_tournament_participants()
    division_table = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    division = division.upper()
    if division not in division_table.keys():
        return 'Division has to be A, B, C, or D'
    division_id = division_table[division]
    txt = '__**Division {}**__\n{}'.format(division, fleet_df_to_scores(df_alliances, division_id))
    return txt


def get_all_division_stars():
    df_alliances = download_tournament_participants()
    division_list = ['A', 'B', 'C', 'D']
    txt = ''
    for i, division in enumerate(division_list):
        division_id = i + 1
        title = '__**Division {}**__'.format(division)
        division_list = fleet_df_to_scores(df_alliances, division_id)
        txt += '{}\n{}\n\n'.format(title, division_list)
    return txt.strip()
