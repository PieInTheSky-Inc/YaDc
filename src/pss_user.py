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
import pss_login as login
import pss_lookups as lookups
import pss_ship as ship
import pss_top as top
import pss_tournament as tourney
import pss_user as user
import settings
import utility as util


# ---------- Constants ----------

SEARCH_USERS_BASE_PATH = f'UserService/SearchUsers?searchString='
USER_KEY_NAME = 'Id'
USER_DESCRIPTION_PROPERTY_NAME = 'Name'

INSPECT_SHIP_BASE_PATH = f'ShipService/InspectShip2'

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


async def get_user_details_by_info(user_info: dict, max_tourney_battle_attempts: int = None, retrieved_at: datetime = None, past_fleet_infos: entity.EntitiesData = None) -> list:
    is_past_data = past_fleet_infos is not None and past_fleet_infos

    user_id = user_info[USER_KEY_NAME]
    retrieved_at = retrieved_at or util.get_utcnow()
    tourney_running = tourney.is_tourney_running(utc_now=retrieved_at)
    if past_fleet_infos:
        ship_info = {}
        fleet_info = past_fleet_infos.get(user_info.get(fleet.FLEET_KEY_NAME))
    else:
        _, ship_info = await ship.get_inspect_ship_for_user(user_id)
        fleet_info = await __get_fleet_info_by_user_info(user_info)

    user_name = __get_user_name_as_text(user_info)

    is_in_tourney_fleet = fleet.is_tournament_fleet(fleet_info) and tourney_running
    attempts = __get_tourney_battle_attempts(user_info, retrieved_at)
    if attempts and max_tourney_battle_attempts:
        attempts_left = max_tourney_battle_attempts - int(attempts)
    else:
        attempts_left = None

    details = {
        'Account created': __get_timestamp_as_text(user_info, 'CreationDate', retrieved_at),
        'Last login': __get_timestamp_as_text(user_info, 'LastLoginDate', retrieved_at),
        'Fleet': __get_fleet_name_and_rank_as_text(user_info, fleet_info),
        'Division': fleet.get_division_name_as_text(fleet_info),
        'Joined fleet': __get_fleet_joined_at_as_text(user_info, fleet_info, retrieved_at),
        'Trophies': __get_trophies_as_text(user_info),
        'League': __get_league_as_text(user_info),
        'Stars': __get_stars_as_text(user_info, is_in_tourney_fleet, attempts_left),
        'Crew donated': __get_crew_donated_as_text(user_info, fleet_info),
        'Crew borrowed': __get_crew_borrowed_as_text(user_info, fleet_info),
        'PVP win/lose/draw': __get_pvp_attack_stats_as_text(user_info),
        'Defense win/lose/draw': __get_pvp_defense_stats_as_text(user_info),
        'Level': await __get_level_as_text(ship_info),
        #'Status': __get_ship_status_as_text(ship_info),
        'User type': __get_user_type_as_text(user_info)
    }

    lines = [f'**```{user_name}```**```']
    for detail_name, detail_value in details.items():
        if detail_value is not None:
            lines.append(f'{detail_name} - {detail_value}')

    if is_past_data:
        lines.append(f'``````{util.get_historic_data_note(retrieved_at)}```')
    else:
        lines[-1] += '```'

    return lines


async def _get_user_details_from_tournament_data(user_info: dict, user_data: dict) -> list:
    user_id = user_info[USER_KEY_NAME]
    user_info['AllianceScore'] = user_data[user_id]['AllianceScore']
    return await get_user_details_by_info(user_info)


async def get_user_infos_from_tournament_data_by_name(user_name: str, user_data: dict) -> list:
    user_name_lower = user_name.lower()
    result = {user_id: user_info for (user_id, user_info) in user_data.items() if user_name_lower in user_info.get(user.USER_DESCRIPTION_PROPERTY_NAME, '').lower()}
    user_infos_current = await _get_user_infos(user_name)
    if user_infos_current:
        for user_info in user_infos_current.values():
            user_id = user_info[user.USER_KEY_NAME]
            if user_id in user_data:
                user_info = await __get_user_info_by_id(user_id)
                if user_id not in result:
                    result[user_id] = user_data[user_id]
                if result[user_id][user.USER_DESCRIPTION_PROPERTY_NAME] != user_info[user.USER_DESCRIPTION_PROPERTY_NAME]:
                    result[user_id]['CurrentName'] = user_info[user.USER_DESCRIPTION_PROPERTY_NAME]
    else:
        for tournament_user_id, tournament_user_info in result.items():
            user_info = await __get_user_info_by_id(tournament_user_id)
            if result[tournament_user_id][user.USER_DESCRIPTION_PROPERTY_NAME] != user_info[user.USER_DESCRIPTION_PROPERTY_NAME]:
                result[tournament_user_id]['CurrentName'] = user_info[user.USER_DESCRIPTION_PROPERTY_NAME]
    return list(result.values())


