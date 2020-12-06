import pss_entity as entity


# ---------- Constants ----------

ACTION_TYPE_DESIGN_BASE_PATH: str = 'RoomService/ListActionTypes2?languageKey=en'
ACTION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'ActionTypeName'
ACTION_TYPE_DESIGN_KEY_NAME: str = 'ActionTypeId'

CONDITION_TYPE_DESIGN_BASE_PATH: str = 'RoomService/ListConditionTypes2?languageKey=en'
CONDITION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'ConditionTypeName'
CONDITION_TYPE_DESIGN_KEY_NAME: str = 'ConditionTypeId'





# ---------- Initialization ----------

action_types_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    ACTION_TYPE_DESIGN_BASE_PATH,
    ACTION_TYPE_DESIGN_KEY_NAME,
    ACTION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'ActionTypeDesigns'
)

condition_types_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    CONDITION_TYPE_DESIGN_BASE_PATH,
    CONDITION_TYPE_DESIGN_KEY_NAME,
    CONDITION_TYPE_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'ConditionTypeDesigns'
)