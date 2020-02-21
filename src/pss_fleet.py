#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime
import discord
import os
import urllib.parse

import emojis
import excel
import pss_assert
import pss_core as core
import pss_fleet as fleet
import pss_login as login
import pss_lookups as lookups
import pss_tournament as tourney
import pss_user as user
import settings
import utility as util


# ---------- Constants ----------

FLEET_KEY_NAME = 'AllianceId'
FLEET_DESCRIPTION_PROPERTY_NAME = 'AllianceName'

FLEET_SHEET_COLUMN_NAMES = [
    'Timestamp',
    'Fleet',
    'Player name',
    'Rank',
    'Last Login Date',
    'Trophies',
    'Stars',
    'Join Date',
    'Logged in ago',
    'Joined ago'
]
FLEET_SHEET_COLUMN_TYPES = [
    settings.EXCEL_COLUMN_FORMAT_DATETIME,
    None,
    None,
    None,
    settings.EXCEL_COLUMN_FORMAT_DATETIME,
    settings.EXCEL_COLUMN_FORMAT_NUMBER,
    settings.EXCEL_COLUMN_FORMAT_NUMBER,
    settings.EXCEL_COLUMN_FORMAT_DATETIME,
    None,
    None
]








# ---------- Helper functions ----------

def _get_fleet_details_by_info(fleet_info: dict, fleet_users_infos: dict) -> list:
    fleet_info = _get_fleet_info_by_id(fleet_info[FLEET_KEY_NAME])

    division_design_id = fleet_info['DivisionDesignId']
    fleet_name = fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
    fleet_description = fleet_info['AllianceDescription'].strip()
    member_count = int(fleet_info['NumberOfMembers'])
    min_trophy_required = fleet_info['MinTrophyRequired']
    ranking = util.get_ranking(fleet_info['Ranking'])
    requires_approval = fleet_info['RequiresApproval'].lower() == 'true'
    stars = int(fleet_info['Score'])
    trophies = sum([int(user_info['Trophy']) for user_info in fleet_users_infos.values()])

    if requires_approval:
        fleet_type = 'Private'
    else:
        fleet_type = 'Public'
    division = lookups.DIVISION_DESIGN_ID_TO_CHAR[division_design_id]

    lines = [f'**```{fleet_name}```**```']
    if fleet_description:
        lines.append(f'{fleet_description}``````')
    lines.append(f'Ranking - {ranking}')
    lines.append(f'Min trophies - {min_trophy_required}')
    lines.append(f'Members - {member_count}')
    lines.append(f'Trophies - {util.get_reduced_number_compact(trophies)}')
    if division != '-':
        lines.append(f'Division - {division}')
        lines.append(f'Stars - {util.get_reduced_number_compact(stars)}')
    lines.append(f'Type - {fleet_type}')

    lines[-1] += '```'

    return lines


def _get_fleet_info_by_name(fleet_name: str, exact: bool = True):
    fleet_infos = _get_fleet_infos_by_name(fleet_name)
    if exact:
        for fleet_info in fleet_infos.values():
            if fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME] == fleet_name:
                return fleet_info
    if fleet_infos:
        return fleet_infos[0]
    else:
        return None


def _get_fleet_info_from_tournament_data(fleet_info: dict, fleet_users_infos: dict, fleet_data: dict) -> list:
    fleet_id = fleet_info[FLEET_KEY_NAME]
    if fleet_id in fleet_data.keys():
        fleet_info['Score'] = fleet_data[fleet_id]['Score']
    return _get_fleet_details_by_info(fleet_info, fleet_users_infos)


