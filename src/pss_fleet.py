import calendar
from datetime import datetime
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from discord import ApplicationContext
from discord import Embed
from discord import Interaction
from discord.utils import escape_markdown
from discord.ext.commands import Context


from . import emojis
from . import excel
from .gdrive import TourneyData
from .pagination import SelectView
from . import pss_assert
from . import pss_core as core
from . import pss_entity as entity
from .pss_exception import NotFound
from . import pss_fleet as fleet
from . import pss_login as login
from . import pss_lookups as lookups
from . import pss_sprites as sprites
from . import pss_top as top
from . import pss_user as user
from . import settings
from .typehints import EntitiesData, EntityInfo
from . import utils


# ---------- Constants ----------

FLEET_DESCRIPTION_PROPERTY_NAME: str = 'AllianceName'
FLEET_KEY_NAME: str = 'AllianceId'

FLEET_SHEET_COLUMN_DEFAULT_HEADERS: List[str] = [
    'Timestamp',
    'Fleet',
    'Player name',
    'Rank',
    'Last Login Date',
    'Trophies',
    'Max Trophies',
    'Stars',
    'Join Date',
    'Crew Donated',
    'Crew Borrowed',
    'Logged in ago',
    'Joined ago',
]
FLEET_SHEET_COLUMN_FORMATS: Dict[str, Optional[str]] = {
    'Timestamp': settings.EXCEL_COLUMN_FORMAT_DATETIME,
    'Fleet': settings.EXCEL_COLUMN_FORMAT_TEXT,
    'Player name': settings.EXCEL_COLUMN_FORMAT_TEXT,
    'Rank': None,
    'Last Login Date': settings.EXCEL_COLUMN_FORMAT_DATETIME,
    'Trophies': settings.EXCEL_COLUMN_FORMAT_NUMBER,
    'Max Trophies': settings.EXCEL_COLUMN_FORMAT_NUMBER,
    'Stars': settings.EXCEL_COLUMN_FORMAT_NUMBER,
    'Join Date': settings.EXCEL_COLUMN_FORMAT_DATETIME,
    'Crew Donated': settings.EXCEL_COLUMN_FORMAT_NUMBER,
    'Crew Borrowed': settings.EXCEL_COLUMN_FORMAT_NUMBER,
    'Logged in ago': None,
    'Joined ago': None,
    'Tournament attempts left': settings.EXCEL_COLUMN_FORMAT_NUMBER,
    'Star value': settings.EXCEL_COLUMN_FORMAT_NUMBER,
}





# ---------- Fleet info ----------

def create_fleets_sheet_csv(fleet_users_data: EntitiesData, retrieved_at: datetime, file_name: str) -> str:
    start = time.perf_counter()
    fleet_sheet_contents = __get_fleet_sheet_lines(fleet_users_data, retrieved_at, include_player_id=True, include_fleet_id=True, include_division_name=True, include_pvp_stats=True)
    time1 = time.perf_counter() - start
    print(f'Creating the fleet users lines took {time1:.2f} seconds.')

    start = time.perf_counter()
    fleet_sheet_path = excel.create_csv_from_data(fleet_sheet_contents, None, None, file_name=file_name)
    time2 = time.perf_counter() - start
    print(f'Creating the csv file took {time2:.2f} seconds ({(time1+time2):.2f} seconds in total).')
    return fleet_sheet_path


async def get_current_tournament_fleet_infos_by_name(fleet_name: str) -> List[EntityInfo]:
    pss_assert.valid_parameter_value(fleet_name, 'fleet_name', min_length=0)

    fleet_infos = list((await __get_current_tournament_fleets_data_by_name(fleet_name)).values())
    return fleet_infos


