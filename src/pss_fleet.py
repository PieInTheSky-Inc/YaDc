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
import pss_entity as entity
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
    'Crew Donated',
    'Crew Borrowed',
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
    settings.EXCEL_COLUMN_FORMAT_NUMBER,
    settings.EXCEL_COLUMN_FORMAT_NUMBER,
    None,
    None
]








# ---------- Helper functions ----------

def __get_description_as_text(fleet_info: entity.EntityInfo) -> str:
    result = None
    description = fleet_info.get('AllianceDescription')
    if description is not None:
        result = description.strip()
    return result


def __get_division_name_and_ranking_as_text(fleet_info: entity.EntityInfo) -> str:
    result = None
    division_name = get_division_name_as_text(fleet_info)
    if division_name is not None and division_name != '-':
        result = division_name
        ranking = fleet_info.get('Ranking')
        if ranking is not None and ranking != '0':
            division_ranking = int(ranking) - lookups.DIVISION_CUTOFF_LOOKUP[division_name][0] + 1
            result += f' ({util.get_ranking(division_ranking)})'
    return result


def get_division_name_as_text(fleet_info: entity.EntityInfo) -> str:
    result = None
    if fleet_info:
        division_design_id = fleet_info.get('DivisionDesignId')
        if division_design_id is not None and division_design_id != '0':
            result = lookups.get_lookup_value_or_default(lookups.DIVISION_DESIGN_ID_TO_CHAR, division_design_id, default='-')
    return result


def __get_member_count(fleet_info: entity.EntityInfo, fleet_users_infos: entity.EntitiesData) -> str:
    result = None
    member_count = fleet_info.get('NumberOfMembers')
    if member_count is not None:
        result = member_count
    else:
        result = len(fleet_users_infos)
    return result


def __get_min_trophies(fleet_info: entity.EntityInfo) -> str:
    result = fleet_info.get('MinTrophyRequired')
    return result


def __get_name(fleet_info: entity.EntityInfo) -> str:
    result = None
    fleet_name = fleet_info.get(FLEET_DESCRIPTION_PROPERTY_NAME)
    if fleet_name is not None:
        result = fleet_name
        current_name = fleet_info.get('CurrentAllianceName')
        if current_name is not None:
            result += f' (now: {current_name})'
    return result


def __get_ranking_as_text(fleet_info: entity.EntityInfo) -> str:
    result = None
    ranking = fleet_info.get('Ranking')
    if ranking is not None and ranking != '0':
        result = util.get_ranking(ranking)
    return result


def __get_stars(fleet_info: entity.EntityInfo) -> str:
    result = None
    stars = fleet_info.get('Score')
    if stars is not None and stars != '0':
        result = stars
    return result


def __get_trophies(fleet_info: entity.EntityInfo, fleet_users_infos: entity.EntitiesData) -> str:
    result = None
    member_count = fleet_info.get('Trophy')
    if member_count is not None:
        result = member_count
    else:
        result = sum(int(user_info.get('Trophy', '0')) for user_info in fleet_users_infos.values())
    return result


def __get_type_as_text(fleet_info: entity.EntityInfo) -> str:
    result = None
    requires_approval = fleet_info.get('RequiresApproval')
    if requires_approval is not None:
        result = lookups.get_lookup_value_or_default(lookups.FLEET_TYPE_LOOKUP, requires_approval.lower() == 'true')
    return result



async def _get_fleet_details_by_info(fleet_info: dict, fleet_users_infos: dict, retrieved_at: datetime = None, is_past_data: bool = False) -> list:
    fleet_name = __get_name(fleet_info)
    description = __get_description_as_text(fleet_info)

    details = {
        'Ranking': __get_ranking_as_text(fleet_info),
        'Min trophies': __get_min_trophies(fleet_info),
        'Members': __get_member_count(fleet_info, fleet_users_infos),
        'Trophies': __get_trophies(fleet_info, fleet_users_infos),
        'Division': __get_division_name_and_ranking_as_text(fleet_info),
        'Stars': __get_stars(fleet_info),
        'Type': __get_type_as_text(fleet_info)
    }

    lines = [f'**```{fleet_name}```**```']
    if description is not None:
        lines.append(f'{description}``````')
    for detail_name, detail_value in details.items():
        if detail_value is not None:
            lines.append(f'{detail_name} - {detail_value}')

    if is_past_data:
        lines.append(f'```{util.get_historic_data_note(retrieved_at)}')
    else:
        lines[-1] += '```'

    return lines