def _get_fleet_sheet_lines(fleet_users_infos: dict, retrieval_date: datetime, fleet_name: str = None) -> list:
    result = [FLEET_SHEET_COLUMN_NAMES]

    for user_info in fleet_users_infos.values():
        logged_in_ago = retrieval_date - util.parse_pss_datetime(user_info['LastLoginDate'])
        joined_ago = retrieval_date - util.parse_pss_datetime(user_info['AllianceJoinDate'])
        if fleet_name is None and FLEET_DESCRIPTION_PROPERTY_NAME in user_info.keys():
            fleet_name = user_info[FLEET_DESCRIPTION_PROPERTY_NAME]
        line = [
            util.format_excel_datetime(retrieval_date),
            fleet_name,
            user_info[user.USER_DESCRIPTION_PROPERTY_NAME],
            user_info['AllianceMembership'],
            util.convert_pss_timestamp_to_excel(user_info['LastLoginDate']),
            int(user_info['Trophy']),
            int(user_info['AllianceScore']),
            util.convert_pss_timestamp_to_excel(user_info['AllianceJoinDate']),
            util.get_formatted_timedelta(logged_in_ago, include_relative_indicator=False),
            util.get_formatted_timedelta(joined_ago, include_relative_indicator=False)
        ]
        result.append(line)
    return result


def get_full_fleet_info_as_text(fleet_info: dict, fleet_data: dict = None, user_data: dict = None, data_date: datetime = None) -> (list, list):
    """Returns a list of lines for the post, as well as the path to the spreadsheet created"""
    fleet_name = fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
    fleet_id = fleet_info[FLEET_KEY_NAME]
    retrieval_date = util.get_utcnow()
    fleet_users_infos = _get_fleet_users_by_id(fleet_id)
    if fleet_users_infos:
        fleet_info = list(fleet_users_infos.values())[0]['Alliance']
    else:
        fleet_info = _get_fleet_info_by_name(fleet_name)

    post_content = _get_fleet_details_by_info(fleet_info, fleet_users_infos)
    fleet_sheet_contents = _get_fleet_sheet_lines(fleet_users_infos, retrieval_date)
    fleet_sheet_path_current = excel.create_xl_from_data(fleet_sheet_contents, fleet_name, retrieval_date, FLEET_SHEET_COLUMN_TYPES)
    file_paths = [fleet_sheet_path_current]

    if fleet_data and fleet_id in fleet_data.keys() and user_data and data_date:
        fleet_info = fleet_data[fleet_id]
        fleet_name = fleet_info[fleet.FLEET_DESCRIPTION_PROPERTY_NAME]
        fleet_users_infos = dict({user_id: user_info for user_id, user_info in user_data.items() if user_info['AllianceId'] == fleet_id})
        fleet_sheet_contents = _get_fleet_sheet_lines(fleet_users_infos, data_date, fleet_name)
        file_name = f'{fleet_name}_tournament-{data_date.year}-{util.get_month_short_name(data_date).lower()}.xlsx'
        fleet_sheet_path_past = excel.create_xl_from_data(fleet_sheet_contents, fleet_name, data_date, FLEET_SHEET_COLUMN_TYPES, file_name=file_name)
        file_paths.append(fleet_sheet_path_past)

    return post_content, file_paths


def _get_search_fleets_base_path(fleet_name: str) -> str:
    access_token = login.DEVICES.get_access_token()
    result = f'AllianceService/SearchAlliances?accessToken={access_token}&skip=0&take=100&name={util.url_escape(fleet_name)}'
    return result


def _get_get_alliance_base_path(fleet_id: str) -> str:
    access_token = login.DEVICES.get_access_token()
    result = f'AllianceService/GetAlliance?accessToken={access_token}&allianceId={fleet_id}'
    return result


def _get_search_fleet_users_base_path(fleet_id: str) -> str:
    access_token = login.DEVICES.get_access_token()
    result = f'AllianceService/ListUsers?accessToken={access_token}&skip=0&take=100&allianceId={fleet_id}'
    return result










# ---------- Alliance info ----------

