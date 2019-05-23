#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
from datetime import date, datetime, time, timedelta, timezone

import pss_core as core
import utility as util


A_WEEK_PRIOR = timedelta(-7)

# ----- Tournament methods ---------------------------------------------------------
def format_tourney_start(start_date, utc_now):
    print('+ called format_tourney_start({}, {})'.format(start_date, utc_now))
    currently_running = is_tourney_running(start_date, utc_now)
    print('[format_tourney_start] retrieved currently_running: {}'.format(currently_running))
    starts = get_start_string(currently_running)
    print('[format_tourney_start] retrieved starts: {}'.format(starts))
    start_date_formatted = util.get_formatted_date(start_date)
    print('[format_tourney_start] retrieved start_date_formatted: {}'.format(start_date_formatted))
    tourney_month = start_date.strftime('%B')
    print('[format_tourney_start] retrieved tourney_month: {}'.format(tourney_month))
    delta_start = start_date - utc_now
    print('[format_tourney_start] retrieved delta_start: {}'.format(delta_start))
    delta_start_formatted = util.get_formatted_timedelta(delta_start)
    print('[format_tourney_start] retrieved delta_start_formatted: {}'.format(delta_start_formatted))
    delta_start_txt = '**{}** ({})'.format(delta_start_formatted, start_date_formatted)
    print('[format_tourney_start] retrieved delta_start_txt: {}'.format(delta_start_txt))
    delta_end_txt = ''
    if currently_running:
        end_date = utility.get_first_of_following_month(start_date)
        print('[format_tourney_start] retrieved end_date: {}'.format(end_date))
        end_date_formatted = util.get_formatted_date(end_date)
        print('[format_tourney_start] retrieved end_date_formatted: {}'.format(end_date_formatted))
        delta_end = end_date - utc_now
        print('[format_tourney_start] retrieved delta_end: {}'.format(delta_end))
        delta_end_formatted = util.get_formatted_timedelta(delta_end, False)
        print('[format_tourney_start] retrieved delta_end_formatted: {}'.format(delta_end_formatted))
        delta_end_txt = ' and goes on for another **{}** (until {})'.format(delta_end_formatted, end_date_formatted)
    result = 'Tournament in {} {} {}{}'.format(tourney_month, starts, delta_start_txt, delta_end_txt)
    print('- exiting format_tourney_start with result: {}'.format(result)) 
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
