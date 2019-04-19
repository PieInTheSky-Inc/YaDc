#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# PSS Toolkit API


# ----- Packages ------------------------------------------------------
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import datetime
import pss_core as core
import utility as util


base_url = 'http://{}/'.format(core.get_production_server())


def get_fleet_spreadsheet(ctx, fleet_name):
    txt = '#fleet {}'.format(fleet_name)
    return str(USER_PSS_TOOLKIT)