def get_fleet_details_by_name(fleet_name: str, as_embed: bool = settings.USE_EMBEDS) -> list:
    pss_assert.valid_parameter_value(fleet_name, 'fleet_name', min_length=0)

    fleet_infos = list(_get_fleet_infos_by_name(fleet_name).values())
    return fleet_infos


def get_fleet_search_details(fleet_info: dict) -> str:
    fleet_name = fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
    fleet_trophies = fleet_info['Trophy']
    fleet_stars = fleet_info['Score']
    fleet_division = int(fleet_info['DivisionDesignId'])
    trophies = f'  {emojis.trophy} {fleet_trophies}'
    if fleet_division > 0:
        stars = f'  {emojis.star} {fleet_stars}'
    else:
        stars = ''
    result = f'{fleet_name}{trophies}{stars}'
    return result


def _get_fleet_info_by_id(fleet_id: str) -> dict:
    path = _get_get_alliance_base_path(fleet_id)
    fleet_data_raw = core.get_data_from_path(path)
    fleet_info = core.xmltree_to_dict3(fleet_data_raw)
    return fleet_info


def _get_fleet_infos_by_name(fleet_name: str) -> dict:
    path = _get_search_fleets_base_path(fleet_name)
    fleet_data_raw = core.get_data_from_path(path)
    fleet_infos = core.xmltree_to_dict3(fleet_data_raw)
    return fleet_infos


def _get_fleet_users_by_id(alliance_id: str) -> dict:
    path = _get_search_fleet_users_base_path(alliance_id)
    fleet_users_data_raw = core.get_data_from_path(path)
    fleet_users_infos = core.xmltree_to_dict3(fleet_users_data_raw)
    return fleet_users_infos


def get_fleet_users_by_info(fleet_info: dict) -> dict:
    fleet_id = fleet_info[FLEET_KEY_NAME]
    return _get_fleet_users_by_id(fleet_id)










# ---------- Stars ----------

def get_fleet_users_stars_from_info(fleet_info: dict, fleet_users_infos: dict, retrieved_date: datetime = None) -> list:
    fleet_name = fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
    division = lookups.DIVISION_DESIGN_ID_TO_CHAR[fleet_info['DivisionDesignId']]

    fleet_users_infos = util.sort_entities_by(list(fleet_users_infos.values()), [('AllianceScore', int, True), (user.USER_KEY_NAME, int, False)])

    lines = [f'**{fleet_name} member stars (division {division})**']
    for i, user_info in enumerate(fleet_users_infos, 1):
        stars = user_info['AllianceScore']
        user_name = user_info[user.USER_DESCRIPTION_PROPERTY_NAME]
        if util.should_escape_entity_name(user_name):
            user_name = f'`{user_name}`'
        lines.append(f'**{i}.** {stars} {emojis.star} {user_name}')

    if retrieved_date is not None:
        lines.append(util.get_historic_data_note(retrieved_date))

    return lines


def get_fleet_users_stars_from_tournament_data(fleet_info: dict, fleet_data: dict, user_data: dict, retrieved_date: datetime) -> list:
    fleet_id = fleet_info[FLEET_KEY_NAME]
    fleet_users_infos = {}
    if fleet_id in fleet_data.keys():
        fleet_info['DivisionDesignId'] = fleet_data[fleet_id]['DivisionDesignId']
        fleet_users_infos = dict({user_info[user.USER_KEY_NAME]: user_info for user_info in user_data.values() if user_info[FLEET_KEY_NAME] == fleet_id})
    return get_fleet_users_stars_from_info(fleet_info, fleet_users_infos, retrieved_date=retrieved_date)












# ---------- Testing ----------

if __name__ == '__main__':
    test_fleets = ['Fallen An']
    for fleet_name in test_fleets:
        os.system('clear')
        is_tourney_running = tourney.is_tourney_running()
        fleet_infos = get_fleet_details_by_name(fleet_name)
        lines = [get_fleet_search_details(fleet_info) for fleet_info in fleet_infos]
        for line in lines:
            print(line)
