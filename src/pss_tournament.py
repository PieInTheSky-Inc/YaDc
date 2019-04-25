#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# ----- Packages ------------------------------------------------------
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from datetime import date, datetime, time, timedelta, timezone

import argparse
import datetime
import os
import pandas as pd
import re
import urllib.request
import uuid
import xml.etree.ElementTree

import pss_core as core


base_url = 'http://{}/'.format(core.get_production_server())

# ----- Utility methods ---------------------------------------------------------
