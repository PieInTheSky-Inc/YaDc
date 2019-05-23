#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
from datetime import date, datetime, time, timedelta, timezone

import pss_core as core
import utility as util


# ----- Tournament methods ---------------------------------------------------------
def format_tourney_start(start_date, utc_now):
    currently_running = is_tourney_running(start_date, utc_now)
    starts = get_start_string(currently_running)
    start_date_formatted = util.get_formatted_date(start_date)
    tourney_month = start_date.strftime('%B')
    delta_start = start_date - utc_now
    delta_start_formatted = '{} ({})'.format(util.get_formatted_timedelta(delta_start), start_date_formatted)
    currently_running_txt = ''
    delta_end_formatted = ''
    result = 'Tournament in {} {} '.format(start_date.strftime('%B'), starts)
    if currently_running:
        end_date = utility.get_first_of_following_month(start_date)
        end_date_formatted = util.get_formatted_date(end_date)
        delta_end = end_date - utcnow
        delta_end_formatted = util.get_formatted_timedelta(delta_end, False)
        currently_running_txt = ' and goes on for another **{}** (until {})'.format(delta_end_formatted, end_date_formatted)
    result = 'Tournament in {} {} **{}**{}'.format(tourney_month, starts, delta_start_formatted, currently_running_txt)
    return result


def get_current_tourney_start():
    first_of_next_month = util.get_first_of_next_month()
    result = first_of_next_month + a_week_prior
    return result


def get_next_tourney_start():
    next_first_of_next_month = util.get_first_of_following_month(util.get_first_of_next_month())
    result = next_first_of_next_month + a_week_prior
    return result


def get_start_string(currently_running):
    if currently_running:
        return 'started'
    else:
        return 'starts'


def is_tourney_running(start_date, utcnow):
    return start_date < utcnow
