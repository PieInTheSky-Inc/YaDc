#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime
import os
import urllib.parse

import emojis
import pss_assert
import pss_core as core
import pss_entity as entity
import pss_fleet as fleet
import pss_lookups as lookups
import pss_ship as ship
import pss_top as top
import settings
import utility as util


# ---------- Constants ----------

SEARCH_USERS_BASE_PATH = f'UserService/SearchUsers?searchString='
USER_KEY_NAME = 'Id'
USER_DESCRIPTION_PROPERTY_NAME = 'Name'

LEAGUE_BASE_PATH = f'LeagueService/ListLeagues2?accessToken='
LEAGUE_INFO_KEY_NAME = 'LeagueId'
LEAGUE_INFO_DESCRIPTION_PROPERTY_NAME = 'LeagueName'
LEAGUE_INFOS_CACHE = []










# ---------- Helper functions ----------

def _calculate_win_rate(wins: int, losses: int, draws: int) -> float:
    battles = wins + losses + draws
    if battles > 0:
        result = (wins + .5 * draws) / battles
        result *= 100
    else:
        result = 0.0
    return result


def _get_league_from_trophies(trophies: int) -> str:
    result = '-'
    if trophies is not None:
        for league_info in LEAGUE_INFOS_CACHE:
            if trophies >= league_info['MinTrophy'] and trophies <= league_info['MaxTrophy']:
                result = league_info[LEAGUE_INFO_DESCRIPTION_PROPERTY_NAME]
                break
    return result


async def get_user_details_by_info(user_info: dict) -> list:
    user_id = user_info[USER_KEY_NAME]
    utc_now = util.get_utcnow()
    inspect_ship_info = await ship.get_inspect_ship_for_user(user_id)
    ship_info = {}
    for key in inspect_ship_info.keys():
        if key != user_id:
            ship_info = inspect_ship_info[key]

    fleet_id = user_info['AllianceId']

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
    ship_status = ship_info.get('ShipStatus', '<unknown>')
    stars = user_info['AllianceScore']
    trophies = int(user_info['Trophy'])
    user_name = user_info[USER_DESCRIPTION_PROPERTY_NAME]
    user_type = user_info['UserType']

    has_fleet = fleet_id != '0'

    if has_fleet:
        fleet_info = await fleet._get_fleet_info_by_id(fleet_id)
        if fleet_info:
            division_design_id = fleet_info['DivisionDesignId']
            fleet_join_date = util.parse_pss_datetime(user_info['AllianceJoinDate'])
            fleet_joined_ago = util.get_formatted_timedelta(fleet_join_date - utc_now)
            fleet_name = fleet_info[fleet.FLEET_DESCRIPTION_PROPERTY_NAME]
            fleet_rank = lookups.get_lookup_value_or_default(lookups.ALLIANCE_MEMBERSHIP, user_info['AllianceMembership'], user_info['AllianceMembership'])
            fleet_name_and_rank = f'{fleet_name} ({fleet_rank})'
            joined = f'{util.format_excel_datetime(fleet_join_date)} ({fleet_joined_ago})'
        else:
            division_design_id = '0'
            fleet_name_and_rank = '<unknown>'
            joined = '-'
    else:
        division_design_id = '0'
        fleet_name_and_rank = '<no fleet>'
        joined = '-'

    ranking = None
    if trophies >= 5000:
        top_captains = await top.get_top_captains_dict()
        for i, top_captain_id in enumerate(top_captains, 1):
            if top_captain_id == user_id:
                ranking = util.get_ranking(i)
                break

    created_ago = util.get_formatted_timedelta(created_on_date - utc_now)
    created = f'{util.format_excel_datetime(created_on_date)} ({created_ago})'
    defense_win_rate = _calculate_win_rate(defense_wins, defense_losses, defense_draws)
    division = lookups.get_lookup_value_or_default(lookups.DIVISION_DESIGN_ID_TO_CHAR, division_design_id, '-')
    league_name = _get_league_from_trophies(trophies)
    level = None
    if user_id:
        level = await ship.get_ship_level(ship_info)
    if level is None:
        level = '-'
    logged_in_ago = util.get_formatted_timedelta(logged_in_date - utc_now)
    logged_in = f'{util.format_excel_datetime(logged_in_date)} ({logged_in_ago})'
    pvp_win_rate = _calculate_win_rate(pvp_wins, pvp_losses, pvp_draws)
    status = lookups.get_lookup_value_or_default(lookups.USER_STATUS, ship_status, default=ship_status)
    user_type = lookups.get_lookup_value_or_default(lookups.USER_TYPE, user_type)

    lines = [f'**```{user_name}```**```']
    if ranking is not None:
        lines.append(f'Ranking: {ranking}')
    lines.append(f'Account created: {created}')
    lines.append(f'Last login: {logged_in}')
    lines.append(f'Fleet: {fleet_name_and_rank}')
    if has_fleet:
        lines.append(f'Division: {division}')
        lines.append(f'Joined fleet: {joined}')
    lines.append(f'Trophies: {trophies}')
    lines.append(f'League: {league_name}')
    lines.append(f'Highest trophies: {highest_trophies}')
    if stars != '0':
        lines.append(f'Stars: {stars}')
    if has_fleet:
        lines.append(f'Crew donated: {crew_donated}')
        lines.append(f'Crew borrowed: {crew_received}')
    lines.append(f'PVP win/lose/draw: {pvp_wins}/{pvp_losses}/{pvp_draws} ({pvp_win_rate:0.2f}%)')
    lines.append(f'Defense win/lose/draw: {defense_wins}/{defense_losses}/{defense_draws} ({defense_win_rate:0.2f}%)')
    lines.append(f'Level: {level}')
    lines.append(f'Status: {status}')
    if user_type:
        lines.append(f'User type: {user_type}')

    lines[-1] += '```'

    return lines


