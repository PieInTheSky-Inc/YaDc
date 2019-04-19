#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import datetime
import pss_core as core
import pss_prestige as p
import pss_research as rs
import xml.etree.ElementTree


base_url = 'http://{}/'.format(core.get_production_server())