def __format_pvp_stats(wins: int, losses: int, draws: int) -> str:
    win_rate = _calculate_win_rate(wins, losses, draws)
    result = f'{wins}/{losses}/{draws} ({win_rate:0.2f}%)'
    return result


def __format_timestamp(timestamp: datetime, retrieved_at: datetime) -> str:
    retrieved_ago = util.get_formatted_timedelta(timestamp - retrieved_at, include_seconds=False)
    result = f'{util.format_excel_datetime(timestamp, include_seconds=False)} ({retrieved_ago})'
    return result


def __get_crew_borrowed_as_text(user_info: entity.EntityInfo, fleet_info: entity.EntityInfo) -> str:
    result = None
    if fleet_info:
        result = user_info.get('CrewReceived')
    return result


def __get_crew_donated_as_text(user_info: entity.EntityInfo, fleet_info: entity.EntityInfo) -> str:
    result = None
    if fleet_info:
        result = user_info.get('CrewDonated')
    return result


async def __get_fleet_info_by_user_info(user_info: entity.EntityInfo) -> entity.EntityInfo:
    result = {}
    fleet_id = user_info.get('AllianceId', '0')
    if fleet_id != '0':
        result = await fleet._get_fleet_info_by_id(fleet_id)
    return result


def __get_fleet_joined_at_as_text(user_info: entity.EntityInfo, fleet_info: entity.EntityInfo, retrieved_at: datetime) -> str:
    result = None
    if fleet_info:
        result = __get_timestamp_as_text(user_info, 'AllianceJoinDate', retrieved_at)
    return result


def __get_fleet_name_and_rank_as_text(user_info: entity.EntityInfo, fleet_info: entity.EntityInfo) -> str:
    result = None
    if fleet_info:
        fleet_name = fleet_info.get(fleet.FLEET_DESCRIPTION_PROPERTY_NAME, '')
        fleet_membership = user_info.get('AllianceMembership')
        fleet_rank = None
        if fleet_membership:
            fleet_rank = lookups.get_lookup_value_or_default(lookups.ALLIANCE_MEMBERSHIP, fleet_membership, default=fleet_membership)
        if fleet_name:
            result = fleet_name
            if fleet_rank:
                result += f' ({fleet_rank})'
        else:
            result = '<data error>'
    else:
        result = '<no fleet>'
    return result


async def __get_inspect_ship_path(user_id: int) -> str:
    access_token = await login.DEVICES.get_access_token()
    result = f'{INSPECT_SHIP_BASE_PATH}?userId={user_id}&accessToken={access_token}'
    return result


def __get_league_as_text(user_info: entity.EntityInfo) -> str:
    result = None
    trophies = user_info.get('Trophy')
    if trophies is not None:
        result = f'{_get_league_from_trophies(int(trophies))}'
        highest_trophies = user_info.get('HighestTrophy')
        if highest_trophies is not None:
            result += f' (highest: {_get_league_from_trophies(int(highest_trophies))})'
    return result


async def __get_level_as_text(ship_info: entity.EntityInfo):
    result = await ship.get_ship_level(ship_info)
    return result


def __get_pvp_attack_stats_as_text(user_info: entity.EntityInfo) -> str:
    result = None
    if all([field in user_info for field in ['PVPAttackDraws', 'PVPAttackLosses', 'PVPAttackWins']]):
        pvp_draws = int(user_info['PVPAttackDraws'])
        pvp_losses = int(user_info['PVPAttackLosses'])
        pvp_wins = int(user_info['PVPAttackWins'])
        result = __format_pvp_stats(pvp_wins, pvp_losses, pvp_draws)
    return result


def __get_pvp_defense_stats_as_text(user_info: entity.EntityInfo) -> str:
    result = None
    if all([field in user_info for field in ['PVPDefenceDraws', 'PVPDefenceLosses', 'PVPDefenceWins']]):
        defense_draws = int(user_info['PVPDefenceDraws'])
        defense_losses = int(user_info['PVPDefenceLosses'])
        defense_wins = int(user_info['PVPDefenceWins'])
        result = __format_pvp_stats(defense_wins, defense_losses, defense_draws)
    return result