async def _get_fleet_info_by_name(fleet_name: str, exact: bool = True):
    fleet_infos = await _get_fleet_infos_by_name(fleet_name)
    if exact:
        for fleet_info in fleet_infos.values():
            if fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME] == fleet_name:
                return fleet_info
    if fleet_infos:
        return fleet_infos[0]
    else:
        return None


async def _get_fleet_info_from_tournament_data(fleet_info: dict, fleet_users_infos: dict, fleet_data: dict) -> list:
    fleet_id = fleet_info[FLEET_KEY_NAME]
    if fleet_id in fleet_data.keys():
        fleet_info['Score'] = fleet_data[fleet_id]['Score']
    return await _get_fleet_details_by_info(fleet_info, fleet_users_infos)


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
            int(user_info.get('CrewDonated', '0')),
            int(user_info.get('CrewReceived', '0')),
            util.get_formatted_timedelta(logged_in_ago, include_relative_indicator=False),
            util.get_formatted_timedelta(joined_ago, include_relative_indicator=False)
        ]
        result.append(line)
    return result


async def get_full_fleet_info_as_text(fleet_info: dict, past_fleets_data: dict = None, past_users_data: dict = None, past_retrieved_at: datetime = None) -> (list, list):
    """Returns a list of lines for the post, as well as the paths to the spreadsheet created"""
    fleet_id = fleet_info[FLEET_KEY_NAME]
    fleet_name = fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
    is_past_data = past_fleets_data and past_users_data and past_retrieved_at

    if is_past_data:
        retrieved_at = past_retrieved_at
        if fleet_info.get('CurrentAllianceName') is None:
            current_fleet_info = await _get_fleet_info_by_id(fleet_id)
            if current_fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME] != fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]:
                fleet_info['CurrentAllianceName'] = current_fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
        fleet_users_infos = {user_id: user_info for user_id, user_info in past_users_data.items() if user_info.get(FLEET_KEY_NAME) == fleet_id}
    else:
        retrieved_at = util.get_utcnow()
        fleet_info = await _get_fleet_info_by_id(fleet_id)
        fleet_users_infos = await _get_fleet_users_by_id(fleet_id)

    post_content = await _get_fleet_details_by_info(fleet_info, fleet_users_infos, retrieved_at=retrieved_at, is_past_data=is_past_data)
    fleet_sheet_contents = _get_fleet_sheet_lines(fleet_users_infos, retrieved_at)
    fleet_sheet_file_name = excel.get_file_name(fleet_name, retrieved_at, consider_tourney=False)
    fleet_sheet_path_current = excel.create_xl_from_data(fleet_sheet_contents, fleet_name, retrieved_at, FLEET_SHEET_COLUMN_TYPES, file_name=fleet_sheet_file_name)
    file_paths = [fleet_sheet_path_current]

    return post_content, file_paths


async def _get_search_fleets_base_path(fleet_name: str) -> str:
    access_token = await login.DEVICES.get_access_token()
    result = f'AllianceService/SearchAlliances?accessToken={access_token}&skip=0&take=100&name={util.url_escape(fleet_name)}'
    return result


async def _get_get_alliance_base_path(fleet_id: str) -> str:
    access_token = await login.DEVICES.get_access_token()
    result = f'AllianceService/GetAlliance?accessToken={access_token}&allianceId={fleet_id}'
    return result


async def _get_search_fleet_users_base_path(fleet_id: str) -> str:
    access_token = await login.DEVICES.get_access_token()
    result = f'AllianceService/ListUsers?accessToken={access_token}&skip=0&take=100&allianceId={fleet_id}'
    return result










# ---------- Alliance info ----------

async def get_fleet_infos_by_name(fleet_name: str, as_embed: bool = settings.USE_EMBEDS) -> list:
    pss_assert.valid_parameter_value(fleet_name, 'fleet_name', min_length=0)

    fleet_infos = list((await _get_fleet_infos_by_name(fleet_name)).values())
    return fleet_infos


