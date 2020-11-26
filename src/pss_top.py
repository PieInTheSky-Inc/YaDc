from datetime import datetime
from discord import Colour, Embed
from discord.ext.commands import Context
from discord.utils import escape_markdown
from typing import List, Tuple, Union

import emojis
import pss_assert
import pss_core as core
from pss_entity import EntitiesData, EntityInfo, EntityRetriever
from pss_exception import Error
import pss_fleet as fleet
import pss_login as login
import pss_lookups as lookups
import pss_sprites as sprites
import pss_tournament as tourney
import pss_user as user
import settings
import utils





# ---------- Constants ----------

DIVISION_DESIGN_BASE_PATH = 'DivisionService/ListAllDivisionDesigns2'
DIVISION_DESIGN_KEY_NAME = 'DivisionDesignId'
DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME = 'DivisionName'

TOP_FLEETS_BASE_PATH = f'AllianceService/ListAlliancesByRanking?skip=0&take='
STARS_BASE_PATH = f'AllianceService/ListAlliancesWithDivision'

ALLOWED_DIVISION_LETTERS = sorted([letter for letter in lookups.DIVISION_CHAR_TO_DESIGN_ID.keys() if letter != '-'])










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










# ---------- Top 100 Alliances ----------

async def get_top_fleets(ctx: Context, take: int = 100, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    tourney_running = tourney.is_tourney_running()
    raw_data = await core.get_data_from_path(TOP_FLEETS_BASE_PATH + str(take))
    data = core.xmltree_to_dict3(raw_data)
    if data:
        title = f'Top {take} fleets'
        prepared_data = __prepare_top_fleets(data)
        body_lines = __create_body_lines_top_fleets(prepared_data, tourney_running)

        if as_embed:
            colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
            return __create_top_embeds(title, body_lines, colour)
        else:
            result = [f'**{title}**']
            result.extend(body_lines)
            return result
    else:
        raise Error(f'An unknown error occured while retrieving the top fleets. Please contact the bot\'s author!')


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
    data = core.xmltree_to_dict3(raw_data)
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
        fleet_infos = core.xmltree_to_dict3(data)
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
            divisions_texts.append((division_design_id, _get_division_stars_as_text(fleet_infos)))

        result = []
        footer = utils.datetime.get_historic_data_note(retrieved_date)
        colour = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
        for division_design_id, division_text in divisions_texts:
            if as_embed:
                division_title = _get_division_title(division_design_id, divisions_designs_infos, False)
                thumbnail_url = await sprites.get_download_sprite_link(divisions_designs_infos[division_design_id]['BackgroundSpriteId'])
                embed_bodies = utils.discord.create_posts_from_lines(division_text, utils.discord.MAXIMUM_CHARACTERS_EMBED_DESCRIPTION)
                for i, embed_body in enumerate(embed_bodies):
                    thumbnail_url = thumbnail_url if i == 0 else None
                    embed = utils.discord.create_embed(division_title, description=embed_body, footer=footer, thumbnail_url=thumbnail_url, colour=colour)
                    result.append(embed)
            else:
                division_title = _get_division_title(division_design_id, divisions_designs_infos, True)
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


def _get_division_stars_as_text(fleet_infos: List[EntityInfo]) -> List[str]:
    lines = []
    fleet_infos = utils.sort_entities_by(fleet_infos, [('Score', int, True)])
    fleet_infos_count = len(fleet_infos)
    for i, fleet_info in enumerate(fleet_infos, start=1):
        fleet_name = escape_markdown(fleet_info['AllianceName'])
        if 'Trophy' in fleet_info.keys():
            trophies = fleet_info['Trophy']
            trophy_str = f' ({trophies} {emojis.trophy})'
        else:
            trophy_str = ''
        stars = fleet_info['Score']
        if i < fleet_infos_count:
            difference = int(stars) - int(fleet_infos[i]['Score'])
        else:
            difference = 0
        lines.append(f'**{i:d}.** {stars} (+{difference}) {emojis.star} {fleet_name}{trophy_str}')
    return lines


def _get_division_title(division_design_id: str, divisions_designs_infos: EntitiesData, include_markdown: bool) -> str:
    title = divisions_designs_infos[division_design_id][DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME]
    if include_markdown:
        return f'__**{title}**__'
    else:
        return title










# ---------- Initilization ----------

divisions_designs_retriever = EntityRetriever(
    DIVISION_DESIGN_BASE_PATH,
    DIVISION_DESIGN_KEY_NAME,
    DIVISION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='DivisionDesigns'
)
