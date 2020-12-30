from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from discord import Embed
from discord.ext.commands import Context

import emojis
import pss_core as core
import pss_crew as crew
import pss_entity as entity
from pss_exception import Error, NotFound
import pss_item as item
import pss_mission as mission
import pss_research as research
import pss_room as room
import pss_sprites as sprites
import pss_training as training
import resources
import settings
from typehints import EntitiesData, EntityInfo
import utils


# ---------- Constants ----------

SITUATION_DESIGN_BASE_PATH: str = f'SituationService/ListSituationDesigns'
SITUATION_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'SituationName'
SITUATION_DESIGN_KEY_NAME: str = 'SituationDesignId'

SITUATION_CHANGE_TYPE_LOOKUP: Dict[str, str] = {
    'AddCrew': 'Additional crew on board',
    'AddEXP': 'EXP event',
    'AddLeagueBonusGas': f'Gas event',
    'AddLoot': 'Item drop',
}

SITUATION_CHANGE_TYPE_TITLE_LOOKUP: Dict[str, str] = {
    'AddCrew': 'Crew added to ship',
    'AddEXP': 'Extra EXP',
    'AddLeagueBonusGas': f'Extra {emojis.pss_gas_big} from league bonus',
    'AddLoot': 'Item dropped',
}

SITUATION_TRIGGER_TYPE_LOOKUP: Dict[str, str] = {
    'None': None,
    'PvP': 'Win a PvP battle',
    'ScanShip': 'Scan a ship',
}





# ---------- Event info ----------

def get_event_details_by_id(situation_design_id: str, situations_data: EntitiesData) -> entity.entity.EntityDetails:
    if situation_design_id:
        if situation_design_id and situation_design_id in situations_data.keys():
            return __create_situation_details_from_info(situations_data[situation_design_id], situations_data)
    return None


async def get_event_details(ctx: Context, situation_id: str = None, all_events: bool = False, latest_only: bool = False, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    has_situation_id = entity.entity_property_has_value(situation_id)
    if has_situation_id and all_events or has_situation_id and latest_only or all_events and latest_only:
        raise ValueError(f'Only one of these parameters may be True: situation_id, all_events, latest_only')
    utc_now = utils.get_utc_now()
    situations_data = await situations_designs_retriever.get_data_dict3()
    situation_infos = sorted(situations_data.values(), key=lambda x: (utils.parse.pss_datetime(x['EndDate']), -int(x[SITUATION_DESIGN_KEY_NAME])), reverse=True)

    if situation_id:
        situation_infos = [situations_data[situation_id]]
    elif all_events:
        situation_infos = list(situations_data.values())
    elif latest_only:
        situation_infos = [situation_infos[0]]
    else:
        situation_infos = __get_current_situation_infos(situations_data, utc_now)

    if not situation_infos:
        if all_events:
            raise NotFound(f'There\'s no event data.')
        else:
            raise NotFound(f'There\'s no event running currently.')
    else:
        situations_details_collection = __create_situations_details_collection_from_infos(situation_infos, situations_data, utc_now=utc_now)
        if as_embed:
            return (await situations_details_collection.get_entities_details_as_embed(ctx))
        else:
            return (await situations_details_collection.get_entities_details_as_text())


async def __get_event_reward(change_type: str, change_argument: str, for_embed: Optional[bool] = False) -> Optional[str]:
    if for_embed is None:
        for_embed = False
    result = None
    reward_amount = None
    reward_details = None
    if entity.entity_property_has_value(change_argument):
        entity_type, entity_id, reward_amount, _ = utils.parse.entity_string(change_argument, default_amount=None)
        if entity_type == 'character':
            characters_data = await crew.characters_designs_retriever.get_data_dict3()
            collections_data = await crew.collections_designs_retriever.get_data_dict3()
            reward_details = crew.get_char_details_by_id(entity_id, characters_data, collections_data)
        elif entity_type == 'item':
            items_data = await item.items_designs_retriever.get_data_dict3()
            reward_details = item.get_item_details_by_id(entity_id, items_data, None)
        else:
            reward_amount = change_argument
    if reward_details:
        details_text = "".join(await reward_details.get_details_as_text(entity.EntityDetailsType.MINI, for_embed=for_embed))
        if reward_amount:
            result = f'{reward_amount}x {details_text}'
        else:
            result = details_text
    elif change_type == 'AddLeagueBonusGas':
        result = f'+{reward_amount} % {emojis.pss_gas_big} from league bonus'
    elif change_type == 'AddEXP':
        result = f'{reward_amount} % exp from battles'
    else:
        result = change_argument
    return result





# ---------- Transformation functions ----------

async def __get_event_type_and_reward(situation_info: EntityInfo, situations_data: EntitiesData, **kwargs) -> Optional[str]:
    for_embed = kwargs.get('for_embed', False)
    change_argument = situation_info.get('ChangeArgumentString')
    change_type = situation_info.get('ChangeType')
    reward = await __get_event_reward(change_type, change_argument, for_embed=for_embed)
    result = f'{SITUATION_CHANGE_TYPE_LOOKUP.get(change_type)}: {reward}'
    return result


def __get_situation_chance(situation_info: EntityInfo, situations_data: EntitiesData, **kwargs) -> Optional[str]:
    chance = situation_info.get('Chance')
    if entity.entity_property_has_value(chance):
        result = f'{chance} %'
    else:
        result = None
    return result


async def __get_situation_requirements(situation_info: EntityInfo, situations_data: EntitiesData, **kwargs) -> Optional[str]:
    for_embed = kwargs.get('for_embed', False)
    requirement_str = situation_info.get('RequirementString')
    requirements = utils.parse.requirement_string(requirement_str)
    result = None
    if len(requirements) > 1 and all(entity_type == 'shiplevel' for entity_type, _, _, _ in requirements):
        min_level = min(entity_amount for _, _, entity_amount, _ in requirements)
        max_level = max(entity_amount for _, _, entity_amount, _ in requirements)
        result = f'Ship level {min_level} to {max_level} (inclusive)'
    else:
        results = []
        for entity_type, entity_id, entity_amount, entity_amount_modifier in requirements:
            details = None
            entity_details = None
            if entity_type == 'mission':
                missions_data = await mission.missions_designs_retriever.get_data_dict3()
                entity_info = missions_data[entity_id]
                details = f'Mission "{entity_info[mission.MISSION_DESIGN_DESCRIPTION_PROPERTY_NAME]}" completed'
            if entity_type == 'room':
                rooms_data = await room.rooms_designs_retriever.get_data_dict3()
                entity_details = room.get_room_details_by_id(entity_id, rooms_data, None, None, None)
            elif entity_type == 'shiplevel':
                resource_key = f'AMOUNTMODIFIER{entity_amount_modifier}'
                details = f'Ship level {entity_amount}{resources.get_resource(resource_key)}'

            if entity_details:
                details = "".join(await entity_details.get_details_as_text(entity.EntityDetailsType.MINI, for_embed=for_embed))
            if details:
                results.append(details)
        result = utils.format.get_and_list(results, emphasis='**') or None
    return result


def __get_situation_trigger(situation_info: EntityInfo, situations_data: EntitiesData, **kwargs) -> Optional[str]:
    trigger_type = situation_info.get('TriggerType')
    if entity.entity_property_has_value(trigger_type):
        return SITUATION_TRIGGER_TYPE_LOOKUP.get(trigger_type, trigger_type)
    return None





# ---------- Create entity.entity.EntityDetails ----------

def __create_situation_details_from_info(situation_info: EntityInfo, situations_data: EntitiesData, utc_now: datetime = None) -> entity.entity.EntityDetails:
    return entity.entity.EntityDetails(situation_info, __properties['title'], __properties['description'], __properties['properties'], __properties['embed_settings'], situations_data, utc_now=utc_now)


def __create_situations_details_collection_from_infos(situations_designs_infos: List[EntityInfo], situations_data: EntitiesData, utc_now: datetime = None) -> entity.EntityDetailsCollection:
    situations_details = [__create_situation_details_from_info(situation_info, situations_data, utc_now=utc_now) for situation_info in situations_designs_infos]
    result = entity.EntityDetailsCollection(situations_details, big_set_threshold=0)
    return result





# ---------- Helper functions ----------

def __get_current_situation_infos(situations_infos: List[EntityInfo], utc_now: datetime) -> List[EntityInfo]:
    result = []
    for situation_info in situations_infos:
        from_date = situation_info.get('FromDate')
        end_date = situation_info.get('EndDate')
        if from_date and end_date:
            start_at = utils.parse.pss_datetime(from_date)
            end_at = utils.parse.pss_datetime(end_date)
            if start_at <= utc_now and end_at > utc_now:
                result.append(situation_info)
    return result





# ---------- Initilization ----------

situations_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    SITUATION_DESIGN_BASE_PATH,
    SITUATION_DESIGN_KEY_NAME,
    SITUATION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'SituationDesigns'
)