def get_fleet_search_details(fleet_info: dict) -> str:
    fleet_name = fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
    fleet_name_current = fleet_info.get('CurrentAllianceName', None)
    if fleet_name_current is not None:
        fleet_name += f' (now: {fleet_name_current})'

    details = []
    fleet_trophies = fleet_info.get('Trophy', None)
    fleet_stars = int(fleet_info.get('Score', '0'))
    if fleet_trophies is not None:
        details.append(f'{emojis.trophy} {fleet_trophies}')
    if fleet_stars > 0:
        details.append(f'{emojis.star} {fleet_stars}')
    result = (f'{fleet_name} ' + ' '.join(details)).strip()
    return result


async def _get_fleet_info_by_id(fleet_id: str) -> dict:
    path = await _get_get_alliance_base_path(fleet_id)
    fleet_data_raw = await core.get_data_from_path(path)
    fleet_info = core.xmltree_to_dict3(fleet_data_raw)
    return fleet_info


async def _get_fleet_infos_by_name(fleet_name: str) -> dict:
    path = await _get_search_fleets_base_path(fleet_name)
    fleet_data_raw = await core.get_data_from_path(path)
    fleet_infos = core.xmltree_to_dict3(fleet_data_raw)
    return fleet_infos


async def _get_fleet_users_by_id(alliance_id: str) -> dict:
    path = await _get_search_fleet_users_base_path(alliance_id)
    fleet_users_data_raw = await core.get_data_from_path(path)
    fleet_users_infos = core.xmltree_to_dict3(fleet_users_data_raw)
    return fleet_users_infos


async def get_fleet_users_by_info(fleet_info: dict) -> dict:
    fleet_id = fleet_info[FLEET_KEY_NAME]
    return await _get_fleet_users_by_id(fleet_id)










# ---------- Stars ----------

async def get_fleet_infos_from_tourney_data_by_name(fleet_name: str, fleet_data: dict) -> list:
    fleet_name_lower = fleet_name.lower()
    result = {fleet_id: fleet_info for (fleet_id, fleet_info) in fleet_data.items() if fleet_name_lower in fleet_info.get(fleet.FLEET_DESCRIPTION_PROPERTY_NAME, '').lower()}
    fleet_infos_current = await _get_fleet_infos_by_name(fleet_name)
    for fleet_info in fleet_infos_current.values():
        fleet_id = fleet_info[fleet.FLEET_KEY_NAME]
        if fleet_id in fleet_data:
            if fleet_id not in result:
                result[fleet_id] = fleet_data[fleet_id]
            if result[fleet_id][fleet.FLEET_DESCRIPTION_PROPERTY_NAME] != fleet_info[fleet.FLEET_DESCRIPTION_PROPERTY_NAME]:
                result[fleet_id]['CurrentAllianceName'] = fleet_info[fleet.FLEET_DESCRIPTION_PROPERTY_NAME]
    return list(result.values())


def get_fleet_users_stars_from_info(fleet_info: dict, fleet_users_infos: dict, retrieved_date: datetime = None) -> list:
    fleet_name = fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
    division = lookups.DIVISION_DESIGN_ID_TO_CHAR[fleet_info['DivisionDesignId']]

    fleet_users_infos = util.sort_entities_by(list(fleet_users_infos.values()), [('AllianceScore', int, True), (user.USER_KEY_NAME, int, False)])
    fleet_users_infos_count = len(fleet_users_infos)

    lines = [f'**{fleet_name} member stars (division {division})**']
    for i, user_info in enumerate(fleet_users_infos, 1):
        stars = user_info['AllianceScore']
        user_name = util.escape_markdown(user_info[user.USER_DESCRIPTION_PROPERTY_NAME])
        if i < fleet_users_infos_count:
            difference = int(user_info['AllianceScore']) - int(fleet_users_infos[i]['AllianceScore'])
        else:
            difference = 0
        lines.append(f'**{i}.** {stars} (+{difference}) {emojis.star} {user_name}')

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

#if __name__ == '__main__':
#    test_fleets = ['Fallen An']
#    for fleet_name in test_fleets:
#        os.system('clear')
#        is_tourney_running = tourney.is_tourney_running()
#        fleet_infos = await get_fleet_details_by_name(fleet_name)
#        lines = [get_fleet_search_details(fleet_info) for fleet_info in fleet_infos]
#        for line in lines:
#            print(line)
