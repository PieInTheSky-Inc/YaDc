from pss_entity import EntityRetriever





# ---------- Constants ----------

STARSYSTEM_DESIGN_BASE_PATH = 'GalaxyService/ListStarSystems?languageKey=en'
STARSYSTEM_DESIGN_KEY_NAME = 'StarSystemId'
STARSYSTEM_DESIGN_DESCRIPTION_PROPERTY_NAME = 'StarSystemTitle'

STARSYSTEMLINK_DESIGN_BASE_PATH = 'GalaxyService/ListStarSystems?languageKey=en'
STARSYSTEMLINK_DESIGN_KEY_NAME = 'StarSystemId'
STARSYSTEMLINK_DESIGN_DESCRIPTION_PROPERTY_NAME = 'StarSystemTitle'










# ---------- Initialization ----------

star_systems_designs_retriever: EntityRetriever = EntityRetriever(
    STARSYSTEM_DESIGN_BASE_PATH,
    STARSYSTEM_DESIGN_KEY_NAME,
    STARSYSTEM_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'StarSystemDesigns'
)

star_system_links_designs_retriever: EntityRetriever = EntityRetriever(
    STARSYSTEMLINK_DESIGN_BASE_PATH,
    STARSYSTEMLINK_DESIGN_KEY_NAME,
    STARSYSTEMLINK_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'StarSystemLinkDesigns'
)