__properties: entity.EntityDetailsCreationPropertiesCollection = {
    'title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=SITUATION_DESIGN_DESCRIPTION_PROPERTY_NAME)
    ),
    'description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='SituationDescription')
    ),
    'properties': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Event type', True, transform_function=__get_event_type_and_reward, embed_only=True, for_embed=True, display_inline_for_embeds=False),
            entity.EntityDetailProperty('Event type', True, transform_function=__get_event_type_and_reward, text_only=True),
            entity.EntityDetailProperty('Chance', True, transform_function=__get_situation_chance),
            entity.EntityDetailProperty('Limit per day', True, entity_property_name='DailyOccurrenceLimit', transform_function=core.transform_get_value),
            entity.EntityDetailProperty('Triggered by', True, entity_property_name='TriggerType', transform_function=__get_situation_trigger),
            entity.EntityDetailProperty('Requirement', True, entity_property_name='RequirementString', transform_function=__get_situation_requirements, embed_only=True, for_embed=True, display_inline_for_embeds=False),
            entity.EntityDetailProperty('Requirement', True, entity_property_name='RequirementString', transform_function=__get_situation_requirements, text_only=True),
            entity.EntityDetailProperty('Starts at', True, entity_property_name='FromDate', transform_function=core.transform_pss_datetime_with_timespan, display_inline_for_embeds=False, omit_time_if_zero=True, include_seconds_in_timespan=False),
            entity.EntityDetailProperty('Ends at', True, entity_property_name='EndDate', transform_function=core.transform_pss_datetime_with_timespan, display_inline_for_embeds=False, omit_time_if_zero=True, include_seconds_in_timespan=False),
        ],
        properties_mini=[]
        ),
    'embed_settings': {
        'icon_url': entity.EntityDetailProperty('icon_url', False, entity_property_name='IconSpriteId', transform_function=sprites.get_download_sprite_link_by_property),
    }
}





async def init() -> None:
    pass