async def get_fleet_infos_from_tourney_data_by_name(fleet_name: str, fleet_data: EntitiesData) -> List[EntityInfo]:
    fleet_name_lower = fleet_name.lower()
    result = {fleet_id: fleet_info for (fleet_id, fleet_info) in fleet_data.items() if fleet_name_lower in fleet_info.get(fleet.FLEET_DESCRIPTION_PROPERTY_NAME, '').lower()}
    fleet_infos_current = await __get_fleets_data_by_name(fleet_name)
    for fleet_info in fleet_infos_current.values():
        fleet_id = fleet_info[fleet.FLEET_KEY_NAME]
        if fleet_id in fleet_data:
            if fleet_id not in result:
                result[fleet_id] = fleet_data[fleet_id]
            if result[fleet_id][fleet.FLEET_DESCRIPTION_PROPERTY_NAME] != fleet_info[fleet.FLEET_DESCRIPTION_PROPERTY_NAME]:
                result[fleet_id]['CurrentAllianceName'] = fleet_info[fleet.FLEET_DESCRIPTION_PROPERTY_NAME]
    return list(result.values())


async def get_fleet_infos_by_name(fleet_name: str) -> List[EntityInfo]:
    pss_assert.valid_parameter_value(fleet_name, 'fleet_name', min_length=0)

    fleet_infos = list((await __get_fleets_data_by_name(fleet_name)).values())
    return fleet_infos


def get_fleet_search_details(fleet_info: EntityInfo) -> str:
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


async def get_fleet_users_data_by_fleet_info(fleet_info: EntityInfo) -> EntitiesData:
    fleet_id = fleet_info[FLEET_KEY_NAME]
    result = await __get_fleet_users_data_by_fleet_id(fleet_id)
    return result


async def get_fleets_data_by_id(fleet_id: str) -> EntitiesData:
    path = await __get_get_alliance_base_path(fleet_id)
    fleet_data_raw = await core.get_data_from_path(path)
    result = utils.convert.xmltree_to_dict3(fleet_data_raw)
    return result


async def get_full_fleet_info_as_text(ctx: Context, fleet_info: EntityInfo, max_tourney_battle_attempts: int = None, past_fleets_data: EntitiesData = None, past_users_data: EntitiesData = None, past_retrieved_at: datetime = None, yesterday_tourney_data: TourneyData = None, as_embed: bool = settings.USE_EMBEDS) -> Tuple[Union[List[Embed], List[str]], List[str]]:
    """Returns a list of lines for the post, as well as the paths to the spreadsheet created"""
    fleet_id = fleet_info[FLEET_KEY_NAME]
    fleet_name = fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
    is_past_data = past_fleets_data and past_users_data and past_retrieved_at

    if is_past_data:
        retrieved_at = past_retrieved_at
        if fleet_info.get('CurrentAllianceName') is None:
            current_fleet_info = await get_fleets_data_by_id(fleet_id)
            if current_fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME] != fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]:
                fleet_info['CurrentAllianceName'] = current_fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
        fleet_users_data = {user_id: user_info for user_id, user_info in past_users_data.items() if user_info.get(FLEET_KEY_NAME) == fleet_id}
    else:
        retrieved_at = utils.get_utc_now()
        fleet_info = await get_fleets_data_by_id(fleet_id)
        fleet_users_data = await __get_fleet_users_data_by_fleet_id(fleet_id, yesterday_tourney_data)

    post_content = await __get_fleet_details_by_info(ctx, fleet_info, fleet_users_data, max_tourney_battle_attempts=max_tourney_battle_attempts, retrieved_at=retrieved_at, is_past_data=is_past_data, as_embed=as_embed)
    fleet_sheet_file_name = excel.get_file_name(fleet_name, retrieved_at, excel.FILE_ENDING.XL, consider_tourney=False)
    file_path = __create_fleet_sheet_xl(fleet_users_data, retrieved_at, fleet_sheet_file_name, max_tourney_battle_attempts=max_tourney_battle_attempts)
    file_paths = []
    if file_path:
        file_paths.append(file_path)

    return post_content, file_paths


async def __get_current_tournament_fleets_data_by_name(fleet_name: str) -> EntitiesData:
    fleet_name = fleet_name.lower()
    fleet_data_raw = await core.get_data_from_path('AllianceService/ListAlliancesWithDivision')
    result = utils.convert.xmltree_to_dict3(fleet_data_raw)
    result = {key: value for key, value in result.items() if fleet_name in value[FLEET_DESCRIPTION_PROPERTY_NAME].lower()}
    return result


