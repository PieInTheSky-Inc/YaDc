from . import pss_entity as entity


# ---------- Constants ----------

MISSION_DESIGN_BASE_PATH: str = 'MissionService/ListAllMissionDesigns2?languageKey=en'
MISSION_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'MissionTitle'
MISSION_DESIGN_KEY_NAME: str = 'MissionDesignId'





# ---------- Initialization ----------

missions_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    MISSION_DESIGN_BASE_PATH,
    MISSION_DESIGN_KEY_NAME,
    MISSION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'MissionDesigns'
)