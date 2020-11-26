from pss_entity import EntityRetriever





# ---------- Constants ----------

ACHIEVEMENT_DESIGN_BASE_PATH = 'AchievementService/ListAchievementDesigns2?languageKey=en'
ACHIEVEMENT_DESIGN_KEY_NAME = 'AchievementDesignId'
ACHIEVEMENT_DESIGN_DESCRIPTION_PROPERTY_NAME = 'AchievementTitle'










# ---------- Initialization ----------

achievements_designs_retriever: EntityRetriever = EntityRetriever(
    ACHIEVEMENT_DESIGN_BASE_PATH,
    ACHIEVEMENT_DESIGN_KEY_NAME,
    ACHIEVEMENT_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'AchievementDesigns'
)
