#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import math
import os

import emojis
import pss_core as core
import pss_tournament as tourney
import settings


# ---------- Top 100 Alliances ----------

def get_top_fleets(take: int = 100, as_embed: bool = settings.USE_EMBEDS):
    path = f'AllianceService/ListAlliancesByRanking?skip=0&take={take}'
    raw_data = core.get_data_from_path(path)
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
    access_token = os.getenv('GPAT')
    path = f'LadderService/ListUsersByRanking?accessToken={access_token}&from=1&to={take}'
    raw_data = core.get_data_from_path(path)
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
