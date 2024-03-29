from . import pss_entity as entity


# ---------- Constants ----------

CRAFT_DESIGN_BASE_PATH: str = 'RoomService/ListCraftDesigns?languageKey=en'
CRAFT_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'CraftName'
CRAFT_DESIGN_KEY_NAME: str = 'CraftDesignId'





# ---------- Initialization ----------

crafts_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    CRAFT_DESIGN_BASE_PATH,
    CRAFT_DESIGN_KEY_NAME,
    CRAFT_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'CraftDesigns'
)