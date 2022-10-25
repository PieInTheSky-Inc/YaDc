import calendar
from datetime import datetime
import math
from typing import List, Optional, Tuple, Union

from discord import ApplicationContext
from discord import Embed
from discord import Interaction
from discord.ext.commands import Context
from discord.file import File
from discord.utils import escape_markdown


from . import emojis
from.pagination import SelectView
from . import pss_assert
from . import pss_core as core
from . import pss_entity as entity
from .pss_exception import NotFound
from . import pss_fleet as fleet
from . import pss_lookups as lookups
from . import pss_room as room
from . import pss_ship as ship
from . import pss_sprites as sprites
from . import pss_top as top
from . import pss_tournament as tourney
from . import pss_user as user
from . import settings
from .typehints import EntitiesData, EntityInfo
from . import utils


# ---------- Constants ----------

INSPECT_SHIP_BASE_PATH = f'ShipService/InspectShip2'

LEAGUE_BASE_PATH = f'LeagueService/ListLeagues2?accessToken='
LEAGUE_INFO_DESCRIPTION_PROPERTY_NAME = 'LeagueName'
LEAGUE_INFO_KEY_NAME = 'LeagueId'
LEAGUE_INFOS_CACHE = []

SEARCH_USERS_BASE_PATH = f'UserService/SearchUsers?searchString='

USER_DESCRIPTION_PROPERTY_NAME = 'Name'
USER_KEY_NAME = 'Id'





# ---------- User info ----------

