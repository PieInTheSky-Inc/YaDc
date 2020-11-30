from pss_entity import EntityRetriever


# ---------- Constants ----------

MISSION_DESIGN_BASE_PATH = 'MissionService/ListAllMissionDesigns2?languageKey=en'
MISSION_DESIGN_KEY_NAME = 'MissionDesignId'
MISSION_DESIGN_DESCRIPTION_PROPERTY_NAME = 'MissionTitle'


# ---------- Initialization ----------

missions_designs_retriever: EntityRetriever = EntityRetriever(
    MISSION_DESIGN_BASE_PATH,
    MISSION_DESIGN_KEY_NAME,
    MISSION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'MissionDesigns'
)