async def __get_fleets_data_by_name(fleet_name: str) -> EntitiesData:
    path = await __get_search_fleets_base_path(fleet_name)
    fleet_data_raw = await core.get_data_from_path(path)
    result = utils.convert.xmltree_to_dict3(fleet_data_raw)
    return result


async def __get_fleet_users_data_by_fleet_id(alliance_id: str, yesterday_tourney_data: TourneyData = None) -> EntitiesData:
    path = await __get_search_fleet_users_base_path(alliance_id)
    fleet_users_data_raw = await core.get_data_from_path(path)
    result = utils.convert.xmltree_to_dict3(fleet_users_data_raw)
    if yesterday_tourney_data:
        for user_id, user_info in result.items():
            user_info['YesterdayAllianceScore'] = int(yesterday_tourney_data.users.get(user_id, {}).get('AllianceScore', 0))
    return result





# ---------- Stars info ----------

async def get_fleet_users_stars_from_info(ctx: Context, fleet_info: EntityInfo, fleet_users_infos: EntitiesData, max_tourney_battle_attempts: int, retrieved_at: datetime = None, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    utc_now = utils.get_utc_now()
    fleet_name = fleet_info[FLEET_DESCRIPTION_PROPERTY_NAME]
    division = lookups.DIVISION_DESIGN_ID_TO_CHAR[fleet_info[top.DIVISION_DESIGN_KEY_NAME]]

    fleet_users_infos = entity.sort_entities_by(list(fleet_users_infos.values()), [('AllianceScore', int, True), (user.USER_KEY_NAME, int, False)])
    fleet_users_infos_count = len(fleet_users_infos)

    title = f'{fleet_name} member stars (division {division})'
    display_attempts = False
    lines = []
    for i, user_info in enumerate(fleet_users_infos, 1):
        stars = user_info['AllianceScore']
        user_name = escape_markdown(user_info[user.USER_DESCRIPTION_PROPERTY_NAME])
        fleet_membership = user_info.get('AllianceMembership')
        if i < fleet_users_infos_count:
            difference = int(user_info['AllianceScore']) - int(fleet_users_infos[i]['AllianceScore'])
        else:
            difference = 0
        user_rank = lookups.get_lookup_value_or_default(lookups.ALLIANCE_MEMBERSHIP, fleet_membership, default=fleet_membership)
        attempts_left = ''
        attempts = user.__get_tourney_battle_attempts(user_info, retrieved_at or utc_now)
        if attempts is not None and max_tourney_battle_attempts:
            display_attempts = True
            attempts_left = f'{max_tourney_battle_attempts - attempts}, '
        lines.append(f'**{i}.** {stars} (+{difference}) {emojis.star} {user_name} ({attempts_left}{user_rank})')

    properties_attempts = 'Attempts left, ' if display_attempts else ''
    properties_text = f'Properties displayed: Rank. Stars (Difference to next) Player name ({properties_attempts}Fleet rank)'
    if retrieved_at is not None:
        footer_text = utils.datetime.get_historic_data_note(retrieved_at)
    else:
        footer_text = None

    if as_embed:
        if footer_text:
            footer_text = '\n'.join((properties_text, footer_text))
        else:
            footer_text = properties_text
        colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
        icon_url = await sprites.get_download_sprite_link(fleet_info.get('AllianceSpriteId'))
        result = utils.discord.create_basic_embeds_from_description(title, description=lines, colour=colour, icon_url=icon_url, footer=footer_text)
        return result
    else:
        lines.insert(0, f'**{title}**')
        lines.append(f'_{properties_text}_')
        if footer_text:
            lines.append(f'```{footer_text}```')
        return lines


async def get_fleet_users_stars_from_tournament_data(ctx, fleet_info: EntityInfo, fleet_data: EntitiesData, user_data: EntitiesData, retrieved_date: datetime, max_tourney_battle_attempts: Optional[int] = None, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    fleet_id = fleet_info[FLEET_KEY_NAME]
    fleet_users_infos = {}
    if fleet_id in fleet_data.keys():
        fleet_info[top.DIVISION_DESIGN_KEY_NAME] = fleet_data[fleet_id][top.DIVISION_DESIGN_KEY_NAME]
        fleet_users_infos = dict({user_info[user.USER_KEY_NAME]: user_info for user_info in user_data.values() if user_info[FLEET_KEY_NAME] == fleet_id})
    return await get_fleet_users_stars_from_info(ctx, fleet_info, fleet_users_infos, max_tourney_battle_attempts, retrieved_at=retrieved_date, as_embed=as_embed)





# ---------- Transformation functions ----------

def __get_description_as_text(fleet_info: EntityInfo, fleet_users_data: EntitiesData, **kwargs) -> Optional[str]:
    result = None
    description = fleet_info.get('AllianceDescription')
    if description is not None:
        result = description.strip()
    return result


def __get_division_name_and_ranking(fleet_info: EntityInfo, fleet_users_data: EntitiesData, **kwargs) -> Optional[str]:
    result = None
    division_name = get_division_name(fleet_info.get(top.DIVISION_DESIGN_KEY_NAME))
    if division_name is not None and division_name != '-':
        result = division_name
        ranking = fleet_info.get('Ranking')
        if ranking is not None and ranking != '0':
            division_ranking = int(ranking) - lookups.DIVISION_CUTOFF_LOOKUP[division_name][0] + 1
            result += f' ({utils.format.ranking(division_ranking)})'
    return result


def __get_historic_data_note(fleet_info: EntityInfo, fleet_users_data: EntitiesData, max_tourney_battle_attempts: int = None, retrieved_at: datetime = None, is_past_data: bool = None, **kwargs) -> Optional[str]:
    if is_past_data:
        result = utils.datetime.get_historic_data_note(retrieved_at)
    else:
        result = None
    return result


def __get_member_count(fleet_info: EntityInfo, fleet_users_data: EntitiesData, **kwargs) -> Optional[str]:
    result = None
    member_count = fleet_info.get('NumberOfMembers')
    if member_count is not None:
        result = member_count
    else:
        result = len(fleet_users_data)
    return result


def __get_min_trophies(fleet_info: EntityInfo, fleet_users_data: EntitiesData, **kwargs) -> Optional[str]:
    result = fleet_info.get('MinTrophyRequired')
    return result


def __get_name(fleet_info: EntityInfo, fleet_users_data: EntitiesData, **kwargs) -> Optional[str]:
    result = None
    fleet_name = fleet_info.get(FLEET_DESCRIPTION_PROPERTY_NAME)
    if fleet_name is not None:
        result = fleet_name
        current_name = fleet_info.get('CurrentAllianceName')
        if current_name is not None:
            result += f' (now: {current_name})'
    return result


def __get_ranking(fleet_info: EntityInfo, fleet_users_data: EntitiesData, **kwargs) -> Optional[str]:
    result = None
    ranking = fleet_info.get('Ranking')
    if ranking is not None and ranking != '0':
        result = utils.format.ranking(ranking)
    return result


def __get_stars(fleet_info: EntityInfo, fleet_users_data: EntitiesData, max_tourney_battle_attempts: int = None, retrieved_at: datetime = None, **kwargs) -> Optional[str]:
    result = None
    stars = fleet_info.get('Score')
    if stars is not None and stars != '0':
        result = stars
        if max_tourney_battle_attempts is not None and fleet_users_data and retrieved_at:
            try:
                attempts_left = sum([max_tourney_battle_attempts - user.__get_tourney_battle_attempts(user_info, retrieved_at) for user_info in fleet_users_data.values()])
                result += f' ({attempts_left} attempts left)'
            except TypeError:
                pass
    return result


def __get_trophies(fleet_info: EntityInfo, fleet_users_data: EntitiesData, **kwargs) -> Optional[str]:
    result = None
    trophy = fleet_info.get('Trophy')
    if trophy is not None:
        result = trophy
    else:
        result = sum(int(user_info.get('Trophy', '0')) for user_info in fleet_users_data.values())
    return result


def __get_type(fleet_info: EntityInfo, fleet_users_data: EntitiesData, **kwargs) -> Optional[str]:
    result = None
    requires_approval = fleet_info.get('RequiresApproval')
    if requires_approval is not None:
        result = lookups.get_lookup_value_or_default(lookups.FLEET_TYPE_LOOKUP, requires_approval.lower() == 'true')
    return result





# ---------- Helper functions ----------

async def find_fleet(ctx: ApplicationContext, fleet_name: str) -> Tuple[EntityInfo, Interaction]:
    response = await utils.discord.respond_with_output(ctx, ['Searching fleet...'])
    fleet_infos = await get_fleet_infos_by_name(fleet_name)
    if fleet_infos:
        fleet_info = None
        if len(fleet_infos) == 1:
            fleet_info = fleet_infos[0]
        else:
            fleet_infos.sort(key=lambda fleet: fleet[FLEET_DESCRIPTION_PROPERTY_NAME])
            fleet_infos = fleet_infos[:25]

            options = {fleet_info[FLEET_KEY_NAME]: (get_fleet_search_details(fleet_info), fleet_info) for fleet_info in fleet_infos}
            view = SelectView(ctx, 'Please select a fleet.', options)
            fleet_info = await view.wait_for_selection(response)

        return fleet_info, response
    else:
        raise NotFound(f'Could not find a fleet named `{fleet_name}`.')


async def find_tournament_fleet(ctx: ApplicationContext, fleet_name: str, tourney_data) -> Tuple[EntityInfo, Interaction]:
    response = await utils.discord.edit_original_response(ctx, ctx.interaction, ['Searching fleet...'])
    fleet_infos = await get_fleet_infos_from_tourney_data_by_name(fleet_name, tourney_data.fleets)
    if fleet_infos:
        fleet_info = None
        if len(fleet_infos) == 1:
            fleet_info = fleet_infos[0]
        else:
            fleet_infos.sort(key=lambda fleet: fleet[FLEET_DESCRIPTION_PROPERTY_NAME])
            fleet_infos = fleet_infos[:25]

            options = {fleet_info[FLEET_KEY_NAME]: (get_fleet_search_details(fleet_info), fleet_info) for fleet_info in fleet_infos}
            view = SelectView(ctx, 'Please select a fleet.', options)
            fleet_info = await view.wait_for_selection(ctx.interaction)

        return fleet_info, ctx.interaction
    else:
        raise NotFound(f'Could not find a fleet named `{fleet_name}` that participated in the {tourney_data.year} {calendar.month_name[int(tourney_data.month)]} tournament.')


def get_division_name(division_design_id: time.strftime) -> str:
    result = None
    if division_design_id is not None and division_design_id != '0':
        result = lookups.get_lookup_value_or_default(lookups.DIVISION_DESIGN_ID_TO_CHAR, division_design_id, default='-')
    return result


def is_tournament_fleet(fleet_info: EntityInfo) -> bool:
    try:
        division_design_id = int(fleet_info.get(top.DIVISION_DESIGN_KEY_NAME, '0'))
        return division_design_id > 0
    except:
        return False


def __create_fleet_sheet_xl(fleet_users_data: EntitiesData, retrieved_at: datetime, file_name: str, max_tourney_battle_attempts: int = None, include_player_id: bool = False, include_fleet_id: bool = False, sort_data: bool = True) -> str:
    start = time.perf_counter()
    fleet_sheet_lines = __get_fleet_sheet_lines(fleet_users_data, retrieved_at, max_tourney_battle_attempts=max_tourney_battle_attempts, include_player_id=include_player_id, include_fleet_id=include_fleet_id, sort_lines=sort_data)
    fleet_sheet_data = __get_fleet_sheet_data_from_lines(fleet_sheet_lines)
    time1 = time.perf_counter() - start
    print(f'Creating the fleet users data took {time1:.2f} seconds.')

    start = time.perf_counter()
    fleet_sheet_path = excel.create_xl_from_raw_data_dict(fleet_sheet_data, None, retrieved_at, file_name=file_name, column_formats=FLEET_SHEET_COLUMN_FORMATS)
    time2 = time.perf_counter() - start
    print(f'Creating the excel sheet took {time2:.2f} seconds ({time1+time2:.2f} seconds in total).')

    return fleet_sheet_path


async def __get_fleet_details_by_info(ctx: Context, fleet_info: EntityInfo, fleet_users_data: EntitiesData, max_tourney_battle_attempts: int = None, retrieved_at: datetime = None, is_past_data: bool = False, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    fleet_details = __create_fleet_details_from_info(fleet_info, fleet_users_data, max_tourney_battle_attempts=max_tourney_battle_attempts, retrieved_at=retrieved_at, is_past_data=is_past_data)
    if as_embed:
        return [(await fleet_details.get_details_as_embed(ctx, display_inline=False))]
    else:
        return (await fleet_details.get_details_as_text(entity.EntityDetailsType.LONG))


def __get_fleet_sheet_data_from_lines(fleet_sheet_lines: List[List]) -> List[Dict]:
    fleet_sheet_data = []
    for i in range(1, len(fleet_sheet_lines)):
        d = {}
        for j in range(len(fleet_sheet_lines[0])):
            d[fleet_sheet_lines[0][j]] = fleet_sheet_lines[i][j]
        fleet_sheet_data.append(d)
    return fleet_sheet_data


def __get_fleet_sheet_lines(fleet_users_data: EntitiesData, retrieved_at: datetime, max_tourney_battle_attempts: int = None, fleet_name: str = None, include_player_id: bool = False, include_fleet_id: bool = False, include_division_name: bool = False, include_pvp_stats: bool = False, sort_lines: bool = True) -> List[Any]:
    titles = list(FLEET_SHEET_COLUMN_DEFAULT_HEADERS)
    include_tourney_battle_attempts = max_tourney_battle_attempts is not None
    if include_tourney_battle_attempts:
        titles.append('Tournament attempts left')
        titles.append('Star value')
    if include_division_name:
        titles.append('Division')
    if include_player_id:
        titles.append('Player ID')
    if include_fleet_id:
        titles.append('Fleet ID')
    if include_pvp_stats:
        titles.extend((
            'PvP wins',
            'PvP losses',
            'PvP draws',
            'Defense wins',
            'Defense losses',
            'Defense draws',
        ))

    result = []
    for user_info in fleet_users_data.values():
        user_fleet_name = fleet_name or user_info.get(FLEET_DESCRIPTION_PROPERTY_NAME, user_info.get('Alliance', {}).get(FLEET_DESCRIPTION_PROPERTY_NAME, ''))
        if user_fleet_name.startswith('='):
            user_fleet_name = f'="{user_fleet_name}"'
        user_name = user_info.get(user.USER_DESCRIPTION_PROPERTY_NAME, '')
        if user_name.startswith('='):
            user_name = f'="{user_name}"'
        last_login_date = user_info.get('LastLoginDate')
        alliance_join_date = user_info.get('AllianceJoinDate')
        logged_in_ago = None
        joined_ago = None
        if last_login_date:
            logged_in_ago = retrieved_at - utils.parse.pss_datetime(last_login_date)
        if alliance_join_date:
            joined_ago = retrieved_at - utils.parse.pss_datetime(alliance_join_date)
        if fleet_name is None and FLEET_DESCRIPTION_PROPERTY_NAME in user_info.keys():
            fleet_name = user_info[FLEET_DESCRIPTION_PROPERTY_NAME]
        line = [
            utils.format.datetime_for_excel(retrieved_at),
            user_fleet_name,
            user_name,
            user_info.get('AllianceMembership', ''),
            utils.convert.pss_timestamp_to_excel(last_login_date),
            int(user_info['Trophy']) if 'Trophy' in user_info else '',
            int(user_info['HighestTrophy']) if 'HighestTrophy' in user_info else '',
            int(user_info['AllianceScore'] if 'AllianceScore' in user_info else ''),
            utils.convert.pss_timestamp_to_excel(alliance_join_date),
            int(user_info['CrewDonated']) if 'CrewDonated' in user_info else '',
            int(user_info['CrewReceived']) if 'CrewReceived' in user_info else '',
            utils.format.timedelta(logged_in_ago, include_relative_indicator=False),
            utils.format.timedelta(joined_ago, include_relative_indicator=False),
        ]
        if include_tourney_battle_attempts:
            attempts_left = None
            attempts = user.__get_tourney_battle_attempts(user_info, retrieved_at)
            if attempts is not None and max_tourney_battle_attempts:
                attempts_left = max_tourney_battle_attempts - attempts
            line.append('' if attempts_left is None else attempts_left)

            star_value = user_info.get('StarValue')
            if star_value is None:
                star_value, _ = user.get_star_value_from_user_info(user_info)
            line.append('' if star_value is None else star_value)
        if include_division_name:
            line.append(get_division_name(user_info.get('Alliance', {}).get(top.DIVISION_DESIGN_KEY_NAME)))
        if include_player_id:
            line.append(user_info.get(user.USER_KEY_NAME, ''))
        if include_fleet_id:
            line.append(user_info.get(FLEET_KEY_NAME, ''))
        if include_pvp_stats:
            line.extend((
                user_info.get('PVPAttackWins', ''),
                user_info.get('PVPAttackLosses', ''),
                user_info.get('PVPAttackDraws', ''),
                user_info.get('PVPDefenceWins', ''),
                user_info.get('PVPDefenceLosses', ''),
                user_info.get('PVPDefenceDraws', ''),
            ))
        result.append(line)

    if sort_lines:
        result = sorted(result, key=lambda x: (
            lookups.ALLIANCE_MEMBERSHIP_LOOKUP.index(x[3]),
            -x[7],
            -x[5],
            x[2]
        ))
    result.insert(0, titles)
    return result


async def __get_get_alliance_base_path(fleet_id: str) -> str:
    access_token = await login.DEVICES.get_access_token()
    result = f'AllianceService/GetAlliance?accessToken={access_token}&allianceId={fleet_id}'
    return result


async def __get_search_fleet_users_base_path(fleet_id: str) -> str:
    access_token = await login.DEVICES.get_access_token()
    result = f'AllianceService/ListUsers?accessToken={access_token}&skip=0&take=100&allianceId={fleet_id}'
    return result


async def __get_search_fleets_base_path(fleet_name: str) -> str:
    access_token = await login.DEVICES.get_access_token()
    result = f'AllianceService/SearchAlliances?accessToken={access_token}&skip=0&take=100&name={utils.convert.url_escape(fleet_name)}'
    return result





# ---------- Create entity.EntityDetails ----------

def __create_fleet_details_from_info(fleet_infos: EntityInfo, fleet_users_data: EntitiesData, max_tourney_battle_attempts: int = None, retrieved_at: datetime = None, is_past_data: bool = None) -> entity.EscapedEntityDetails:
    return entity.EscapedEntityDetails(fleet_infos, __properties['title'], __properties['description'], __properties['properties'], __properties['embed_settings'], fleet_users_data, max_tourney_battle_attempts=max_tourney_battle_attempts, retrieved_at=retrieved_at, is_past_data=is_past_data)





# ---------- Initialization ----------

__properties: entity.EntityDetailsCreationPropertiesCollection = {
    'title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, transform_function=__get_name)
    ),
    'description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, omit_if_none=True, transform_function=__get_description_as_text)
    ),
    'properties': entity.EntityDetailPropertyListCollection(
        [
        entity.EntityDetailProperty('Ranking', True, transform_function=__get_ranking),
        entity.EntityDetailProperty('Min trophies', True, transform_function=__get_min_trophies),
        entity.EntityDetailProperty('Members', True, transform_function=__get_member_count),
        entity.EntityDetailProperty('Trophies', True, transform_function=__get_trophies),
        entity.EntityDetailProperty('Division', True, transform_function=__get_division_name_and_ranking),
        entity.EntityDetailProperty('Stars', True, transform_function=__get_stars),
        entity.EntityDetailProperty('Type', True, transform_function=__get_type),
        entity.EntityDetailProperty('Championship score', True, entity_property_name='ChampionshipScore'),
        entity.EntityDetailProperty('history_note', False, transform_function=__get_historic_data_note, text_only=True)
    ]),
    'embed_settings': {
        'icon_url': entity.EntityDetailProperty('icon_url', False, entity_property_name='AllianceSpriteId', transform_function=sprites.get_download_sprite_link_by_property),
        'footer': entity.EntityDetailProperty('history_note', False, transform_function=__get_historic_data_note)
    }
}