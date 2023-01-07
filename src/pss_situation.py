from datetime import datetime
from typing import Dict, List, Optional, Union

from discord import Embed
from discord.ext.commands import Context

from . import emojis
from . import pss_core as core
from . import pss_crew as crew
from . import pss_entity as entity
from .pss_exception import NotFound
from . import pss_item as item
from . import pss_mission as mission
from . import pss_room as room
from . import pss_sprites as sprites
from . import resources
from . import settings
from .typehints import EntitiesData, EntityInfo
from . import utils


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

def get_event_details_by_id(situation_design_id: str, situations_data: EntitiesData) -> entity.EntityDetails:
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
    situation_infos = sorted(situations_data.values(), key=lambda x: (utils.parse.pss_datetime(x['EndDate']), int(x[SITUATION_DESIGN_KEY_NAME])), reverse=True)

    if situation_id:
        situation_infos = [situations_data[situation_id]]
    elif all_events:
        situation_infos.reverse()
    elif latest_only:
        if __get_is_event_running(situation_infos[0], utc_now):
            situation_infos = [situation_infos[1]]
        else:
            situation_infos = [situation_infos[0]]
    else:
        situation_infos = __get_current_situations_infos(situations_data.values(), utc_now)

    if not situation_infos:
        if all_events:
            raise NotFound(f'There\'s no event data.')
        else:
            raise NotFound(f'There\'s no event running currently.')
    else:
        chars_data = await crew.characters_designs_retriever.get_data_dict3()
        collections_data = await crew.collections_designs_retriever.get_data_dict3()
        items_data = await item.items_designs_retriever.get_data_dict3()
        missions_data = await mission.missions_designs_retriever.get_data_dict3()
        rooms_data = await room.rooms_designs_retriever.get_data_dict3()

        situations_details_collection = __create_situations_details_collection_from_infos(situation_infos, situations_data, chars_data, collections_data, items_data, missions_data, rooms_data, utc_now=utc_now)
        if as_embed:
            return (await situations_details_collection.get_entities_details_as_embed(ctx))
        else:
            return (await situations_details_collection.get_entities_details_as_text())


async def get_current_events_details(situations_data: EntitiesData, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, missions_data: EntitiesData, rooms_data: EntitiesData, utc_now: datetime) -> List[entity.EntityDetails]:
    current_situations_infos = __get_current_situations_infos(situations_data.values(), utc_now)
    result = __create_situations_details_list_from_infos(current_situations_infos, situations_data, chars_data, collections_data, items_data, missions_data, rooms_data, utc_now)
    return result


async def __get_event_reward(change_type: str, change_argument: str, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, for_embed: Optional[bool] = False) -> Optional[str]:
    if for_embed is None:
        for_embed = False
    result = None
    reward_amount = None
    reward_details = None
    if entity.entity_property_has_value(change_argument):
        entity_type, entity_id, reward_amount, _ = utils.parse.entity_string(change_argument, default_amount=None)
        if entity_type == 'character':
            reward_details = crew.get_char_details_by_id(entity_id, chars_data, collections_data)
        elif entity_type == 'item':
            reward_details = item.get_item_details_by_id(entity_id, items_data, None)
        else:
            reward_amount = int(change_argument)
    if reward_details:
        details_text = "".join(await reward_details.get_details_as_text(entity.EntityDetailsType.MINI, for_embed=for_embed))
        if reward_amount:
            result = f'{reward_amount}x {details_text}'
        else:
            result = details_text
    elif change_type == 'AddLeagueBonusGas':
        result = f'{reward_amount+100} % league bonus for {emojis.pss_gas_big}'
    elif change_type == 'AddEXP':
        result = f'{reward_amount} % exp from battles'
    else:
        result = change_argument
    return result


def __get_is_event_running(situation_info: EntityInfo, utc_now: datetime) -> bool:
    starts = utils.parse.pss_datetime(situation_info['FromDate'])
    ends = utils.parse.pss_datetime(situation_info['EndDate'])
    return starts <= utc_now and ends >= utc_now





# ---------- Transformation functions ----------

async def __get_event_type_and_reward(situation_info: EntityInfo, situations_data: EntitiesData, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, missions_data: EntitiesData, rooms_data: EntitiesData, **kwargs) -> Optional[str]:
    for_embed = kwargs.get('for_embed', False)
    change_argument = situation_info.get('ChangeArgumentString')
    change_type = situation_info.get('ChangeType')
    reward = await __get_event_reward(change_type, change_argument, chars_data, collections_data, items_data, for_embed=for_embed)
    result = f'{SITUATION_CHANGE_TYPE_LOOKUP.get(change_type)}: {reward}'
    return result


def __get_situation_chance(situation_info: EntityInfo, situations_data: EntitiesData, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, missions_data: EntitiesData, rooms_data: EntitiesData, **kwargs) -> Optional[str]:
    chance = situation_info.get('Chance')
    if entity.entity_property_has_value(chance):
        result = f'{chance} %'
    else:
        result = None
    return result


