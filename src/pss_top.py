from datetime import datetime
from typing import List, Tuple, Union

from discord import Colour, Embed
from discord.ext.commands import Context
from discord.utils import escape_markdown

import emojis
import pss_assert
import pss_core as core
import pss_entity as entity
from pss_exception import Error
import pss_fleet as fleet
import pss_login as login
import pss_lookups as lookups
import pss_sprites as sprites
import pss_tournament as tourney
import pss_user as user
import settings
from typehints import EntitiesData, EntityInfo
import utils


# ---------- Constants ----------

ALLOWED_DIVISION_LETTERS: List[str] = sorted([letter for letter in lookups.DIVISION_CHAR_TO_DESIGN_ID.keys() if letter != '-'])

DIVISION_DESIGN_BASE_PATH: str = 'DivisionService/ListAllDivisionDesigns2'
DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'DivisionName'
DIVISION_DESIGN_KEY_NAME: str = 'DivisionDesignId'

STARS_BASE_PATH: str = 'AllianceService/ListAlliancesWithDivision'

TOP_FLEETS_BASE_PATH: str = 'AllianceService/ListAlliancesByRanking?skip=0&take='





# ---------- Top fleets info ----------

async def get_top_fleets(ctx: Context, take: int = 100, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    tourney_running = tourney.is_tourney_running()
    divisions_designs_data = await divisions_designs_retriever.get_data_dict3()
    fleets_divisions_max_ranks = [int(fleet_division_design_info['MaxRank']) for fleet_division_design_info in __get_fleet_division_designs(divisions_designs_data).values()]
    raw_data = await core.get_data_from_path(TOP_FLEETS_BASE_PATH + str(take))
    data = utils.convert.xmltree_to_dict3(raw_data)
    if data:
        title = f'Top {take} fleets'
        prepared_data = __prepare_top_fleets(data)
        body_lines = __create_body_lines_top_fleets(prepared_data, tourney_running, fleets_divisions_max_ranks)

        if as_embed:
            colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            return __create_top_embeds(title, body_lines, colour)
        else:
            result = [f'**{title}**']
            result.extend(body_lines)
            return result
    else:
        raise Error(f'An unknown error occured while retrieving the top fleets. Please contact the bot\'s author!')


def __create_body_lines_top_fleets(prepared_data: List[Tuple[int, str, str, str]], tourney_running: bool, fleets_divisions_max_ranks: List[int]) -> List[str]:
    if tourney_running:
        result = [
            f'**{position}.** {fleet_name} ({trophies} {emojis.trophy} - {stars} {emojis.star})'
            for position, fleet_name, trophies, stars
            in prepared_data
        ]
    else:
        result = [
            f'**{position}.** {fleet_name} ({trophies} {emojis.trophy})'
            for position, fleet_name, trophies, _
            in prepared_data
        ]
    for rank in sorted(fleets_divisions_max_ranks, reverse=True):
        if rank < len(result):
            result.insert(rank, utils.discord.ZERO_WIDTH_SPACE)
    return result


def __prepare_top_fleets(fleets_data: EntitiesData) -> List[Tuple]:
    result = [
        (
            position,
            escape_markdown(fleet_info[fleet.FLEET_DESCRIPTION_PROPERTY_NAME]),
            fleet_info['Trophy'],
            fleet_info['Score']
        ) for position, fleet_info in enumerate(fleets_data.values(), start=1)
    ]
    return result





# ---------- Top captains info ----------

async def get_top_captains(ctx: Context, take: int = 100, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    skip = 0
    data = await __get_top_captains_data(skip, take)

    if data:
        title = f'Top {take} captains'
        prepared_data = __prepare_top_captains(data, skip, take)
        body_lines = __create_body_lines_top_captains(prepared_data)
        if as_embed:
            colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            result = __create_top_embeds(title, body_lines, colour)
        else:
            result = [f'**{title}**']
            result.extend(body_lines)
        return result
    else:
        raise Error(f'An unknown error occured while retrieving the top captains. Please contact the bot\'s author!')


def __create_body_lines_top_captains(prepared_data: List[Tuple[int, str, str, str]]) -> List[str]:
    result = [
        f'**{position}.** {user_name} ({fleet_name}) - {trophies} {emojis.trophy}'
        for position, user_name, fleet_name, trophies
        in prepared_data
    ]
    return result


async def __get_top_captains_data(skip: int, take: int) -> EntitiesData:
    path = await __get_top_captains_path(skip, take)
    raw_data = await core.get_data_from_path(path)
    data = utils.convert.xmltree_to_dict3(raw_data)
    return data


async def __get_top_captains_path(skip: int, take: int) -> str:
    skip += 1
    access_token = await login.DEVICES.get_access_token()
    result = f'LadderService/ListUsersByRanking?accessToken={access_token}&from={skip}&to={take}'
    return result


def __prepare_top_captains(users_data: EntitiesData, skip: int, take: int) -> List[Tuple]:
    start = skip + 1
    end = skip + take
    result = [
        (
            position,
            escape_markdown(user_info[user.USER_DESCRIPTION_PROPERTY_NAME]),
            escape_markdown(user_info[fleet.FLEET_DESCRIPTION_PROPERTY_NAME]),
            user_info['Trophy']
        )
        for position, user_info
        in enumerate(users_data.values(), start=start)
        if position >= start and position <= end
    ]
    return result





# ---------- Stars info ----------

async def get_division_stars(ctx: Context, division: str = None, fleet_data: dict = None, retrieved_date: datetime = None, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    if division:
        pss_assert.valid_parameter_value(division, 'division', min_length=1, allowed_values=ALLOWED_DIVISION_LETTERS)
        if division == '-':
            division = None
    else:
        division = None

    if fleet_data is None or retrieved_date is None:
        data = await core.get_data_from_path(STARS_BASE_PATH)
        fleet_infos = utils.convert.xmltree_to_dict3(data)
    else:
        fleet_infos = fleet_data

    divisions_designs_infos = await divisions_designs_retriever.get_data_dict3()

    divisions = {}
    if division:
        division_design_id = lookups.DIVISION_CHAR_TO_DESIGN_ID[division.upper()]
        divisions[division_design_id] = [fleet_info for fleet_info in fleet_infos.values() if fleet_info[DIVISION_DESIGN_KEY_NAME] == division_design_id]
        pass
    else:
        for division_design_id in lookups.DIVISION_DESIGN_ID_TO_CHAR.keys():
            if division_design_id != '0':
                divisions[division_design_id] = [fleet_info for fleet_info in fleet_infos.values() if fleet_info[DIVISION_DESIGN_KEY_NAME] == division_design_id]

    if divisions:
        divisions_texts = []
        for division_design_id, fleet_infos in divisions.items():
            divisions_texts.append((division_design_id, __get_division_stars_as_text(fleet_infos)))

        result = []
        footer = utils.datetime.get_historic_data_note(retrieved_date)
        colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
        for division_design_id, division_text in divisions_texts:
            if as_embed:
                division_title = __get_division_title(division_design_id, divisions_designs_infos, False)
                thumbnail_url = await sprites.get_download_sprite_link(divisions_designs_infos[division_design_id]['BackgroundSpriteId'])
                embed_bodies = utils.discord.create_posts_from_lines(division_text, utils.discord.MAXIMUM_CHARACTERS_EMBED_DESCRIPTION)
                for i, embed_body in enumerate(embed_bodies):
                    thumbnail_url = thumbnail_url if i == 0 else None
                    embed = utils.discord.create_embed(division_title, description=embed_body, footer=footer, thumbnail_url=thumbnail_url, colour=colour)
                    result.append(embed)
            else:
                division_title = __get_division_title(division_design_id, divisions_designs_infos, True)
                result.append(division_title)
                result.extend(division_text)
                result.append(utils.discord.ZERO_WIDTH_SPACE)

        if not as_embed:
            result = result[:-1]
            if footer:
                result.append(f'```{footer}```')

        return result
    else:
        raise Error(f'An unknown error occured while retrieving division info. Please contact the bot\'s author!')


def __get_division_stars_as_text(fleet_infos: List[EntityInfo]) -> List[str]:
    lines = []
    fleet_infos = entity.sort_entities_by(fleet_infos, [('Score', int, True)])
    fleet_infos_count = len(fleet_infos)
    for i, fleet_info in enumerate(fleet_infos, start=1):
        fleet_name = escape_markdown(fleet_info['AllianceName'])
        additional_info: List[Tuple[str, str]] = []
        trophies = fleet_info.get('Trophy')
        if trophies:
            additional_info.append((trophies, emojis.trophy))
        member_count = fleet_info.get('NumberOfMembers')
        if member_count:
            additional_info.append((str(member_count), emojis.members))
        stars = fleet_info['Score']
        if i < fleet_infos_count:
            difference = int(stars) - int(fleet_infos[i]['Score'])
        else:
            difference = 0
        if additional_info:
            additional_str = f' ({" ".join([" ".join(info) for info in additional_info])})'
        else:
            additional_str = ''
        lines.append(f'**{i:d}.** {stars} (+{difference}) {emojis.star} {fleet_name}{additional_str}')
    return lines


def __get_division_title(division_design_id: str, divisions_designs_infos: EntitiesData, include_markdown: bool) -> str:
    title = divisions_designs_infos[division_design_id][DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME]
    if include_markdown:
        return f'__**{title}**__'
    else:
        return title





# ---------- Helper functions ----------

def is_valid_division_letter(div_letter: str) -> bool:
    if div_letter is None:
        result = True
    else:
        result = div_letter.lower() in [letter.lower() for letter in ALLOWED_DIVISION_LETTERS]
    return result


def __create_top_embeds(title: str, body_lines: List[str], colour: Colour) -> List[Embed]:
    bodies = utils.discord.create_posts_from_lines(body_lines, utils.discord.MAXIMUM_CHARACTERS_EMBED_DESCRIPTION)
    result = []
    for body in bodies:
        result.append(utils.discord.create_embed(title, description=body, colour=colour))
    return result


def __get_fleet_division_designs(divisions_designs_data: EntitiesData) -> EntitiesData:
    result = {key: value for key, value in divisions_designs_data.items() if value.get('DivisionType') == 'Fleet'}
    return result





# ---------- Initilization ----------

divisions_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    DIVISION_DESIGN_BASE_PATH,
    DIVISION_DESIGN_KEY_NAME,
    DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='DivisionDesigns'
)