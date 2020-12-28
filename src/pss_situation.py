import pss_entity as entity

# ---------- Constants ----------

SITUATION_DESIGN_BASE_PATH: str = f'SituationService/ListSituationDesigns'
SITUATION_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'SituationName'
SITUATION_DESIGN_KEY_NAME: str = 'SituationId'





# ---------- Initialization ----------

situations_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    SITUATION_DESIGN_BASE_PATH,
    SITUATION_DESIGN_KEY_NAME,
    SITUATION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'SituationDesigns'
)