def __get_ship_status_as_text(ship_info: entity.EntityInfo) -> str:
    result = None
    ship_status = ship_info.get('ShipStatus')
    if ship_status is not None:
        result = lookups.get_lookup_value_or_default(lookups.USER_STATUS, ship_status, default=ship_status)
    return result


def __get_stars_as_text(user_info: entity.EntityInfo, is_in_tourney_fleet: bool, attempts_left: int = None) -> str:
    result = None
    stars = user_info.get('AllianceScore')
    if is_in_tourney_fleet or (stars is not None and stars != '0'):
        result = stars
        if attempts_left is not None and is_in_tourney_fleet:
            result += f' ({attempts_left} attempts left)'
    return result


def __get_timestamp_as_text(user_info: entity.EntityInfo, field_name: str, retrieved_at: datetime) -> str:
    result = None
    timestamp = __parse_timestamp(user_info, field_name)
    if timestamp is not None:
        result = __format_timestamp(timestamp, retrieved_at)
    return result


def __get_trophies_as_text(user_info: entity.EntityInfo) -> str:
    result = None
    trophies = user_info.get('Trophy')
    if trophies is not None:
        result = f'{trophies}'
        highest_trophies = user_info.get('HighestTrophy')
        if highest_trophies is not None:
            result += f' (highest: {highest_trophies})'
    return result


def __get_tourney_battle_attempts(user_info: entity.EntityInfo, utc_now: datetime) -> int:
    attempts = user_info.get('TournamentBonusScore')
    if attempts:
        attempts = int(attempts)
        last_login_date = util.parse_pss_datetime(user_info.get('LastLoginDate'))
        if last_login_date:
            if last_login_date.day != utc_now.day:
                attempts = 0
    return attempts


async def __get_user_info_by_id(user_id: int) -> entity.EntityInfo:
    path = await __get_inspect_ship_path(user_id)
    inspect_ship_info_raw = await core.get_data_from_path(path)
    inspect_ship_info = core.convert_raw_xml_to_dict(inspect_ship_info_raw)
    result = inspect_ship_info['ShipService']['InspectShip']['User']
    return result


def __get_user_type_as_text(user_info: entity.EntityInfo) -> str:
    result = None
    user_type = user_info.get('UserType')
    if user_type is not None:
        result = lookups.get_lookup_value_or_default(lookups.USER_TYPE, user_type)
    return result


def __parse_timestamp(user_info: entity.EntityInfo, field_name: str) -> str:
    result = None
    timestamp = user_info.get(field_name)
    if timestamp is not None:
        result = util.parse_pss_datetime(timestamp)
    return result


def __get_user_name_as_text(user_info: entity.EntityInfo) -> str:
    result = None
    user_name = user_info.get('Name')
    if user_name is not None:
        result = user_name
        current_user_name = user_info.get('CurrentName')
        if current_user_name is not None:
            result += f' (now: {current_user_name})'
    return result












# ---------- User info ----------

async def get_user_details_by_name(user_name: str, as_embed: bool = settings.USE_EMBEDS) -> list:
    pss_assert.valid_parameter_value(user_name, 'user_name', min_length=0)

    user_infos = list((await _get_user_infos(user_name)).values())
    return user_infos


def get_user_search_details(user_info: dict) -> str:
    user_name = __get_user_name_as_text(user_info)
    user_trophies = user_info.get('Trophy', '?')
    user_stars = int(user_info.get('AllianceScore', '0'))

    details = []
    if user_info.get(fleet.FLEET_KEY_NAME, '0') != '0':
        fleet_name = user_info.get(fleet.FLEET_DESCRIPTION_PROPERTY_NAME, None)
        if fleet_name is not None:
            details.append(f'({fleet_name})')

    details.append(f'{emojis.trophy} {user_trophies}')
    if user_stars > 0:
        details.append(f'{emojis.star} {user_stars}')
    result = f'{user_name} ' + ' '.join(details)
    return result


async def _get_user_infos(user_name: str) -> dict:
    path = f'{SEARCH_USERS_BASE_PATH}{util.url_escape(user_name)}'
    user_data_raw = await core.get_data_from_path(path)
    user_infos = core.xmltree_to_dict3(user_data_raw)
    return user_infos










# ---------- Initialization ----------

async def init():
    league_data = await core.get_data_from_path(LEAGUE_BASE_PATH)
    league_infos = core.xmltree_to_dict3(league_data)
    for league_info in sorted(list(league_infos.values()), key=lambda league_info: int(league_info['MinTrophy'])):
        league_info['MinTrophy'] = int(league_info['MinTrophy'])
        league_info['MaxTrophy'] = int(league_info['MaxTrophy'])
        LEAGUE_INFOS_CACHE.append(league_info)