async def get_user_details_by_info(ctx: Context, user_info: EntityInfo, max_tourney_battle_attempts: int = None, retrieved_at: datetime = None, past_fleet_infos: EntitiesData = None, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    is_past_data = past_fleet_infos is not None and past_fleet_infos

    user_id = user_info[USER_KEY_NAME]
    retrieved_at = retrieved_at or utils.get_utc_now()
    tourney_running = tourney.is_tourney_running(utc_now=retrieved_at)
    if past_fleet_infos:
        ship_info = {}
        fleet_info = past_fleet_infos.get(user_info.get(fleet.FLEET_KEY_NAME))
        current_user_info = await __get_user_info_by_id(user_id) or {}
        current_user_name = current_user_info.get(USER_DESCRIPTION_PROPERTY_NAME)
        if current_user_name and current_user_name != user_info.get(USER_DESCRIPTION_PROPERTY_NAME):
            user_info['CurrentName'] = current_user_name
    else:
        _, ship_info = await ship.get_inspect_ship_for_user(user_id)
        fleet_info = await __get_fleet_info_by_user_info(user_info)

    is_in_tourney_fleet = fleet.is_tournament_fleet(fleet_info) and tourney_running
    user_details = __create_user_details_from_info(user_info, fleet_info, ship_info, max_tourney_battle_attempts=max_tourney_battle_attempts, retrieved_at=retrieved_at, is_past_data=is_past_data, is_in_tourney_fleet=is_in_tourney_fleet)

    if as_embed:
        return [(await user_details.get_details_as_embed(ctx, display_inline=False))]
    else:
        return (await user_details.get_details_as_text(entity.EntityDetailsType.LONG))


async def get_users_infos_by_name(user_name: str) -> List[EntityInfo]:
    pss_assert.valid_parameter_value(user_name, 'user_name', min_length=0)

    user_infos = list((await __get_users_data(user_name)).values())
    return user_infos


async def get_user_infos_from_tournament_data_by_name(user_name: str, users_data: EntitiesData) -> List[EntityInfo]:
    user_name_lower = user_name.lower()
    result = {user_id: user_info for (user_id, user_info) in users_data.items() if user_name_lower in user_info.get(user.USER_DESCRIPTION_PROPERTY_NAME, '').lower()}
    user_infos_current = await __get_users_data(user_name)
    if user_infos_current:
        for user_info in user_infos_current.values():
            user_id = user_info[user.USER_KEY_NAME]
            if user_id in users_data:
                current_user_info = await __get_user_info_by_id(user_id) or {}
                current_user_name = current_user_info.get(user.USER_DESCRIPTION_PROPERTY_NAME)
                if user_id not in result:
                    result[user_id] = users_data[user_id]
                if current_user_name and current_user_name != result[user_id][user.USER_DESCRIPTION_PROPERTY_NAME]:
                    result[user_id]['CurrentName'] = current_user_name
    else:
        for tournament_user_id, tournament_user_info in result.items():
            user_info = await __get_user_info_by_id(tournament_user_id)
            if result[tournament_user_id][user.USER_DESCRIPTION_PROPERTY_NAME] != user_info[user.USER_DESCRIPTION_PROPERTY_NAME]:
                result[tournament_user_id]['CurrentName'] = user_info[user.USER_DESCRIPTION_PROPERTY_NAME]
    return list(result.values())


async def get_user_ship_layout(ctx: Context, user_id: str, as_embed: bool = settings.USE_EMBEDS) -> Tuple[Union[List[Embed], List[str]], File]:
    ships_designs_data = await ship.ships_designs_retriever.get_data_dict3()
    rooms_designs_data = await room.rooms_designs_retriever.get_data_dict3()
    rooms_designs_sprites_data = await room.rooms_designs_sprites_retriever.get_data_dict3()
    user_info, user_ship_info = await ship.get_inspect_ship_for_user(user_id)
    ship_design_info: entity.EntityInfo = ships_designs_data[user_ship_info.get('ShipDesignId')]
    rooms_designs_sprites_ids = {value.get('RoomDesignId'): value.get('SpriteId') for value in rooms_designs_sprites_data.values() if value.get('RaceId') == ship_design_info.get('RaceId')}
    file_name_prefix = f'{ctx.author.id}{int(utils.get_utc_now().timestamp())}'
    file_path = await ship.make_ship_layout_sprite(file_name_prefix, user_ship_info, ship_design_info, rooms_designs_data, rooms_designs_sprites_ids)
    title = f'{escape_markdown(user_info[user.USER_DESCRIPTION_PROPERTY_NAME])}'
    fields = []
    fleet_name = user_info.get(fleet.FLEET_DESCRIPTION_PROPERTY_NAME)
    if fleet_name:
        fields.append(('Fleet', escape_markdown(fleet_name), None))
    fields.append(('Trophies', user_info['Trophy'], None))
    fields.append(('Ship', f'{ship_design_info["ShipDesignName"]} (level {ship_design_info["ShipLevel"]})', None))

    if as_embed:
        miniship_sprite_url = await sprites.get_download_sprite_link(ship_design_info.get('MiniShipSpriteId'))
        user_pin_sprite_url = await sprites.get_download_sprite_link(user_info.get('IconSpriteId'))
        colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
        embed = utils.discord.create_basic_embeds_from_fields(title, fields=fields, colour=colour, thumbnail_url=miniship_sprite_url, icon_url=user_pin_sprite_url)[0]
        output = [embed]
    else:
        output = [f'**{title}**'] + [f'{field[0]}{entity.DEFAULT_DETAIL_PROPERTY_LONG_SEPARATOR}{field[1]}' for field in fields]
    return output, file_path


def get_user_search_details(user_info: EntityInfo) -> str:
    user_name = __get_user_name(user_info)
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


async def __get_users_data(user_name: str) -> EntitiesData:
    path = f'{SEARCH_USERS_BASE_PATH}{utils.convert.url_escape(user_name)}'
    user_data_raw = await core.get_data_from_path(path)
    user_infos = utils.convert.xmltree_to_dict3(user_data_raw)
    return user_infos





# ---------- Transformation functions ----------

def __get_crew_borrowed(user_info: EntityInfo, fleet_info: EntityInfo = None, **kwargs) -> Optional[str]:
    result = None
    if fleet_info:
        result = user_info.get('CrewReceived')
    return result


def __get_crew_donated(user_info: EntityInfo, fleet_info: EntityInfo = None, **kwargs) -> Optional[str]:
    result = None
    if fleet_info:
        result = user_info.get('CrewDonated')
    return result


def __get_crew_donated_borrowed(user_info: EntityInfo, fleet_info: EntityInfo = None, **kwargs) -> Optional[str]:
    result = None
    if fleet_info:
        crew_donated = __get_crew_donated(user_info, fleet_info, **kwargs)
        crew_borrowed = __get_crew_borrowed(user_info, fleet_info, **kwargs)
        if crew_donated and crew_borrowed:
            result = f'{crew_donated}/{crew_borrowed}'
    return result


def __get_division_name(user_info: EntityInfo, fleet_info: EntityInfo = None, **kwargs) -> Optional[str]:
    if fleet_info:
        result = fleet.get_division_name(fleet_info.get(top.DIVISION_DESIGN_KEY_NAME))
    else:
        result = '-'
    return result


def __get_fleet_joined_at(user_info: EntityInfo, fleet_info: EntityInfo = None, retrieved_at: datetime = None, **kwargs) -> Optional[str]:
    result = None
    if fleet_info and retrieved_at:
        result = __get_timestamp(user_info, retrieved_at, **kwargs)
    return result


def __get_fleet_name_and_rank(user_info: EntityInfo, fleet_info: EntityInfo = None, **kwargs) -> Optional[str]:
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


def __get_historic_data_note(user_info: EntityInfo, retrieved_at: datetime = None, is_past_data: bool = None, **kwargs) -> Optional[str]:
    if is_past_data:
        result = utils.datetime.get_historic_data_note(retrieved_at)
    else:
        result = None
    return result


def __get_league(user_info: EntityInfo, **kwargs) -> Optional[str]:
    result = None
    trophies = user_info.get('Trophy')
    if trophies is not None:
        result = f'{__get_league_from_trophies(int(trophies))}'
        highest_trophies = user_info.get('HighestTrophy')
        if highest_trophies is not None:
            result += f' (highest: {__get_league_from_trophies(int(highest_trophies))})'
    return result


async def __get_level(user_info: EntityInfo, ship_info: EntityInfo = None, **kwargs) -> Optional[str]:
    result = await ship.get_ship_level(ship_info)
    return result


def __get_pvp_attack_stats(user_info: EntityInfo, **kwargs) -> Optional[str]:
    result = None
    if all([field in user_info for field in ['PVPAttackDraws', 'PVPAttackLosses', 'PVPAttackWins']]):
        pvp_draws = int(user_info['PVPAttackDraws'])
        pvp_losses = int(user_info['PVPAttackLosses'])
        pvp_wins = int(user_info['PVPAttackWins'])
        result = __format_pvp_stats(pvp_wins, pvp_losses, pvp_draws)
    return result


def __get_pvp_defense_stats(user_info: EntityInfo, **kwargs) -> Optional[str]:
    result = None
    if all([field in user_info for field in ['PVPDefenceDraws', 'PVPDefenceLosses', 'PVPDefenceWins']]):
        defense_draws = int(user_info['PVPDefenceDraws'])
        defense_losses = int(user_info['PVPDefenceLosses'])
        defense_wins = int(user_info['PVPDefenceWins'])
        result = __format_pvp_stats(defense_wins, defense_losses, defense_draws)
    return result


def __get_star_value(user_info: EntityInfo, max_tourney_battle_attempts: int = None, retrieved_at: datetime = None, is_in_tourney_fleet: bool = None, **kwargs) -> Optional[str]:
    result = None
    if is_in_tourney_fleet and tourney.is_tourney_running(retrieved_at):
        star_value = user_info.get('StarValue')
        if star_value is None:
            star_value, source = get_star_value_from_user_info(user_info)
            if star_value is not None:
                if source < 0:
                    result = f'{star_value} (based on trophies)'
                elif source > 0:
                    result = f'{star_value} (based on yesterday\'s stars)'
                else:
                    result = str(star_value)
        else:
            result = str(star_value)
    return result


def __get_stars(user_info: EntityInfo, max_tourney_battle_attempts: int = None, retrieved_at: datetime = None, is_in_tourney_fleet: bool = None, **kwargs) -> Optional[str]:
    attempts = __get_tourney_battle_attempts(user_info, retrieved_at)
    if attempts is not None and max_tourney_battle_attempts:
        attempts_left = max_tourney_battle_attempts - int(attempts)
    else:
        attempts_left = None

    result = None
    stars = user_info.get('AllianceScore')
    if is_in_tourney_fleet or (stars is not None and stars != '0'):
        result = stars
        if attempts_left is not None and is_in_tourney_fleet:
            result += f' ({attempts_left} attempts left)'
    return result


def __get_timestamp(user_info: EntityInfo, retrieved_at: datetime = None, **kwargs) -> Optional[str]:
    value = kwargs.get('entity_property')
    timestamp = utils.parse.pss_datetime(value)
    if timestamp is None:
        return None
    return __format_past_timestamp(timestamp, retrieved_at)


def __get_trophies(user_info: EntityInfo, **kwargs) -> Optional[str]:
    result = None
    trophies = user_info.get('Trophy')
    if trophies is not None:
        result = f'{trophies}'
        highest_trophies = user_info.get('HighestTrophy')
        if highest_trophies is not None:
            result += f' (highest: {highest_trophies})'
    return result


def __get_user_type(user_info: EntityInfo, **kwargs) -> Optional[str]:
    result = None
    user_type = user_info.get('UserType')
    if user_type is not None:
        result = lookups.get_lookup_value_or_default(lookups.USER_TYPE, user_type)
    return result


def __get_user_name(user_info: EntityInfo, **kwargs) -> Optional[str]:
    result = None
    user_name = user_info.get(USER_DESCRIPTION_PROPERTY_NAME)
    if user_name is not None:
        result = user_name
        current_user_name = user_info.get('CurrentName')
        if current_user_name is not None:
            result += f' (now: {current_user_name})'
    return result





# ---------- Helper functions ----------

async def find_tournament_user(ctx: ApplicationContext, player_name: str, tourney_data) -> Tuple[EntityInfo, Interaction]:
    response = await utils.discord.edit_original_message(ctx.interaction, ['Searching player...'])
    user_infos = await get_user_infos_from_tournament_data_by_name(player_name, tourney_data.users)

    if user_infos:
        if len(user_infos) == 1:
            user_info = user_infos[0]
        else:
            user_infos.sort(key=lambda user: user[USER_DESCRIPTION_PROPERTY_NAME])
            user_infos = user_infos[:25]

            options = {user_info[USER_KEY_NAME]: (get_user_search_details(user_info), user_info) for user_info in user_infos}
            view = SelectView(ctx, 'Please select a player.', options)
            user_info = await view.wait_for_selection(ctx.interaction)

        return user_info, ctx.interaction
    else:
        raise NotFound(f'Could not find a player named `{player_name}` that participated in the {tourney_data.year} {calendar.month_name[int(tourney_data.month)]} tournament.')


async def find_user(ctx: ApplicationContext, player_name: str) -> Tuple[EntityInfo, Interaction]:
    response = await utils.discord.respond_with_output(ctx, ['Searching player...'])
    user_infos = await get_users_infos_by_name(player_name)
    if user_infos:
        user_info = None
        if len(user_infos) == 1:
            user_info = user_infos[0]
        else:
            options = {user_info[USER_KEY_NAME]: (get_user_search_details(user_info), user_info) for user_info in user_infos}
            view = SelectView(ctx, 'Please select a player.', options)
            user_info = await view.wait_for_selection(response)

        return user_info, response
    else:
        raise NotFound(f'Could not find a player named `{player_name}`.')


def get_star_value_from_user_info(user_info: EntityInfo, star_count: Union[int, str] = None) -> Tuple[Optional[int], Optional[int]]:
    """
    Returns: (star_value: `int`, source: `int`)

    `source` is:
       -1, if the star value has been calculated from the trophies
       1, if the star value has been calculated from the stars
       0, else
    """
    result = None
    source = None
    trophies = user_info.get('Trophy')
    if trophies:
        trophies = int(trophies)
        stars = int(star_count if star_count is not None else user_info.get('YesterdayAllianceScore', 0))
        from_trophies = math.floor(trophies / 1000)
        from_stars = math.floor(stars * 0.15)
        result = max(from_trophies, from_stars)
        source = -1 if from_trophies > from_stars else 0 if from_trophies == from_stars else 1
    return result, source


def __calculate_win_rate(wins: int, losses: int, draws: int) -> float:
    battles = wins + losses + draws
    if battles > 0:
        result = (wins + .5 * draws) / battles
        result *= 100
    else:
        result = 0.0
    return result


def __format_past_timestamp(timestamp: datetime, retrieved_at: datetime) -> str:
    retrieved_ago = utils.format.timedelta(timestamp - retrieved_at, include_seconds=False)
    result = f'{utils.format.datetime_for_excel(timestamp, include_seconds=False)} ({retrieved_ago})'
    return result


def __format_pvp_stats(wins: int, losses: int, draws: int) -> str:
    win_rate = __calculate_win_rate(wins, losses, draws)
    result = f'{wins}/{losses}/{draws} ({win_rate:0.2f}%)'
    return result


async def __get_fleet_info_by_user_info(user_info: EntityInfo) -> EntityInfo:
    result = {}
    fleet_id = user_info.get('AllianceId', '0')
    if fleet_id != '0':
        result = await fleet.get_fleets_data_by_id(fleet_id)
    return result


def __get_league_from_trophies(trophies: int) -> str:
    result = '-'
    if trophies is not None:
        for league_info in LEAGUE_INFOS_CACHE:
            if trophies >= league_info['MinTrophy'] and trophies <= league_info['MaxTrophy']:
                result = league_info[LEAGUE_INFO_DESCRIPTION_PROPERTY_NAME]
                break
    return result


def __get_tourney_battle_attempts(user_info: EntityInfo, utc_now: datetime) -> int:
    attempts = user_info.get('TournamentBonusScore')
    if attempts:
        attempts = int(attempts)
        last_login_date = utils.parse.pss_datetime(user_info.get('LastLoginDate'))
        if last_login_date:
            if last_login_date.day != utc_now.day:
                attempts = 0
    return attempts


async def __get_user_info_by_id(user_id: int) -> EntityInfo:
    result, _ = await ship.get_inspect_ship_for_user(user_id)
    return result


def __parse_timestamp(user_info: EntityInfo, field_name: str) -> Optional[str]:
    result = None
    timestamp = user_info.get(field_name)
    if timestamp is not None:
        result = utils.parse.pss_datetime(timestamp)
    return result





# ---------- Create entity.EntityDetails ----------

def __create_user_details_from_info(user_info: EntityInfo, fleet_info: EntityInfo = None, ship_info: EntityInfo = None, max_tourney_battle_attempts: int = None, retrieved_at: datetime = None, is_past_data: bool = None, is_in_tourney_fleet: bool = None) -> entity.EscapedEntityDetails:
    return entity.EscapedEntityDetails(user_info, __properties['title'], None, __properties['properties'], __properties['embed_settings'], fleet_info=fleet_info, ship_info=ship_info, max_tourney_battle_attempts=max_tourney_battle_attempts, retrieved_at=retrieved_at, is_past_data=is_past_data, is_in_tourney_fleet=is_in_tourney_fleet)





# ---------- Initialization ----------

__properties: entity.EntityDetailsCreationPropertiesCollection = {
    'title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, transform_function=__get_user_name)
    ),
    'properties': entity.EntityDetailPropertyListCollection(
        [
        entity.EntityDetailProperty('Account created', True, entity_property_name='CreationDate', transform_function=__get_timestamp),
        entity.EntityDetailProperty('Last Login', True, entity_property_name='LastLoginDate', transform_function=__get_timestamp),
        entity.EntityDetailProperty('Fleet', True, transform_function=__get_fleet_name_and_rank),
        entity.EntityDetailProperty('Division', True, transform_function=__get_division_name),
        entity.EntityDetailProperty('Joined fleet', True, entity_property_name='AllianceJoinDate', transform_function=__get_fleet_joined_at),
        entity.EntityDetailProperty('Trophies', True, transform_function=__get_trophies),
        entity.EntityDetailProperty('League', True, transform_function=__get_league),
        entity.EntityDetailProperty('Stars', True, transform_function=__get_stars),
        entity.EntityDetailProperty('Star value', True, transform_function=__get_star_value),
        entity.EntityDetailProperty('Crew donated', True, transform_function=__get_crew_donated, text_only=True),
        entity.EntityDetailProperty('Crew borrowed', True, transform_function=__get_crew_borrowed, text_only=True),
        entity.EntityDetailProperty('Crew donated/borrowed', True, transform_function=__get_crew_donated_borrowed, embed_only=True),
        entity.EntityDetailProperty('PVP win/lose/draw', True, transform_function=__get_pvp_attack_stats),
        entity.EntityDetailProperty('Defense win/lose/draw', True, transform_function=__get_pvp_defense_stats),
        entity.EntityDetailProperty('Level', True, transform_function=__get_level),
        entity.EntityDetailProperty('Championship score', True, entity_property_name='ChampionshipScore'),
        entity.EntityDetailProperty('User type', True, transform_function=__get_user_type),
        entity.EntityDetailProperty('history_note', False, transform_function=__get_historic_data_note, text_only=True)
    ]),
    'embed_settings': {
        'icon_url': entity.EntityDetailProperty('icon_url', False, entity_property_name='IconSpriteId', transform_function=sprites.get_download_sprite_link_by_property),
        'footer': entity.EntityDetailProperty('history_note', False, transform_function=__get_historic_data_note)
    }
}


async def init() -> None:
    league_data = await core.get_data_from_path(LEAGUE_BASE_PATH)
    league_infos = utils.convert.xmltree_to_dict3(league_data)
    for league_info in sorted(list(league_infos.values()), key=lambda league_info: int(league_info['MinTrophy'])):
        league_info['MinTrophy'] = int(league_info['MinTrophy'])
        league_info['MaxTrophy'] = int(league_info['MaxTrophy'])
        LEAGUE_INFOS_CACHE.append(league_info)