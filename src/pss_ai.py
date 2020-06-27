#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import pss_entity as entity





# ---------- Constants ----------

ACTION_TYPE_DESIGN_BASE_PATH = 'RoomService/ListActionTypes2?languageKey=en'
ACTION_TYPE_DESIGN_KEY_NAME = 'ActionTypeId'
ACTION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ActionTypeName'

CONDITION_TYPE_DESIGN_BASE_PATH = 'RoomService/ListConditionTypes2?languageKey=en'
CONDITION_TYPE_DESIGN_KEY_NAME = 'ConditionTypeId'
CONDITION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ConditionTypeName'










# ---------- Initialization ----------

action_types_designs_retriever: entity.EntityDesignsRetriever = entity.EntityDesignsRetriever(
    ACTION_TYPE_DESIGN_BASE_PATH,
    ACTION_TYPE_DESIGN_KEY_NAME,
    ACTION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'ActionTypeDesigns'
)

condition_types_designs_retriever: entity.EntityDesignsRetriever = entity.EntityDesignsRetriever(
    CONDITION_TYPE_DESIGN_BASE_PATH,
    CONDITION_TYPE_DESIGN_KEY_NAME,
    CONDITION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'ConditionTypeDesigns'
)
