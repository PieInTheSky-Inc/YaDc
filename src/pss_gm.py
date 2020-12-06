import pss_entity as entity


# ---------- Constants ----------

STARSYSTEM_DESIGN_BASE_PATH: str = 'GalaxyService/ListStarSystems?languageKey=en'
STARSYSTEM_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'StarSystemTitle'
STARSYSTEM_DESIGN_KEY_NAME: str = 'StarSystemId'

STARSYSTEMLINK_DESIGN_BASE_PATH: str = 'GalaxyService/ListStarSystems?languageKey=en'
STARSYSTEMLINK_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'StarSystemTitle'
STARSYSTEMLINK_DESIGN_KEY_NAME: str = 'StarSystemId'





# ---------- Initialization ----------

star_systems_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    STARSYSTEM_DESIGN_BASE_PATH,
    STARSYSTEM_DESIGN_KEY_NAME,
    STARSYSTEM_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'StarSystemDesigns'
)

star_system_links_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    STARSYSTEMLINK_DESIGN_BASE_PATH,
    STARSYSTEMLINK_DESIGN_KEY_NAME,
    STARSYSTEMLINK_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'StarSystemLinkDesigns'
)