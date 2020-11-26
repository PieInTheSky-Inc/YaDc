from pss_entity import EntityRetriever





# ---------- Constants ----------

ACTION_TYPE_DESIGN_BASE_PATH = 'RoomService/ListActionTypes2?languageKey=en'
ACTION_TYPE_DESIGN_KEY_NAME = 'ActionTypeId'
ACTION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ActionTypeName'

CONDITION_TYPE_DESIGN_BASE_PATH = 'RoomService/ListConditionTypes2?languageKey=en'
CONDITION_TYPE_DESIGN_KEY_NAME = 'ConditionTypeId'
CONDITION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME = 'ConditionTypeName'










# ---------- Initialization ----------

action_types_designs_retriever: EntityRetriever = EntityRetriever(
    ACTION_TYPE_DESIGN_BASE_PATH,
    ACTION_TYPE_DESIGN_KEY_NAME,
    ACTION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'ActionTypeDesigns'
)

condition_types_designs_retriever: EntityRetriever = EntityRetriever(
    CONDITION_TYPE_DESIGN_BASE_PATH,
    CONDITION_TYPE_DESIGN_KEY_NAME,
    CONDITION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'ConditionTypeDesigns'
)
