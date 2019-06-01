#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
from datetime import date, datetime, time, timedelta, timezone

import discord

import pss_core as core
import utility as util


A_WEEK_PRIOR = timedelta(-7)

# ----- Tournament methods ---------------------------------------------------------
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
    fields = []
    currently_running = is_tourney_running(start_date, utc_now)
    starts = get_start_string(currently_running)
    tourney_month = start_date.strftime('%B')
    delta_start = start_date - utc_now
    delta_start_formatted = util.get_formatted_timedelta(delta_start)
    fields.append(util.get_embed_field('Starts in', delta_start_formatted, True))
    if currently_running:
        end_date = util.get_first_of_following_month(start_date)
        delta_end = end_date - utc_now
        delta_end_formatted = util.get_formatted_timedelta(delta_end, False)
        fields.append(util.get_embed_field('Ends in', delta_start_formatted, True))
    result = util.create_embed('Tournament info', f'for {tourney_month}', colour, fields)
    return result


def get_current_tourney_start():
    first_of_next_month = util.get_first_of_next_month()
    result = first_of_next_month + A_WEEK_PRIOR
    return result


def get_next_tourney_start():
    next_first_of_next_month = util.get_first_of_following_month(util.get_first_of_next_month())
    result = next_first_of_next_month + A_WEEK_PRIOR
    return result


def get_start_string(currently_running):
    if currently_running:
        return 'started'
    else:
        return 'starts'


def is_tourney_running(start_date, utc_now):
    return start_date < utc_now
