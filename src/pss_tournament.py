from datetime import datetime
from typing import List

from discord import Colour, Embed

import pss_core as core
import utils


# ---------- Tournament ----------

def convert_tourney_embed_to_plain_text(embed: Embed) -> List[str]:
    result = [f'**{embed.author.name}**']
    for field in embed.fields:
        result.append(f'{field.name} {field.value}')
    return result


def format_tourney_start(start_date: datetime, utc_now: datetime) -> str:
    currently_running = is_tourney_running(start_date, utc_now)
    starts = get_start_string(currently_running)
    start_date_formatted = utils.format.date(start_date, True, False)
    tourney_month = start_date.strftime('%B')
    delta_start = start_date - utc_now
    delta_start_formatted = utils.format.timedelta(delta_start)
    delta_start_txt = f'**{delta_start_formatted}** ({start_date_formatted})'
    delta_end_txt = ''
    if currently_running:
        end_date = utils.datetime.get_first_of_following_month(start_date)
        end_date_formatted = utils.format.date(end_date, True, False)
        delta_end = end_date - utc_now
        delta_end_formatted = utils.format.timedelta(delta_end, False)
        delta_end_txt = f' and goes on for another **{delta_end_formatted}** (until {end_date_formatted})'
    result = f'Tournament in **{tourney_month}** {starts} {delta_start_txt}{delta_end_txt}'
    return result


def get_current_tourney_start(utc_now: datetime = None) -> datetime:
    first_of_next_month = utils.datetime.get_first_of_next_month(utc_now)
    result = first_of_next_month - utils.datetime.ONE_WEEK
    return result


async def get_max_tourney_battle_attempts() -> int:
    latest_settings = await core.get_latest_settings()
    max_tourney_battle_attempts = latest_settings.get('TournamentBonusScore')
    if max_tourney_battle_attempts:
        return int(max_tourney_battle_attempts)
    else:
        return None


def get_next_tourney_start(utc_now: datetime = None) -> datetime:
    next_first_of_next_month = utils.datetime.get_first_of_following_month(utils.datetime.get_first_of_next_month(utc_now))
    result = next_first_of_next_month - utils.datetime.ONE_WEEK
    return result


def get_start_string(currently_running: bool ) -> str:
    if currently_running:
        return 'started'
    else:
        return 'starts'


def get_tourney_start_as_embed(start_date: datetime, utc_now: datetime, colour: Colour = None) -> Embed:
    if colour is None:
        colour = 0
    fields = []
    currently_running = is_tourney_running(start_date, utc_now)
    starts = get_start_string(currently_running)
    start_date_formatted = utils.format.date(start_date, True, False)
    tourney_month = start_date.strftime('%B')
    delta_start = start_date - utc_now
    delta_start_formatted = utils.format.timedelta(delta_start)
    delta_start_txt = f'{delta_start_formatted} ({start_date_formatted})'
    if currently_running:
        fields.append(utils.discord.get_embed_field_def(starts.capitalize(), start_date_formatted, True))
    else:
        fields.append(utils.discord.get_embed_field_def(starts.capitalize(), delta_start_txt, True))
    if currently_running:
        end_date = utils.datetime.get_first_of_following_month(start_date)
        delta_end = end_date - utc_now
        delta_end_formatted = utils.format.timedelta(delta_end, True)
        fields.append(utils.discord.get_embed_field_def('Ends', delta_end_formatted, True))
    result = utils.discord.create_embed(f'{tourney_month} tournament', colour=colour, fields=fields)
    return result


def is_tourney_running(start_date: datetime = None, utc_now: datetime = None) -> bool:
    if not utc_now:
        utc_now = utils.get_utc_now()
    if not start_date:
        start_date = get_current_tourney_start(utc_now)

    return start_date < utc_now