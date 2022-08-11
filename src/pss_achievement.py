from . import pss_entity as entity


# ---------- Constants ----------

ACHIEVEMENT_DESIGN_BASE_PATH: str = 'AchievementService/ListAchievementDesigns2?languageKey=en'
ACHIEVEMENT_DESIGN_KEY_NAME: str = 'AchievementDesignId'
ACHIEVEMENT_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'AchievementTitle'


# ---------- Initialization ----------

achievements_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    ACHIEVEMENT_DESIGN_BASE_PATH,
    ACHIEVEMENT_DESIGN_KEY_NAME,
    ACHIEVEMENT_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'AchievementDesigns'
)