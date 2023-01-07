from datetime import timedelta
from typing import List, Optional, Union

from discord import Embed
from discord.ext.commands import Context

from . import pss_assert
from . import pss_core as core
from . import pss_entity as entity
from .pss_exception import NotFound
from . import pss_lookups as lookups
from . import pss_sprites as sprites
from . import settings
from .typehints import EntitiesData, EntityInfo
from . import utils


# ---------- Constants ----------

BIG_SET_THRESHOLD: int = 4

RESEARCH_DESIGN_BASE_PATH: str = 'ResearchService/ListAllResearchDesigns2?languageKey=en'
RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'ResearchName'
RESEARCH_DESIGN_KEY_NAME: str = 'ResearchDesignId'





# ---------- Research info ----------

def get_research_details_by_id(research_design_id: str, researches_data: EntitiesData) -> entity.EntityDetails:
    if research_design_id:
        if research_design_id and research_design_id in researches_data.keys():
            research_info = researches_data[research_design_id]
            research_details = __create_research_details_from_info(research_info, researches_data)
            return research_details
    return None


async def get_research_infos_by_name(research_name: str, ctx: Context, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(research_name)

    researches_data = await researches_designs_retriever.get_data_dict3()
    researches_designs_infos = await researches_designs_retriever.get_entities_infos_by_name(research_name, entities_data=researches_data, sorted_key_function=__get_key_for_research_sort)

    if not researches_designs_infos:
        raise NotFound(f'Could not find a research named **{research_name}**.')
    else:
        exact_match_details = None
        exact_research_info = None
        big_set_threshold = BIG_SET_THRESHOLD
        if len(researches_designs_infos) >= big_set_threshold:
            lower_research_name = research_name.strip().lower()
            for research_design_info in researches_designs_infos:
                if research_design_info.get(RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME, '').lower() == lower_research_name:
                    exact_research_info = research_design_info
                    break

        if exact_research_info:
            researches_designs_infos = [research_design_info for research_design_info in researches_designs_infos if research_design_info[RESEARCH_DESIGN_KEY_NAME] != exact_research_info[RESEARCH_DESIGN_KEY_NAME]]
            exact_match_details = __create_research_details_from_info(exact_research_info, researches_data)
            big_set_threshold -= 1
        researches_details = __create_researches_details_collection_from_infos(researches_designs_infos, researches_data)

        result = []
        if as_embed:
            if exact_match_details:
                result.append(await exact_match_details.get_details_as_embed(ctx))
            result.extend(await researches_details.get_entities_details_as_embed(ctx, big_set_threshold=big_set_threshold))
        else:
            if exact_match_details:
                result.extend(await exact_match_details.get_details_as_text(details_type=entity.EntityDetailsType.LONG))
                result.append(utils.discord.ZERO_WIDTH_SPACE)
            result.extend(await researches_details.get_entities_details_as_text(big_set_threshold=big_set_threshold))
        return result





# ---------- Transformation functions ----------

def __get_costs(research_info: EntityInfo, researches_data: EntitiesData, **kwargs) -> Optional[str]:
    bux_cost = int(research_info['StarbuxCost'])
    gas_cost = int(research_info['GasCost'])

    if bux_cost:
        cost = bux_cost
        currency = 'starbux'
    elif gas_cost:
        cost = gas_cost
        currency = 'gas'
    else:
        cost = 0
        currency = ''

    cost_reduced, cost_multiplier = utils.format.get_reduced_number(cost)
    currency_emoji = lookups.CURRENCY_EMOJI_LOOKUP.get(currency, '')
    result = f'{cost_reduced}{cost_multiplier} {currency_emoji}'
    return result


def __get_duration(research_info: EntityInfo, researches_data: EntitiesData, **kwargs) -> Optional[str]:
    seconds = int(research_info['ResearchTime'])
    result = utils.format.timedelta(timedelta(seconds=seconds), include_relative_indicator=False)
    return result


def __get_required_research_name(research_info: EntityInfo, researches_data: EntitiesData, **kwargs) -> Optional[str]:
    required_research_design_id = research_info['RequiredResearchDesignId']
    if required_research_design_id != '0':
        result = researches_data[required_research_design_id][RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    else:
        result = None
    return result





# ---------- Helper functions ----------

def __get_key_for_research_sort(research_info: EntityInfo, researches_data: EntitiesData) -> str:
    result = ''
    parent_infos = __get_parents(research_info, researches_data)
    if parent_infos:
        for parent_info in parent_infos:
            result += parent_info[RESEARCH_DESIGN_KEY_NAME].zfill(4)
    result += research_info[RESEARCH_DESIGN_KEY_NAME].zfill(4)
    return result


def __get_parents(research_info: EntityInfo, researches_data: EntitiesData) -> List[EntityInfo]:
    parent_research_design_id = research_info['RequiredResearchDesignId']
    if parent_research_design_id == '0':
        parent_research_design_id = None

    if parent_research_design_id is not None:
        parent_info = researches_data[parent_research_design_id]
        result = __get_parents(parent_info, researches_data)
        result.append(parent_info)
        return result
    else:
        return []


def get_research_name_from_id(research_id: str, researches_data: EntitiesData) -> Optional[str]:
    if research_id != '0':
        research_info = researches_data[research_id]
        return research_info[RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME]
    else:
        return None





# ---------- Create entity.EntityDetails ----------

def __create_research_details_from_info(research_info: EntityInfo, researches_data: EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(research_info, __properties['title'], __properties['description'], __properties['properties'], __properties['embed_settings'], researches_data)


def __create_researches_details_collection_from_infos(researches_designs_infos: List[EntityInfo], researches_data: EntitiesData) -> entity.EntityDetailsCollection:
    researches_details = [__create_research_details_from_info(item_info, researches_data) for item_info in researches_designs_infos]
    result = entity.EntityDetailsCollection(researches_details, big_set_threshold=BIG_SET_THRESHOLD)
    return result





# ---------- Initilization ----------

researches_designs_retriever = entity.EntityRetriever(
    RESEARCH_DESIGN_BASE_PATH,
    RESEARCH_DESIGN_KEY_NAME,
    RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='ResearchDesigns'
)

__properties: entity.EntityDetailsCreationPropertiesCollection = {
    'title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=RESEARCH_DESIGN_DESCRIPTION_PROPERTY_NAME)
    ),
    'description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='ResearchDescription'),
        property_short=entity.NO_PROPERTY
    ),
    'properties': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Cost', True, transform_function=__get_costs),
            entity.EntityDetailProperty('Duration', True, transform_function=__get_duration),
            entity.EntityDetailProperty('Required LAB lvl', True, entity_property_name='RequiredLabLevel'),
            entity.EntityDetailProperty('Required Research', True, transform_function=__get_required_research_name)
        ],
        properties_medium=[
            entity.EntityDetailProperty('Cost', False, transform_function=__get_costs),
            entity.EntityDetailProperty('Duration', False, transform_function=__get_duration),
            entity.EntityDetailProperty('LAB lvl', True, entity_property_name='RequiredLabLevel')
        ],
        properties_mini=[]
    ),
    'embed_settings': {
        'thumbnail_url': entity.EntityDetailProperty('thumbnail_url', False, entity_property_name='LogoSpriteId', transform_function=sprites.get_download_sprite_link_by_property)
    }
}