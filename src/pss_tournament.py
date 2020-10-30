#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import date, datetime, time, timedelta, timezone
from typing import List
import discord

import pss_core as core
import utility as util


# ---------- tournament command methods ----------

__A_WEEK_PRIOR = timedelta(-7)


def format_tourney_start(start_date, utc_now):
    currently_running = is_tourney_running(start_date, utc_now)
    starts = get_start_string(currently_running)
    start_date_formatted = util.get_formatted_date(start_date, True, False)
    tourney_month = start_date.strftime('%B')
    delta_start = start_date - utc_now
    delta_start_formatted = util.get_formatted_timedelta(delta_start)
    delta_start_txt = f'**{delta_start_formatted}** ({start_date_formatted})'
    delta_end_txt = ''
    if currently_running:
        end_date = util.get_first_of_following_month(start_date)
        end_date_formatted = util.get_formatted_date(end_date, True, False)
        delta_end = end_date - utc_now
        delta_end_formatted = util.get_formatted_timedelta(delta_end, False)
        delta_end_txt = f' and goes on for another **{delta_end_formatted}** (until {end_date_formatted})'
    result = f'Tournament in **{tourney_month}** {starts} {delta_start_txt}{delta_end_txt}'
    return result


def embed_tourney_start(start_date, utc_now, colour=None):
    if colour is None:
        colour = 0
    fields = []
    currently_running = is_tourney_running(start_date, utc_now)
    starts = get_start_string(currently_running)
    start_date_formatted = util.get_formatted_date(start_date, True, False)
    tourney_month = start_date.strftime('%B')
    delta_start = start_date - utc_now
    delta_start_formatted = util.get_formatted_timedelta(delta_start)
    delta_start_txt = f'{delta_start_formatted} ({start_date_formatted})'
    if currently_running:
        fields.append(util.get_embed_field_def(starts.capitalize(), start_date_formatted, True))
    else:
        fields.append(util.get_embed_field_def(starts.capitalize(), delta_start_txt, True))
    if currently_running:
        end_date = util.get_first_of_following_month(start_date)
        delta_end = end_date - utc_now
        delta_end_formatted = util.get_formatted_timedelta(delta_end, True)
        fields.append(util.get_embed_field_def('Ends', delta_end_formatted, True))
    result = util.create_embed(f'{tourney_month} tournament', colour=colour, fields=fields)
    return result


def convert_tourney_embed_to_plain_text(embed: discord.Embed) -> List[str]:
    result = [f'**{embed.author.name}**']
    for field in embed.fields:
        result.append(f'{field.name} {field.value}')
    return result


def get_current_tourney_start(utc_now: datetime = None):
    first_of_next_month = util.get_first_of_next_month(utc_now)
    result = first_of_next_month + __A_WEEK_PRIOR
    return result


def get_next_tourney_start(utc_now: datetime = None):
    next_first_of_next_month = util.get_first_of_following_month(util.get_first_of_next_month(utc_now))
    result = next_first_of_next_month + __A_WEEK_PRIOR
    return result


def get_start_string(currently_running):
    if currently_running:
        return 'started'
    else:
        return 'starts'


def is_tourney_running(start_date=None, utc_now=None):
    if not utc_now:
        utc_now = util.get_utcnow()
    if not start_date:
        start_date = get_current_tourney_start(utc_now)

    return start_date < utc_now
