#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime
import os
import urllib.parse

import emojis
import pss_assert
import pss_core as core
import pss_lookups as lookups
import pss_ship as ship
import settings
import utility as util


# ---------- Constants ----------

SEARCH_USERS_BASE_PATH = f'UserService/SearchUsers?searchString='
USER_KEY_NAME = 'Id'
USER_DESCRIPTION_PROPERTY_NAME = 'Name'










# ---------- Helper functions ----------

def get_user_details_by_info(user_info: dict) -> list:
    user_id = user_info[USER_KEY_NAME]
    utc_now = util.get_utcnow()
    inspect_ship_info = ship.get_inspect_ship_for_user(user_id)
    for key in inspect_ship_info.keys():
        if key != user_id:
            ship_info = inspect_ship_info[key]

    alliance_id = user_info['AllianceId']
    created_on_date = util.parse_pss_datetime(user_info['CreationDate'])
    crew_donated = user_info['CrewDonated']
    crew_received = user_info['CrewReceived']
    defense_draws = int(user_info['PVPDefenceDraws'])
    defense_losses = int(user_info['PVPDefenceLosses'])
    defense_wins = int(user_info['PVPDefenceWins'])
    highest_trophies = user_info['HighestTrophy']
    logged_in_date = util.parse_pss_datetime(user_info['LastLoginDate'])
    pvp_draws = int(user_info['PVPAttackDraws'])
    pvp_losses = int(user_info['PVPAttackLosses'])
    pvp_wins = int(user_info['PVPAttackWins'])
    ship_status = ship_info['ShipStatus']
    stars = user_info['AllianceScore']
    trophies = user_info['Trophy']
    user_name = user_info[USER_DESCRIPTION_PROPERTY_NAME]
    user_type = user_info['UserType']

    if alliance_id != '0':
        division_design_id = user_info['AllianceQualifyDivisionDesignId']
        fleet_join_date = util.parse_pss_datetime(user_info['AllianceJoinDate'])
        fleet_joined_ago = util.get_formatted_timedelta(fleet_join_date - utc_now)
        fleet_name = user_info['AllianceName']
        fleet_rank = lookups.get_lookup_value_or_default(lookups.ALLIANCE_MEMBERSHIP, user_info['AllianceMembership'], user_info['AllianceMembership'])
        fleet_name_and_rank = f'{fleet_name} ({fleet_rank})'
        joined = f'{util.format_excel_datetime(fleet_join_date)} ({fleet_joined_ago})'
    else:
        division_design_id = '0'
        fleet_name_and_rank = '-'
        joined = '-'

    created_ago = util.get_formatted_timedelta(created_on_date - utc_now)
    created = f'{util.format_excel_datetime(created_on_date)} ({created_ago})'
    defense_win_rate = _calculate_win_rate(defense_wins, defense_losses, defense_draws)
    division = lookups.get_lookup_value_or_default(lookups.DIVISION_DESIGN_ID_TO_CHAR, division_design_id, '-')
    if user_id:
        level = ship.get_ship_level(ship_info)
    else:
        level = '-'
    logged_in_ago = util.get_formatted_timedelta(logged_in_date - utc_now)
    logged_in = f'{util.format_excel_datetime(logged_in_date)} ({logged_in_ago})'
    pvp_win_rate = _calculate_win_rate(pvp_wins, pvp_losses, pvp_draws)
    if division == '-':
        stars = '-'
    status = lookups.get_lookup_value_or_default(lookups.USER_STATUS, ship_status, default=ship_status)
    user_type = lookups.get_lookup_value_or_default(lookups.USER_TYPE, user_type, user_type)

    lines = [f'**```{user_name}```**```']
    lines.append(f'Account created: {created}')
    lines.append(f'Last login: {logged_in}')
    lines.append(f'Fleet: {fleet_name_and_rank}')
    lines.append(f'Joined fleet: {joined}')
    lines.append(f'Trophies: {trophies}')
    lines.append(f'Highest trophies: {highest_trophies}')
    lines.append(f'Division: {division}')
    lines.append(f'Stars: {stars}')
    lines.append(f'Crew donated: {crew_donated}')
    lines.append(f'Crew borrowed: {crew_received}')
    lines.append(f'PVP win/lose/draw: {pvp_wins}/{pvp_losses}/{pvp_draws} ({pvp_win_rate:0.2f}%)')
    lines.append(f'Defense win/lose/draw: {defense_wins}/{defense_losses}/{defense_draws} ({defense_win_rate:0.2f}%)')
    lines.append(f'Level: {level}')
    lines.append(f'Status: {status}')
    lines.append(f'User type: {user_type}')

    lines[-1] += '```'

    return lines


def _calculate_win_rate(wins: int, losses: int, draws: int) -> float:
    battles = wins + losses + draws
    if battles > 0:
        result = (wins + .5 * draws) / battles
        result *= 100
    else:
        result = 0.0
    return result










# ---------- User info ----------

def get_user_details_by_name(user_name: str, as_embed: bool = settings.USE_EMBEDS) -> list:
    pss_assert.valid_parameter_value(user_name, 'user_name', min_length=0)

    user_infos = _get_user_infos(user_name)
    user_ids = sorted([int(user_id) for user_id in user_infos.keys() if user_id])
    user_ids = [str(user_id) for user_id in user_ids]
    user_infos = [user_info for user_id, user_info in user_infos.items() if user_id in user_ids]
    return user_infos


def get_user_search_details(user_info: dict) -> str:
    user_name = user_info[USER_DESCRIPTION_PROPERTY_NAME]
    user_trophies = user_info['Trophy']
    user_stars = user_info['AllianceScore']
    if user_info['AllianceId'] != '0':
        fleet_division = int(user_info['AllianceQualifyDivisionDesignId'])
        fleet_name = user_info['AllianceName']
    else:
        fleet_division = 0
        fleet_name = ''
    trophies = f'{emojis.trophy} {user_trophies}'
    if fleet_name:
        fleet = f' (Fleet: {fleet_name})'
    else:
        fleet = ''
    if fleet_division > 0:
        stars = f'{emojis.star} {user_stars}'
    else:
        stars = ''
    result = f'{user_name}{fleet}, {trophies}, {stars}'
    return result


def _get_user_infos(user_name: str) -> dict:
    path = f'{SEARCH_USERS_BASE_PATH}{util.url_escape(user_name)}'
    user_data_raw = core.get_data_from_path(path)
    user_infos = core.xmltree_to_dict3(user_data_raw)
    return user_infos
