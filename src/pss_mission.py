#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import discord
import os
import re
from typing import Callable, Dict, List, Optional, Tuple, Union

import pss_assert
from cache import PssCache
import pss_core as core
import pss_entity as entity
import pss_lookups as lookups
import resources
import settings
import utility as util





# ---------- Constants ----------

MISSION_DESIGN_BASE_PATH = 'MissionService/ListAllMissionDesigns2?languageKey=en'
MISSION_DESIGN_KEY_NAME = 'MissionDesignId'
MISSION_DESIGN_DESCRIPTION_PROPERTY_NAME = 'MissionTitle'










# ---------- Initialization ----------

missions_designs_retriever: entity.EntityDesignsRetriever = entity.EntityDesignsRetriever(
    MISSION_DESIGN_BASE_PATH,
    MISSION_DESIGN_KEY_NAME,
    MISSION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'MissionDesigns'
)
