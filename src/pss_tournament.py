#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from datetime import date, datetime, time, timedelta, timezone

import pss_core as core
import utility


base_url = 'http://{}/'.format(core.get_production_server())
a_week_prior = timedelta(-7)

# ----- Utility methods ---------------------------------------------------------
def get_current_tourney_start():
    first_of_next_month = utility.get_first_of_next_month()
    result = first_of_next_month + a_week_prior
    return result


def get_next_tourney_start():
    next_first_of_next_month = utility.get_first_of_following_month(utility.get_first_of_next_month())
    result = next_first_of_next_month + a_week_prior
    return result


def format_tourney_start(start_date, utcnow = None):
    if utcnow == None:
        utcnow = datetime.fromordinal(1)
    starts = 'starts'
    if start_date < utcnow:
        starts = 'started'
    formatted_date = utility.get_formatted_datetime(start_date)
    result = 'Tournament in {} {} on: {}'.format(start_date.strftime('%B'), starts, formatted_date)
    return result