async def __get_situation_requirements(situation_info: EntityInfo, situations_data: EntitiesData, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, missions_data: EntitiesData, rooms_data: EntitiesData, **kwargs) -> Optional[str]:
    for_embed = kwargs.get('for_embed', False)
    requirement_str = situation_info.get('RequirementString')
    requirements = utils.parse.requirement_string(requirement_str)
    result = None
    if len(requirements) > 1 and all(entity_type == 'shiplevel' for entity_type, _, _, _ in requirements):
        levels = [entity_amount for _, _, entity_amount, _ in requirements]
        result = f'Ship level {min(levels)} to {max(levels)} (inclusive)'
    else:
        results = []
        for entity_type, entity_id, entity_amount, entity_amount_modifier in requirements:
            details = None
            entity_details = None
            if entity_type == 'mission':
                entity_info = missions_data[entity_id]
                details = f'Mission "{entity_info[mission.MISSION_DESIGN_DESCRIPTION_PROPERTY_NAME]}" completed'
            if entity_type == 'room':
                entity_details = room.get_room_details_by_id(entity_id, rooms_data, None, None, None)
            elif entity_type == 'shiplevel':
                resource_key = f'AMOUNTMODIFIER{entity_amount_modifier}'
                details = f'Ship level {entity_amount}{resources.get_resource(resource_key)}'

            if entity_details:
                details = ''.join(await entity_details.get_details_as_text(entity.EntityDetailsType.MINI, for_embed=for_embed))
            if details:
                results.append(details)
        result = utils.format.get_and_list(results, emphasis='**') or None
    return result


def __get_situation_trigger(situation_info: EntityInfo, situations_data: EntitiesData, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, missions_data: EntitiesData, rooms_data: EntitiesData, **kwargs) -> Optional[str]:
    trigger_type = situation_info.get('TriggerType')
    if entity.entity_property_has_value(trigger_type):
        return SITUATION_TRIGGER_TYPE_LOOKUP.get(trigger_type, trigger_type)
    return None





# ---------- Create entity.entity.EntityDetails ----------

def __create_situation_details_from_info(situation_info: EntityInfo, situations_data: EntitiesData, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, missions_data: EntitiesData, rooms_data: EntitiesData, utc_now: datetime = None) -> entity.entity.EntityDetails:
    return entity.entity.EntityDetails(situation_info, __properties['title'], __properties['description'], __properties['properties'], __properties['embed_settings'], situations_data, chars_data, collections_data, items_data, missions_data, rooms_data, utc_now=utc_now)


def __create_situations_details_list_from_infos(situations_designs_infos: List[EntityInfo], situations_data: EntitiesData, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, missions_data: EntitiesData, rooms_data: EntitiesData, utc_now: datetime = None) -> List[entity.EntityDetails]:
    result = [__create_situation_details_from_info(situation_info, situations_data, chars_data, collections_data, items_data, missions_data, rooms_data, utc_now=utc_now) for situation_info in situations_designs_infos]
    return result


def __create_situations_details_collection_from_infos(situations_designs_infos: List[EntityInfo], situations_data: EntitiesData, chars_data: EntitiesData, collections_data: EntitiesData, items_data: EntitiesData, missions_data: EntitiesData, rooms_data: EntitiesData, utc_now: datetime = None) -> entity.EntityDetailsCollection:
    situations_details = __create_situations_details_list_from_infos(situations_designs_infos, situations_data, chars_data, collections_data, items_data, missions_data, rooms_data, utc_now=utc_now)
    result = entity.EntityDetailsCollection(situations_details, big_set_threshold=0)
    return result





# ---------- Helper functions ----------

def __get_current_situations_infos(situations_infos: List[EntityInfo], utc_now: datetime) -> List[EntityInfo]:
    result = []
    for situation_info in situations_infos:
        from_date = situation_info.get('FromDate')
        end_date = situation_info.get('EndDate')
        if from_date and end_date:
            start_at = utils.parse.pss_datetime(from_date)
            end_at = utils.parse.pss_datetime(end_date)
            if start_at <= utc_now and end_at > utc_now:
                situation_info['from_date'] = from_date
                situation_info['end_date'] = end_date
                result.append(situation_info)
    result = sorted(result, key=lambda x: (x['end_date'], x['from_date'], int(x[SITUATION_DESIGN_KEY_NAME])), reverse=True)
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
        properties_medium=[
            entity.EntityDetailProperty('Ends at', True, entity_property_name='EndDate', transform_function=core.transform_pss_datetime_with_timespan, display_inline_for_embeds=False, omit_time_if_zero=True, include_seconds_in_timespan=False)
        ],
        properties_mini=[]
        ),
    'embed_settings': {
        'icon_url': entity.EntityDetailProperty('icon_url', False, entity_property_name='IconSpriteId', transform_function=sprites.get_download_sprite_link_by_property),
    }
}





async def init() -> None:
    pass