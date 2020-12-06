from typing import List, Optional, Tuple, Union

from discord import Embed
from discord.ext.commands import Context

import emojis
import pss_assert
import pss_entity as entity
from pss_exception import Error
import pss_item as item
import pss_lookups as lookups
import pss_research as research
import pss_sprites as sprites
import settings
import utils


# ---------- Constants ----------

BASE_STATS: List[str] = lookups.STATS_LEFT + lookups.STATS_RIGHT

TRAINING_DESIGN_BASE_PATH: str = 'TrainingService/ListAllTrainingDesigns2?languageKey=en'
TRAINING_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'TrainingName'
TRAINING_DESIGN_KEY_NAME: str = 'TrainingDesignId'





# ---------- Training info ----------

async def get_training_details_from_id(training_id: str, trainings_data: entity.EntitiesData, items_data: entity.EntitiesData = None, researches_data: entity.EntitiesData = None) -> entity.EntityDetails:
    if not items_data:
        items_data = await item.items_designs_retriever.get_data_dict3()
    if not researches_data:
        researches_data = await research.researches_designs_retriever.get_data_dict3()
    training_info = trainings_data[training_id]
    result = __create_training_details_from_info(training_info, trainings_data, items_data, researches_data)
    return result


async def get_training_details_from_name(training_name: str, ctx: Context, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(training_name)

    trainings_data = await trainings_designs_retriever.get_data_dict3()
    training_infos = await trainings_designs_retriever.get_entities_infos_by_name(training_name, trainings_data)

    if not training_infos:
        raise Error(f'Could not find a training named **{training_name}**.')
    else:
        items_data = await item.items_designs_retriever.get_data_dict3()
        researches_data = await research.researches_designs_retriever.get_data_dict3()
        trainings_details_collection = __create_trainings_details_collection_from_infos(training_infos, trainings_data, items_data, researches_data)
        custom_footer = 'The stats displayed are chances. The actual result may be much lower depending on: max training points, training points used, the training points gained on a particular stat and fatigue.'

        if as_embed:
            return (await trainings_details_collection.get_entities_details_as_embed(ctx, custom_detail_property_separator='\n', custom_footer_text=custom_footer))
        else:
            return (await trainings_details_collection.get_entities_details_as_text(custom_footer_text=custom_footer))





# ---------- Transformation functions ----------

def __get_costs(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData, **kwargs) -> Optional[str]:
    cost = int(training_info['MineralCost'])
    if cost:
        cost_compact = utils.format.get_reduced_number_compact(cost)
        result = f'{cost_compact} {emojis.pss_min_big}'
    else:
        result = None
    return result


def __get_duration(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData, **kwargs) -> Optional[str]:
    seconds = int(training_info['Duration'])
    if seconds:
        result = utils.format.duration(seconds, include_relative_indicator=False)
    else:
        result = 'Instant'
    return result


def __get_fatigue(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData, **kwargs) -> Optional[str]:
    fatigue = int(training_info['Fatigue'])
    if fatigue:
        result = f'{fatigue}h'
    else:
        result = None
    return result


def __get_required_research(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData, **kwargs) -> Optional[str]:
    required_research_id = training_info['RequiredResearchDesignId']
    result = research.get_research_name_from_id(required_research_id, researches_data)
    return result


def __get_stat_chances(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData, **kwargs) -> Optional[str]:
    add_line_breaks = kwargs.get('add_line_breaks', False)
    chances = []
    max_chance_value = 0
    result = []
    for stat_name in BASE_STATS:
        stat_chance = __get_stat_chance(stat_name, training_info)
        if stat_chance is not None:
            chances.append(stat_chance)

    if chances:
        chance_values = [stat_chance[2] for stat_chance in chances]
        max_chance_value = max(chance_values)
        result = [__get_stat_chance_as_text(*stat_chance) for stat_chance in chances if stat_chance[2] == max_chance_value]
        result.extend([__get_stat_chance_as_text(*stat_chance) for stat_chance in chances if stat_chance[2] != max_chance_value])

    xp_stat_chance = __get_stat_chance('Xp', training_info, guaranteed=True)
    result.append(__get_stat_chance_as_text(*xp_stat_chance))

    separator = '\n' if add_line_breaks else ' '
    return separator.join(result)


async def __get_thumbnail_url(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData, **kwargs) -> Optional[str]:
    training_sprite_id = training_info.get('TrainingSpriteId')
    sprite_id = None
    if entity.entity_property_has_value(training_sprite_id) and training_sprite_id != '454':
        sprite_id = training_sprite_id
    else:
        training_id = training_info.get(TRAINING_DESIGN_KEY_NAME)
        item_details = item.get_item_details_by_training_id(training_id, items_data, trainings_data)
        if item_details:
            item_sprite_id = item_details[0].entity_info.get('ImageSpriteId')
            if entity.entity_property_has_value(item_sprite_id):
                sprite_id = item_sprite_id
    if sprite_id:
        result = await sprites.get_download_sprite_link(sprite_id)
    else:
        result = None
    return result


async def __get_training_item_name(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData, **kwargs) -> Optional[str]:
    training_id = training_info[TRAINING_DESIGN_KEY_NAME]
    items_details = item.get_item_details_by_training_id(training_id, items_data, trainings_data)
    result = [''.join(await item_details.get_details_as_text(entity.EntityDetailsType.MINI)) for item_details in items_details]
    return ', '.join(result)


def __get_training_room(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData, **kwargs) -> Optional[str]:
    required_room_level = training_info['RequiredRoomLevel']
    training_room_type = int(training_info['Rank'])
    room_name, _ = __get_room_names(training_room_type)
    if room_name:
        result = f'{room_name} lvl {required_room_level}'
    else:
        result = None
    return result





# ---------- Create entity.EntityDetails ----------

def __create_training_details_from_info(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(training_info, __properties['title'], __properties['description'], __properties['properties'], __properties['embed_settings'], trainings_data, items_data, researches_data)


def __create_training_details_list_from_infos(trainings_designs_infos: List[entity.EntityInfo], trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData) -> List[entity.EntitiesData]:
    return [__create_training_details_from_info(training_info, trainings_data, items_data, researches_data) for training_info in trainings_designs_infos]


def __create_trainings_details_collection_from_infos(trainings_designs_infos: List[entity.EntityInfo], trainings_data: entity.EntitiesData, items_data: entity.EntitiesData, researches_data: entity.EntitiesData) -> entity.EntityDetailsCollection:
    trainings_details = __create_training_details_list_from_infos(trainings_designs_infos, trainings_data, items_data, researches_data)
    result = entity.EntityDetailsCollection(trainings_details, big_set_threshold=3)
    return result





# ---------- Helper functions ----------

def __get_key_for_training_sort(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData) -> str:
    result = ''
    parent_infos = __get_parents(training_info, trainings_data)
    if parent_infos:
        for parent_info in parent_infos:
            result += parent_info[TRAINING_DESIGN_KEY_NAME].zfill(4)
    result += training_info[TRAINING_DESIGN_KEY_NAME].zfill(4)
    return result


def __get_parents(training_info: entity.EntityInfo, trainings_data: entity.EntitiesData) -> List[entity.EntityInfo]:
    parent_training_design_id = training_info['RequiredTrainingDesignId']
    if parent_training_design_id == '0':
        parent_training_design_id = None

    if parent_training_design_id is not None:
        parent_info = trainings_data[parent_training_design_id]
        result = __get_parents(parent_info, trainings_data)
        result.append(parent_info)
        return result
    else:
        return []


def __get_room_names(training_room_type: int) -> Tuple[Optional[str], Optional[str]]:
    return lookups.TRAINING_RANK_ROOM_LOOKUP.get(training_room_type, (None, None))


def __get_stat_chance(stat_name: str, training_info: entity.EntityInfo, guaranteed: bool = False) -> Optional[Tuple[str, str, str, str]]:
    if stat_name and training_info:
        chance_name = f'{stat_name}Chance'
        if chance_name in training_info.keys():
            stat_chance = int(training_info[chance_name])
            if stat_chance > 0:
                stat_emoji = lookups.STAT_EMOJI_LOOKUP[stat_name]
                stat_unit = lookups.STAT_UNITS_LOOKUP[stat_name]
                operator = '' if guaranteed else '\u2264'
                return (stat_emoji, operator, stat_chance, stat_unit)
    return None


def __get_stat_chance_as_text(stat_emoji: str, operator: str, stat_chance: str, stat_unit: str) -> str:
    return f'{stat_emoji} {operator}{stat_chance}{stat_unit}'





# ---------- Initilization ----------

trainings_designs_retriever = entity.EntityRetriever(
    TRAINING_DESIGN_BASE_PATH,
    TRAINING_DESIGN_KEY_NAME,
    TRAINING_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='TrainingDesigns',
    sorted_key_function=__get_key_for_training_sort
)

__properties: entity.EntityDetailsCreationPropertiesCollection = {
    'title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=TRAINING_DESIGN_DESCRIPTION_PROPERTY_NAME),
        property_mini=entity.NO_PROPERTY
    ),
    'description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='TrainingDescription'),
        property_short=entity.NO_PROPERTY
    ),
    'properties': entity.EntityDetailPropertyListCollection([
            entity.EntityDetailProperty('Duration', True, transform_function=__get_duration),
            entity.EntityDetailProperty('Cost', True, transform_function=__get_costs),
            entity.EntityDetailProperty('Fatigue', True, transform_function=__get_fatigue),
            entity.EntityDetailProperty('Training room', True, transform_function=__get_training_room),
            entity.EntityDetailProperty('Research required', True, transform_function=__get_required_research),
            entity.EntityDetailProperty('Consumable', True, transform_function=__get_training_item_name),
            entity.EntityDetailProperty('Stat gain chances', False, transform_function=__get_stat_chances, text_only=True),
            entity.EntityDetailProperty('Stat gain chances', False, transform_function=__get_stat_chances, embed_only=True, add_line_breaks=True)
    ],
    properties_short=[
            entity.EntityDetailProperty('Consumable', True, transform_function=__get_training_item_name, embed_only=True),
            entity.EntityDetailProperty('Stat gain chances', False, transform_function=__get_stat_chances, text_only=True),
            entity.EntityDetailProperty('Stat gain chances', False, transform_function=__get_stat_chances, embed_only=True, add_line_breaks=True)
    ],
    properties_mini=[
            entity.EntityDetailProperty('Stat gain chances', False, transform_function=__get_stat_chances, text_only=True),
            entity.EntityDetailProperty('Stat gain chances', False, transform_function=__get_stat_chances, embed_only=True, add_line_breaks=True)
    ]
    ),
    'embed_settings': {
        'thumbnail_url': entity.EntityDetailProperty('thumbnail_url', False, transform_function=__get_thumbnail_url)
    }
}