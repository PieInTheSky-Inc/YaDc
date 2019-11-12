#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import math
import os

import emojis
import pss_core as core
import pss_tournament as tourney
import settings


# ---------- Constants ----------
TOP_FLEETS_BASE_PATH = f'AllianceService/ListAlliancesByRanking?skip=0&take='
TOP_CAPTAINS_BASE_PATH = f'LadderService/ListUsersByRanking?accessToken={settings.GPAT}&from=1&to='
STARS_BASE_PATH = f''


# ---------- Top 100 Alliances ----------

def get_top_fleets(take: int = 100, as_embed: bool = settings.USE_EMBEDS):
    raw_data = core.get_data_from_path(TOP_FLEETS_BASE_PATH + str(take))
    data = core.xmltree_to_dict3(raw_data)
    if as_embed:
        return _get_top_fleets_as_embed(data, take), True
    else:
        return _get_top_fleets_as_text(data, take), True


def _get_top_fleets_as_embed(alliance_data: dict, take: int = 100):
    return ''


def _get_top_fleets_as_text(alliance_data: dict, take: int = 100):
    tourney_running = tourney.is_tourney_running()

    headline = f'**Top {take} fleets**'
    lines = [headline]

    position = 0
    for entry in alliance_data.values():
        position += 1
        name = entry['AllianceName']
        trophies = entry['Trophy']
        stars = entry['Score']

        trophy_txt = f'{trophies} {emojis.trophy}'
        if tourney_running:
            stars_txt = f', {stars} {emojis.star}'
        else:
            stars_txt = ''

        line = f'**{position}.** {name} ({trophy_txt}{stars_txt})'
        lines.append(line)

    return lines





# ---------- Top 100 Captains ----------

def get_top_captains(take: int = 100, as_embed: bool = settings.USE_EMBEDS):
    raw_data = core.get_data_from_path(TOP_CAPTAINS_BASE_PATH + str(take))
    data = core.xmltree_to_dict3(raw_data)
    if as_embed:
        return _get_top_captains_as_embed(data, take), True
    else:
        return _get_top_captains_as_text(data, take), True


def _get_top_captains_as_embed(captain_data: dict, take: int = 100):
    return ''


def _get_top_captains_as_text(captain_data: dict, take: int = 100):
    headline = f'**Top {take} captains**'
    lines = [headline]

    position = 0
    for entry in captain_data.values():
        position += 1
        name = entry['Name']
        trophies = entry['Trophy']
        fleet_name = entry['AllianceName']

        trophy_txt = f'{trophies} {emojis.trophy}'

        line = f'**{position}.** {name} ({fleet_name}): {trophy_txt}'
        lines.append(line)
        if position == take:
            break

    return lines





# ---------- Stars info ----------

def get_division_stars(division: str = None, as_embed: bool = settings.USE_EMBEDS):
    pass





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