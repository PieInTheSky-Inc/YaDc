#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime
import math
import os

import emojis
import pss_assert
import pss_core as core
import pss_lookups as lookups
import pss_tournament as tourney
import settings
import utility as util


# ---------- Constants ----------
TOP_FLEETS_BASE_PATH = f'AllianceService/ListAlliancesByRanking?skip=0&take='
TOP_CAPTAINS_BASE_PATH = f'LadderService/ListUsersByRanking?accessToken={settings.GPAT}&from=1&to='
STARS_BASE_PATH = f'AllianceService/ListAlliancesWithDivision'

ALLOWED_DIVISION_LETTERS = sorted([letter for letter in lookups.DIVISION_CHAR_TO_DESIGN_ID.keys() if letter != '-'])


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

def get_division_stars(division: str = None, fleet_data: dict = None, retrieved_date: datetime = None, as_embed: bool = settings.USE_EMBEDS):
    if division:
        pss_assert.valid_parameter_value(division, 'division', min_length=1, allowed_values=ALLOWED_DIVISION_LETTERS)
        if division == '-':
            division = None
    else:
        division = None

    if fleet_data is None or retrieved_date is None:
        data = core.get_data_from_path(STARS_BASE_PATH)
        fleet_infos = core.xmltree_to_dict3(data)
    else:
        fleet_infos = fleet_data

    divisions = {}
    if division:
        division_design_id = lookups.DIVISION_CHAR_TO_DESIGN_ID[division.upper()]
        divisions[division.upper()] = [fleet_info for fleet_info in fleet_infos.values() if fleet_info['DivisionDesignId'] == division_design_id]
        pass
    else:
        for division_design_id in lookups.DIVISION_DESIGN_ID_TO_CHAR.keys():
            if division_design_id != '0':
                division_letter = lookups.DIVISION_DESIGN_ID_TO_CHAR[division_design_id]
                divisions[division_letter] = [fleet_info for fleet_info in fleet_infos.values() if fleet_info['DivisionDesignId'] == division_design_id]

    if divisions:
        result = []
        for division_letter, fleet_infos in divisions.items():
            result.extend(_get_division_stars_as_text(division_letter, fleet_infos))
            result.append(settings.EMPTY_LINE)
        if result:
            result = result[:-1]
            if retrieved_date is not None:
                result.append(util.get_historic_data_note(retrieved_date))
        return result, True
    else:
        return [], False


def _get_division_stars_as_embed(division_letter: str, fleet_infos: dict):
    return ''


def _get_division_stars_as_text(division_letter: str, fleet_infos: list) -> list:
    lines = [f'__**Division {division_letter.upper()}**__']
    fleet_infos = util.sort_entities_by(fleet_infos, [('Score', int, True)])
    for i, fleet_info in enumerate(fleet_infos):
        fleet_name = fleet_info['AllianceName']
        if 'Trophy' in fleet_info.keys():
            trophies = fleet_info['Trophy']
            trophy_str = f' ({trophies} {emojis.trophy})'
        else:
            trophy_str = ''
        stars = fleet_info['Score']
        position = i + 1
        if util.should_escape_entity_name(fleet_name):
            fleet_name = f'`{fleet_name}`'
        lines.append(f'**{position:d}.** {stars} {emojis.star} {fleet_name}{trophy_str}')
    return lines