async def _get_user_details_from_tournament_data(user_info: dict, user_data: dict) -> list:
    user_id = user_info[USER_KEY_NAME]
    user_info['AllianceScore'] = user_data[user_id]['AllianceScore']
    return await get_user_details_by_info(user_info)


async def get_user_infos_from_tournament_data(user_name: str, user_data: dict, fleet_data: dict) -> list:
    user_name = user_name.lower()
    result = [user_info for user_info in user_data.values() if user_name in user_info.get('Name', '').lower()]
    if not result:
        result = list((await _get_user_infos(user_name)).values())
    return result










# ---------- User info ----------

async def get_user_details_by_name(user_name: str, as_embed: bool = settings.USE_EMBEDS) -> list:
    pss_assert.valid_parameter_value(user_name, 'user_name', min_length=0)

    user_infos = list((await _get_user_infos(user_name)).values())
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


async def _get_user_infos(user_name: str) -> dict:
    path = f'{SEARCH_USERS_BASE_PATH}{util.url_escape(user_name)}'
    user_data_raw = await core.get_data_from_path(path)
    user_infos = core.xmltree_to_dict3(user_data_raw)
    return user_infos


def get_user_details_from_tourney_info(user_info: entity.EntityDesignInfo, fleet_infos: entity.EntitiesDesignsData, retrieved_at: datetime) -> list:
    no_data = '<no data>'
    no_fleet = '<no fleet>'
    lines = []

    user_name = user_info.get('Name', no_data)
    fleet_id = user_info.get('AllianceId', '0')
    fleet_info = fleet_infos.get(fleet_id, None)
    trophies = user_info.get('Trophy', no_data)
    stars = user_info.get('AllianceScore', no_data)
    logged_in_at = user_info.get('LastLoginDate', None)
    if logged_in_at:
        logged_in_at = util.parse_pss_datetime(logged_in_at)
        logged_in_ago = util.get_formatted_timedelta(logged_in_at - retrieved_at)
        logged_in = f'{util.format_excel_datetime(logged_in_at)} ({logged_in_ago})'
    else:
        logged_in = no_data

    if fleet_info is None:
        fleet_name = no_data
        joined_fleet_at = None
        fleet_name_and_rank = None
        division = None
    else:
        fleet_name = fleet_info.get(fleet.FLEET_DESCRIPTION_PROPERTY_NAME, no_data)

        joined_fleet_at = user_info.get('AllianceJoinDate', None)
        if joined_fleet_at:
            joined_fleet_at = util.parse_pss_datetime(joined_fleet_at)
            joined_fleet_ago = util.get_formatted_timedelta(joined_fleet_at - retrieved_at)
            joined_fleet = f'{util.format_excel_datetime(joined_fleet_at)} ({joined_fleet_ago})'
        else:
            joined_fleet = no_data
        fleet_rank = user_info.get('AllianceMembership', no_data)
        fleet_name_and_rank = f'{fleet_name} ({fleet_rank})'
        division_design_id = fleet_info.get('DivisionDesignId', None)
        if division_design_id:
            division = lookups.get_lookup_value_or_default(lookups.DIVISION_DESIGN_ID_TO_CHAR, division_design_id, '-')
        else:
            division = None
    if trophies == no_data:
        league_name = no_data
    else:
        league_name = _get_league_from_trophies(int(trophies))

    lines.append(f'**```{user_name}```**```')
    lines.append(f'Last login: {logged_in}')
    lines.append(f'Fleet: {fleet_name_and_rank}')
    if division:
        lines.append(f'Division: {division}')
    if joined_fleet:
        lines.append(f'Joined fleet: {joined_fleet}')
    lines.append(f'Trophies: {trophies}')
    lines.append(f'League: {league_name}')
    lines.append(f'Stars: {stars}')

    if retrieved_at is not None:
        lines.append(f'```{util.get_historic_data_note(retrieved_at)}')
    else:
        lines[-1] += '```'

    return lines











# ---------- Initialization ----------

async def init():
    league_data = await core.get_data_from_path(LEAGUE_BASE_PATH)
    league_infos = core.xmltree_to_dict3(league_data)
    for league_info in sorted(list(league_infos.values()), key=lambda league_info: int(league_info['MinTrophy'])):
        league_info['MinTrophy'] = int(league_info['MinTrophy'])
        league_info['MaxTrophy'] = int(league_info['MaxTrophy'])
        LEAGUE_INFOS_CACHE.append(league_info)