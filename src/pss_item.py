import re
from typing import Dict, List, Optional, Tuple, Union

from discord import Embed
from discord.ext.commands import Context

from . import pss_assert
from . import pss_core as core
from . import emojis
from . import pss_entity as entity
from .pss_exception import Error, NotFound, TooManyResults
from . import pss_lookups as lookups
from . import pss_sprites as sprites
from . import pss_training as training
from . import resources
from . import settings
from .typehints import EntitiesData, EntityInfo
from . import utils


# ---------- Typehint definitions -----------

IngredientsTree = Tuple[str, int, 'IngredientsTree']





# ---------- Constants ----------

ALLOWED_ITEM_NAMES: List[str]
ANY_SLOT_MARKERS = ['all', 'any']

ITEM_DESIGN_BASE_PATH: str = 'ItemService/ListItemDesigns2?languageKey=en'
ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'ItemDesignName'
ITEM_DESIGN_KEY_NAME: str = 'ItemDesignId'

NOT_ALLOWED_ITEM_NAMES: List[str] = [
    'AI',
    'MK',
    'I',
    'II',
    'III',
    'IV',
    'V',
    'VI',
]

RX_ARTIFACTS_INDICATORS: re.Pattern = re.compile(r'\(\w{1,2}\)|fragment', re.IGNORECASE)

__SLOTS_AVAILABLE: str = f'These are valid values for the _slot_ parameter: all/any (for all slots), {", ".join(lookups.EQUIPMENT_SLOTS_LOOKUP.keys())}'
__STATS_AVAILABLE: str = f'These are valid values for the _stat_ parameter: {", ".join(lookups.STAT_TYPES_LOOKUP.keys())}'





# ---------- Item info ----------

async def get_item_details_by_name(ctx: Context, item_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_data = await items_designs_retriever.get_data_dict3()
    item_infos = __get_item_infos_by_name(item_name, items_data)

    if not item_infos:
        raise NotFound(f'Could not find an item named `{item_name}`.')
    else:
        trainings_data = await training.trainings_designs_retriever.get_data_dict3()
        items_data_for_sort = {item_info.get(ITEM_DESIGN_KEY_NAME): item_info for item_info in item_infos}
        item_infos = sorted(item_infos, key=lambda item_info: (
            __get_key_for_base_items_sort(item_info, items_data_for_sort)
        ))
        items_details_collection = __create_base_details_collection_from_infos(item_infos, items_data, trainings_data)
        if items_details_collection.count > 50:
            raise TooManyResults('The search returned too many results. Please narrow down your search and try again.')

        if as_embed:
            return (await items_details_collection.get_entities_details_as_embed(ctx, custom_footer_text=resources.get_resource('PRICE_NOTE_EMBED')))
        else:
            return (await items_details_collection.get_entities_details_as_text(custom_footer_text=resources.get_resource('PRICE_NOTE')))


def __get_key_for_base_items_sort(item_info: EntityInfo, items_data: EntitiesData) -> str:
    result = item_info.get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
    item_sub_type = item_info.get('ItemSubType')
    if entity.entity_property_has_value(item_sub_type) and item_sub_type in lookups.ITEM_SUB_TYPES_TO_GET_PARENTS_FOR:
        parents = __get_parents(item_info, items_data)
        if parents:
            result = parents[0].get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
            result += ''.join([item_info.get(ITEM_DESIGN_KEY_NAME).zfill(4) for item_info in parents])
    return result





# ---------- Best info -----------

async def get_best_items(ctx: Context, slot: str, stat: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_parameter_value(slot, 'slot', allowed_values=lookups.EQUIPMENT_SLOTS_LOOKUP.keys(), allow_none_or_empty=True)
    pss_assert.valid_parameter_value(stat, 'stat', allowed_values=lookups.STAT_TYPES_LOOKUP.keys())

    items_details = await items_designs_retriever.get_data_dict3()
    error = __get_best_items_error(slot, stat)
    if error:
        raise Error(error)

    any_slot = not slot or slot in ANY_SLOT_MARKERS
    slot_filter = __get_slot_filter(slot, any_slot)
    stat_filter = __get_stat_filter(stat)
    best_items = __get_best_items_designs(slot_filter, stat_filter, items_details)

    if not best_items:
        if not any_slot:
            slot = f' for slot `{slot}`'
        raise NotFound(f'Could not find an item{slot} providing bonus `{stat_filter.lower()}`.')
    else:
        groups = await __get_collection_groups(best_items, stat_filter, as_embed)

        result = []
        if as_embed:
            for title, best_items_collection in groups.items():
                footer = __get_footer_text_for_group(title, as_embed)
                embeds = await best_items_collection.get_entities_details_as_embed(ctx, custom_title=title, custom_footer_text=footer)
                result.extend(embeds)
            return result
        else:
            module_title = None
            for title, best_items_collection in groups.items():
                if 'module' in title.lower():
                    module_title = title
                texts = await best_items_collection.get_entities_details_as_text(custom_title=title)
                result.extend(texts)
                result.append(utils.discord.ZERO_WIDTH_SPACE)
            footer = __get_footer_text_for_group(module_title, as_embed)
            result.append(footer)
            return result


def __get_best_items_designs(slot_filter: List[str], stat_filter: str, items_data: EntitiesData) -> Dict[str, List[entity.EntityDetails]]:
    filters = {
        'ItemType': 'Equipment',
        'ItemSubType': slot_filter,
        'EnhancementType': stat_filter
    }
    result = {}

    filtered_data = core.filter_entities_data(items_data, filters, ignore_case=True)

    if filtered_data:
        items_infos = sorted(filtered_data.values(), key=__get_key_for_best_items_sort)
        # Filter out destroyed modules
        items_infos = __filter_destroyed_modules_from_item_infos(items_infos)
        items_details = [__create_best_item_details_from_info(item_info, items_data) for item_info in items_infos]
        result = entity.group_entities_details(items_details, 'ItemSubType')
    return result


def __get_best_items_error(slot: str, stat: str) -> Optional[str]:
    if not stat:
        return f'You must specify a stat! {__STATS_AVAILABLE}'
    if slot:
        slot = slot.lower()
        if slot not in lookups.EQUIPMENT_SLOTS_LOOKUP.keys() and slot not in resources.get_resource('ANY_SLOT_NAMES'):
            return f'The specified equipment slot is not valid! {__SLOTS_AVAILABLE}'
    if stat.lower() not in lookups.STAT_TYPES_LOOKUP.keys():
        return f'The specified stat is not valid! {__STATS_AVAILABLE}'

    return None


def __get_best_items_title(stat: str, slot: str, is_equipment_slot: bool, use_markdown: bool = True) -> str:
    bold_marker = '**' if use_markdown else ''
    slot_text = ' slot' if is_equipment_slot else 's'
    return f'Best {bold_marker}{stat}{bold_marker} bonus for {bold_marker}{slot}{bold_marker}{slot_text}'


async def __get_collection_groups(best_items: Dict[str, List[entity.EntityDetails]], stat: str, as_embed: bool) -> Dict[str, entity.EntityDetailsCollection]:
    result = {}
    group_names_sorted = sorted(best_items.keys(), key=lambda x: lookups.EQUIPMENT_SLOTS_ORDER_LOOKUP.index(x))

    for group_name in group_names_sorted:
        group = best_items[group_name]
        title = __get_best_items_title(stat, *__get_pretty_slot(group_name), use_markdown=(not as_embed))

        items_details_collection = __create_best_item_details_collection_from_details(group)
        result[title] = items_details_collection
    return result


def __get_footer_text_for_group(group_title: str, as_embed: bool) -> str:
    result = []
    if group_title and 'module' in group_title.lower():
        if as_embed:
            result.append(resources.get_resource('HERO_MODULE_NOTE_EMBED'))
        else:
            result.append(resources.get_resource('HERO_MODULE_NOTE'))
    if as_embed:
        result.append(resources.get_resource('PRICE_NOTE_EMBED'))
    else:
        result.append(resources.get_resource('PRICE_NOTE'))
    return '\n'.join(result)


def __get_key_for_best_items_sort(item_info: EntityInfo) -> str:
    if item_info.get('EnhancementValue') and item_info.get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME):
        slot = item_info['ItemSubType']
        rarity_num = lookups.RARITY_ORDER_LOOKUP[item_info['Rarity']]
        enhancement_value = int((1000.0 - float(item_info['EnhancementValue'])) * 10)
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
        result = f'{enhancement_value}{slot}{rarity_num}{item_name}'
        return result


def __get_pretty_slot(slot: str) -> Tuple[str, bool]:
    """
    Returns: (slot name, is equipment)
    """
    if 'Equipment' in slot:
        return slot.replace('Equipment', ''), True
    else:
        return slot, False





# ---------- Price info ----------

async def get_item_price(ctx: Context, item_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_data = await items_designs_retriever.get_data_dict3()
    item_infos = __get_item_infos_by_name(item_name, items_data)

    if not item_infos:
        raise NotFound(f'Could not find an item named `{item_name}`.')
    else:
        get_best_match = utils.is_str_in_list(item_name, ALLOWED_ITEM_NAMES, case_sensitive=False) and len(item_name) < settings.MIN_ENTITY_NAME_LENGTH - 1
        if get_best_match:
            item_infos = [item_infos[0]]

        item_infos = entity.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])
        items_details_collection = __create_price_details_collection_from_infos(item_infos, items_data)

        if as_embed:
            custom_footer = '\n'.join([resources.get_resource('MARKET_FAIR_PRICE_NOTE_EMBED'), resources.get_resource('PRICE_NOTE_EMBED')])
            return (await items_details_collection.get_entities_details_as_embed(ctx, custom_footer_text=custom_footer))
        else:
            custom_footer = '\n'.join([resources.get_resource('MARKET_FAIR_PRICE_NOTE'), resources.get_resource('PRICE_NOTE')])
            return (await items_details_collection.get_entities_details_as_text())





# ---------- Ingredients info ----------

async def get_ingredients_for_item(ctx: Context, item_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_data = await items_designs_retriever.get_data_dict3()
    item_infos = __get_item_infos_by_name(item_name, items_data, return_best_match=True)

    if not item_infos:
        raise NotFound(f'Could not find an item named `{item_name}`.')
    else:
        ingredients_details_collection = __create_ingredients_details_collection_from_infos([item_infos[0]], items_data)
        if as_embed:
            return (await ingredients_details_collection.get_entities_details_as_embed(ctx, custom_footer_text=resources.get_resource('PRICE_NOTE_EMBED')))
        else:
            return (await ingredients_details_collection.get_entities_details_as_text(custom_footer_text=resources.get_resource('PRICE_NOTE')))


def __flatten_ingredients_tree(ingredients_tree: IngredientsTree) -> List[Dict[str, int]]:
    """Returns a list of dicts"""
    ingredients = {}
    ingredients_without_subs = []
    sub_ingredients = []

    for item_id, item_amount, item_ingredients in ingredients_tree:
        if item_id in ingredients.keys():
            ingredients[item_id] += item_amount
        else:
            ingredients[item_id] = item_amount

        if item_ingredients:
            sub_ingredients.extend(item_ingredients)
        else:
            ingredients_without_subs.append((item_id, item_amount, item_ingredients))

    result = [ingredients]

    if len(ingredients_without_subs) != len(ingredients_tree):
        sub_ingredients.extend(ingredients_without_subs)
        flattened_subs = __flatten_ingredients_tree(sub_ingredients)
        result.extend(flattened_subs)

    return result


def __parse_ingredients_tree(ingredients_str: str, items_data: EntitiesData, include_partial_artifacts: bool, parent_amount: int = 1) -> List[IngredientsTree]:
    """returns a tree structure: [(item_id, item_amount, item_ingredients[])]"""
    if not ingredients_str:
        return []

    # Ingredients format is: [<id>x<amount>][|<id>x<amount>]*
    ingredients_dict = get_ingredients_dict(ingredients_str)
    result = []

    for item_id, item_amount in ingredients_dict.items():
        item_info = items_data[item_id]
        item_name = item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME].lower()
        item_amount = int(item_amount)
        # Filter out void particles and fragments
        if include_partial_artifacts or ('void particle' not in item_name and ' fragment' not in item_name):
            combined_amount = item_amount * parent_amount
            item_ingredients = __parse_ingredients_tree(item_info['Ingredients'], items_data, include_partial_artifacts, combined_amount)
            result.append((item_id, combined_amount, item_ingredients))

    return result





# ---------- Upgrade info ----------

async def get_item_upgrades_from_name(ctx: Context, item_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(item_name, allowed_values=ALLOWED_ITEM_NAMES)

    items_data = await items_designs_retriever.get_data_dict3()
    items_ids = __get_item_design_ids_from_name(item_name, items_data)
    items_infos = __filter_destroyed_modules_from_item_infos([items_data[item_id] for item_id in items_ids])

    if not items_ids or not items_infos:
        raise NotFound(f'Could not find an item named `{item_name}` that can be upgraded.')
    else:
        upgrades_infos = []
        found_upgrades_for_data = {}
        no_upgrades_for_data = {}
        for item_id in items_ids:
            upgrades_for = __get_upgrades_for(item_id, items_data)
            upgrades_infos.extend(upgrades_for)
            if all(upgrades_for):
                found_upgrades_for_data[item_id] = items_data[item_id]
            else:
                no_upgrades_for_data[item_id] = items_data[item_id]


        if all(item_info is None for item_info in upgrades_infos):
            item_names = '\n'.join(sorted(f'{emojis.small_orange_diamond}{item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]}' for item_info in items_infos))
            raise Error(f'Found the following items that can\'t be upgraded:\n{item_names}')

        # Remove double entries
        upgrades_infos = list(dict([(item_info[ITEM_DESIGN_KEY_NAME], item_info) for item_info in upgrades_infos if item_info is not None]).values())
        upgrades_infos = entity.sort_entities_by(upgrades_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])
        upgrades_infos_count = len(upgrades_infos)
        upgrade_details_collection = __create_upgrade_details_collection_from_infos(upgrades_infos, items_data, found_upgrades_for_data, no_upgrades_for_data, len(upgrades_infos))

        if as_embed:
            custom_title = f'Found {upgrades_infos_count} crafting recipes requiring {item_name}'
            return (await upgrade_details_collection.get_entities_details_as_embed(ctx, custom_title=custom_title))
        else:
            custom_title = f'Found {upgrades_infos_count} crafting recipes requiring **{item_name}**:'
            return (await upgrade_details_collection.get_entities_details_as_text(custom_title=custom_title, big_set_details_type=entity.EntityDetailsType.LONG))


def __get_footer_upgrades(items_data: EntitiesData) -> str:
    items_names = utils.format.get_and_list(sorted(item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME] for item_info in items_data.values()))
    result = f'Also found the following items that can\'t be upgraded: {items_names}'
    return result


def __get_title_upgrades(upgrades_infos_count: int, items_data: EntitiesData) -> str:
    items_names_list = utils.format.get_or_list(sorted(item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME] for item_info in items_data.values()))
    result = f'{upgrades_infos_count} crafting recipes requiring: {items_names_list}'
    return result


def __get_upgrades_for(item_id: str, items_data: EntitiesData) -> List[Optional[EntityInfo]]:
    # iterate through item_design_data and return every item_design containing the item id in question in property 'Ingredients'
    result = []
    for item_info in items_data.values():
        ingredient_item_ids = list(get_ingredients_dict(item_info['Ingredients']).keys())
        if item_id in ingredient_item_ids:
            result.append(item_info)
    if not result:
        result = [None]
    return result





# ---------- Transformation functions ----------

def __get_all_ingredients(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    include_partial_artifacts = get_include_partial_artifacts(item_info)
    ingredients_tree = __parse_ingredients_tree(item_info['Ingredients'], items_data, include_partial_artifacts)
    ingredients_dicts = __flatten_ingredients_tree(ingredients_tree)
    ingredients_dicts = [d for d in ingredients_dicts if d]
    lines = []
    if ingredients_dicts:
        for ingredients_dict in ingredients_dicts:
            current_level_lines = []
            current_level_costs = 0
            for ingredient_item_id, ingredient_amount in ingredients_dict.items():
                ingredient_item_info = items_data[ingredient_item_id]
                ingredient_name = ingredient_item_info[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
                ingredient_price = int(ingredient_item_info['MarketPrice'])
                price_sum = ingredient_price * ingredient_amount
                current_level_costs += price_sum
                current_level_lines.append(f'> {ingredient_amount} x {ingredient_name} ({ingredient_price} bux ea): {price_sum} bux')
            lines.extend(current_level_lines)
            lines.append(f'Crafting costs: {current_level_costs} bux')
            lines.append(utils.discord.ZERO_WIDTH_SPACE)
        if lines:
            lines = lines[:-1]
    else:
        lines.append('This item can\'t be crafted')
    return '\n'.join(lines)


def __get_can_sell(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    flags = int(item_info['Flags'])
    if flags & 1 == 0:
        result = resources.get_resource('CANNOT_BE_SOLD')
    else:
        result = None
    return result


def __get_enhancement_value(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    enhancement_value = float(item_info['EnhancementValue'])
    result = f'{enhancement_value:.1f}'
    return result


async def __get_image_url(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    logo_sprite_id = item_info.get('LogoSpriteId')
    image_sprite_id = item_info.get('ImageSpriteId')
    if entity.entity_property_has_value(logo_sprite_id) and logo_sprite_id != image_sprite_id:
        return await sprites.get_download_sprite_link(logo_sprite_id)
    else:
        return None


def __get_ingredients(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    ingredients = get_ingredients_dict(item_info.get('Ingredients'))
    result = []
    for item_id, amount in ingredients.items():
        item_name = items_data[item_id].get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
        result.append(f'> {item_name} x{amount}')
    if result:
        return '\n'.join(result)
    else:
        return None


def __get_item_bonus_type_and_value(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    use_emojis = kwargs.get('use_emojis', False)
    enhancements = get_all_enhancements(item_info)
    result = ', '.join(f'{__get_pretty_enhancement(*enhancement, use_emojis=use_emojis)}' for enhancement in enhancements)
    if result and item_info['ItemType'] == 'Equipment' and 'Equipment' in item_info['ItemSubType'] and lookups.RARITY_ORDER_LOOKUP[item_info['Rarity']] <= 30:
        result += ' (+ ??)'
    return result or None


def __get_item_price(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    flags = int(item_info['Flags'])
    if flags & 1 == 0:
        result = resources.get_resource('CANNOT_BE_SOLD')
    else:
        fair_price = item_info['FairPrice']
        market_price = item_info['MarketPrice']
        result = f'{market_price} ({fair_price})'
    return result


def __get_item_slot(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    result = None
    use_emojis = kwargs.get('use_emojis')
    item_type = item_info['ItemType']
    item_sub_type = item_info['ItemSubType']
    if item_type == 'Equipment' and 'Equipment' in item_sub_type:
        if use_emojis:
            result = lookups.EQUIPMENT_SLOTS_EMOJI_LOOKUP.get(item_sub_type)
        else:
            result = item_sub_type.replace('Equipment', '')
    return result


def __get_pretty_market_price(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    flags = int(item_info['Flags'])
    if flags & 1 == 0:
        result = resources.get_resource('CANNOT_BE_SOLD')
    else:
        market_price = item_info['MarketPrice']
        result = f'{market_price} bux'
    return result


def __get_price(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    flags = int(item_info['Flags'])
    if flags & 1 == 0:
        result = None
    else:
        price = kwargs.get('entity_property')
        result = f'{price} bux'
    return result


def __get_rarity_emoji(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    result = lookups.RARITY_INDICTAOR_EMOJIS_LOOKUP.get(item_info['Rarity'])
    return result


def __get_requirements(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    requirement_string = entity.get_property_from_entity_info(item_info, 'RequirementString')
    result = None
    if requirement_string:
        results = []
        requirements = utils.parse.requirement_string(requirement_string)
        for entity_type, _, entity_amount, entity_amount_modifier in requirements:
            details = None
            if entity_type == 'shiplevel':
                resource_key = f'AMOUNTMODIFIER{entity_amount_modifier}'
                details = f'Ship level {entity_amount}{resources.get_resource(resource_key)}'

            if details:
                results.append(details)
        result = utils.format.get_and_list(results, emphasis='**') or None
    return result


def __get_title_ingredients(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    value = kwargs.get('entity_property')
    if value:
        result = f'Ingredients for: {value}'
    else:
        result = None
    return result


async def __get_training_mini_details(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData, **kwargs) -> Optional[str]:
    for_embed = kwargs.get('for_embed', False)
    training_design_id = item_info.get(training.TRAINING_DESIGN_KEY_NAME)
    if entity.entity_property_has_value(training_design_id):
        training_design_details: entity.EntityDetails = await training.get_training_details_from_id(training_design_id, trainings_data, items_data)
        result = await training_design_details.get_details_as_text(entity.EntityDetailsType.MINI, for_embed=for_embed)
        return ''.join(result)
    else:
        return None


def get_type(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData = None, **kwargs) -> Optional[str]:
    item_sub_type = item_info.get('ItemSubType')
    if entity.entity_property_has_value(item_sub_type) and 'Equipment' not in item_sub_type:
        result = item_sub_type.replace('Equipment', '')
        result = lookups.ITEM_SUB_TYPES_LOOKUP.get(result, result)
    else:
        item_type = item_info.get('ItemType')
        if entity.entity_property_has_value(item_type):
            result = item_type
        else:
            result = None
    return result





# ---------- Helper functions ----------

def filter_items_details_for_equipment(items_details: List[entity.EntityDetails]) -> List[entity.EntityDetails]:
    result = [item_details for item_details in items_details if __get_item_slot(item_details.entity_info, None, None) is not None]
    if result:
        stat = items_details[0].entity_info.get('EnhancementType')
        slot = __get_item_slot(items_details[0].entity_info, None, None)
        if all(item_details.entity_info.get('EnhancementType') == stat and __get_item_slot(item_details.entity_info, None, None) == slot for item_details in items_details):
            return [items_details[0]]
    return result


def fix_slot_and_stat(slot: str, stat: str) -> Tuple[str, str]:
    if not slot and not stat:
        pass
    elif slot and not stat:
        stat = slot.lower()
        slot = None
    if not slot and stat:
        pass
    else:
        slot = slot.lower()
        stat = stat.lower()
        temp_stat = f'{slot} {stat}'.strip()
        if temp_stat in lookups.STAT_TYPES_LOOKUP:
            slot = None
            stat = temp_stat
        else:
            if slot in lookups.STAT_TYPES_LOOKUP and stat in lookups.EQUIPMENT_SLOTS_LOOKUP:
                slot, stat = (stat, slot)
            elif ' ' in stat:
                split_stat = stat.split(' ')
                temp_slot = f'{slot} {split_stat[0]}'
                temp_stat = ' '.join(split_stat[1:])
                if temp_slot in lookups.STAT_TYPES_LOOKUP and temp_stat in lookups.EQUIPMENT_SLOTS_LOOKUP:
                    slot, stat = temp_stat, temp_slot
    return slot, stat


async def get_image_url(item_info: EntityInfo) -> Optional[str]:
    logo_sprite_id = item_info.get('LogoSpriteId')
    image_sprite_id = item_info.get('ImageSpriteId')
    if entity.entity_property_has_value(logo_sprite_id) and logo_sprite_id != image_sprite_id:
        return await sprites.get_download_sprite_link(logo_sprite_id)
    elif entity.entity_property_has_value(image_sprite_id):
        return await sprites.get_download_sprite_link(image_sprite_id)
    else:
        return None


def get_include_partial_artifacts(item_info: EntityInfo) -> bool:
    item_name = item_info.get(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
    result = RX_ARTIFACTS_INDICATORS.search(item_name) is not None
    return result


def get_item_details_by_id(item_design_id: str, items_data: EntitiesData, trainings_data: EntitiesData) -> entity.EntityDetails:
    if item_design_id and item_design_id in items_data.keys():
        return __create_base_details_from_info(items_data[item_design_id], items_data, trainings_data)
    else:
        return None


def get_item_details_by_training_id(training_id: str, items_data: EntitiesData, trainings_data: EntitiesData) -> List[entity.EntityDetails]:
    items_designs_ids = core.get_ids_from_property_value(items_data, training.TRAINING_DESIGN_KEY_NAME, training_id, fix_data_delegate=__fix_item_name, match_exact=True)
    result = [get_item_details_by_id(item_design_id, items_data, trainings_data) for item_design_id in items_designs_ids]
    return result


async def get_item_search_details(item_details: entity.EntityDetails) -> List[str]:
    result = await item_details.get_details_as_text(entity.EntityDetailsType.MINI)
    return ''.join(result)


async def get_items_details_by_name(item_name: str, sorted: bool = True) -> List[entity.EntityDetails]:
    items_data = await items_designs_retriever.get_data_dict3()
    trainings_data = await training.trainings_designs_retriever.get_data_dict3()
    item_infos = __get_item_infos_by_name(item_name, items_data)
    if sorted:
        item_infos = entity.sort_entities_by(item_infos, [(ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, None, False)])
    result = __create_base_details_list_from_infos(item_infos, items_data, trainings_data)
    return result


def get_slot_and_stat_type(item_details: entity.EntityDetails) -> Tuple[str, str]:
    slot = __get_item_slot(item_details.entity_info, None, None)
    stat = item_details.entity_info['EnhancementType']
    return slot, stat


def __filter_destroyed_modules_from_item_infos(items_infos: List[EntityInfo]) -> List[EntityInfo]:
    result = [item_info for item_info in items_infos if item_info.get('ItemSubType') != 'Module' or entity.entity_property_has_value(item_info.get('ModuleArgument'))]
    return result


def __fix_item_name(item_name: str) -> str:
    result = item_name.lower()
    result = re.sub('[^a-z0-9]', '', result)
    result = re.sub("(darkmatterrifle|dmr)(mark|mk)?(ii|2)", "dmrmarkii", result)
    result = result.replace('anonmask', 'anonymousmask')
    result = result.replace('armour', 'armor')
    result = result.replace('bunny', 'rabbit')
    result = result.replace('golden', 'gold')
    return result


def get_all_enhancements(item_info: EntityInfo) -> List[Tuple[str, float]]:
    result = []
    bonus_type = entity.get_property_from_entity_info(item_info, 'EnhancementType')
    if bonus_type:
        bonus_value = entity.get_property_from_entity_info(item_info, 'EnhancementValue')
        if bonus_value:
            result.append((str(bonus_type), float(bonus_value)))

    module_type = entity.get_property_from_entity_info(item_info, 'ModuleType')
    if module_type and module_type in lookups.MODULE_TYPE_TO_STAT_LOOKUP:
        module_stat = lookups.MODULE_TYPE_TO_STAT_LOOKUP.get(module_type)
        module_argument = entity.get_property_from_entity_info(item_info, 'ModuleArgument')
        if module_argument:
            result.append((module_stat, float(module_argument) / 100))
    return result


def __get_allowed_item_names(items_data: EntitiesData, not_allowed_item_names: List[str]) -> List[str]:
    result = []
    for item_design_data in items_data.values():
        if ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME in item_design_data.keys():
            item_name = item_design_data[ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME]
            if item_name:
                item_name = core.fix_allowed_value_candidate(item_name)
                if len(item_name) < settings.MIN_ENTITY_NAME_LENGTH:
                    result.append(item_name)
                else:
                    item_name_parts = item_name.split(' ')
                    for item_name_part in item_name_parts:
                        part_length = len(item_name_part)
                        length_matches = part_length > 1 and part_length < settings.MIN_ENTITY_NAME_LENGTH
                        is_proper_name = item_name_part == item_name_part.upper()
                        if length_matches and is_proper_name:
                            try:
                                int(item_name_part)
                                continue
                            except:
                                if item_name_part not in not_allowed_item_names:
                                    result.append(item_name_part)
    if result:
        result = list(set(result))
    return result


def get_ingredients_dict(ingredients: str) -> Dict[str, str]:
    result = {}
    if entity.entity_property_has_value(ingredients):
        result = dict([ingredient.split('x') for ingredient in ingredients.split('|')])
    return result


def __get_parents(item_info: EntityInfo, items_data: EntitiesData) -> List[EntityInfo]:
    item_design_id = item_info.get(ITEM_DESIGN_KEY_NAME)
    root_item_design_id = item_info.get('RootItemDesignId')
    result = []
    if entity.entity_property_has_value(root_item_design_id) and item_design_id != root_item_design_id:
        parent_info = items_data.get(root_item_design_id)
        if parent_info:
            result = __get_parents(parent_info, items_data)
            result.append(parent_info)
    return result


def __get_item_design_ids_from_name(item_name: str, items_data: EntitiesData) -> List[str]:
    results = core.get_ids_from_property_value(items_data, ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, item_name, fix_data_delegate=__fix_item_name)
    return results


def __get_item_infos_by_name(item_name: str, items_data: EntitiesData, return_best_match: bool = False) -> List[EntityInfo]:
    item_design_ids = __get_item_design_ids_from_name(item_name, items_data)
    result = [items_data[item_design_id] for item_design_id in item_design_ids if item_design_id in items_data.keys()]

    if result:
        get_best_match = return_best_match or utils.is_str_in_list(item_name, ALLOWED_ITEM_NAMES, case_sensitive=False) and len(item_name) < settings.MIN_ENTITY_NAME_LENGTH - 1
        if get_best_match:
            result = [result[0]]

    return result


def __get_pretty_enhancement(enhancement_type: str, enhancement_value: float, use_emojis: bool = False) -> str:
    modifier = lookups.STAT_UNITS_ENHANCEMENT_MODIFIER_LOOKUP.get(enhancement_type) or ''
    if use_emojis:
        enhancement_type = lookups.STAT_EMOJI_LOOKUP.get(enhancement_type)
    result = f'{enhancement_type} +{enhancement_value}{modifier}'
    return result


def __get_slot_filter(slot: str, any_slot: bool) -> List[str]:
    if any_slot:
        result = list(lookups.EQUIPMENT_SLOTS_LOOKUP.values())
    else:
        slot = slot.lower()
        result = [lookups.EQUIPMENT_SLOTS_LOOKUP[slot]]
    return result


def __get_stat_filter(stat: str) -> str:
    stat = stat.lower()
    return lookups.STAT_TYPES_LOOKUP[stat]





# ---------- Create entity.EntityDetails ----------

def __create_base_details_from_info(item_info: EntityInfo, items_data: EntitiesData, trainings_data: EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(item_info, __properties['title'], __properties['description'], __properties['base'], __properties['embed_settings'], items_data, trainings_data)


def __create_base_details_collection_from_infos(items_infos: List[EntityInfo], items_data: EntitiesData, trainings_data: EntitiesData) -> entity.EntityDetailsCollection:
    base_details = __create_base_details_list_from_infos(items_infos, items_data, trainings_data)
    result = entity.EntityDetailsCollection(base_details, big_set_threshold=3)
    return result


def __create_base_details_list_from_infos(items_infos: List[EntityInfo], items_data: EntitiesData, trainings_data: EntitiesData) -> entity.EntityDetails:
    result = [__create_base_details_from_info(item_info, items_data, trainings_data) for item_info in items_infos]
    return result



def __create_best_item_details_from_info(item_info: EntityInfo, items_data: EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(item_info, __properties['title'], __properties['description'], __properties['best'], __properties['embed_settings'], items_data, prefix='> ')


def __create_best_item_details_collection_from_details(best_details: List[entity.EntityDetails]) -> entity.EntityDetailsCollection:
    result = entity.EntityDetailsCollection(best_details, big_set_threshold=1)
    return result



def __create_ingredients_design_data_from_info(item_info: EntityInfo, items_data: EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(item_info, __properties['title_ingredients'], __properties['description_ingredients'], None, __properties['embed_settings'], items_data)


def __create_ingredients_details_collection_from_infos(items_designs_infos: List[EntityInfo], items_data: EntitiesData) -> entity.EntityDetailsCollection:
    price_details = [__create_ingredients_design_data_from_info(item_info, items_data) for item_info in items_designs_infos]
    result = entity.EntityDetailsCollection(price_details, big_set_threshold=0)
    return result



def __create_price_design_data_from_info(item_info: EntityInfo, items_data: EntitiesData) -> entity.EntityDetails:
    return entity.EntityDetails(item_info, __properties['title'], __properties['description'], __properties['price'], __properties['embed_settings'], items_data)


def __create_price_details_collection_from_infos(items_designs_infos: List[EntityInfo], items_data: EntitiesData) -> entity.EntityDetailsCollection:
    price_details = [__create_price_design_data_from_info(item_info, items_data) for item_info in items_designs_infos]
    result = entity.EntityDetailsCollection(price_details, big_set_threshold=1)
    return result



def __create_upgrade_design_data_from_info(item_info: EntityInfo, items_data: EntitiesData, found_upgrades_for_data: EntitiesData, no_upgrades_for_data: EntitiesData, upgrades_infos_count: int) -> entity.EntityDetails:
    return entity.EntityDetails(item_info, __properties['title'], entity.NO_PROPERTY, __properties['upgrade'], __properties['embed_settings'], items_data, found_upgrades_for_data=found_upgrades_for_data, no_upgrades_for_data=no_upgrades_for_data, upgrades_infos_count=upgrades_infos_count)


def __create_upgrade_details_collection_from_infos(items_designs_infos: List[EntityInfo], items_data: EntitiesData, found_upgrades_for_data: EntitiesData, no_upgrades_for_data: EntitiesData, upgrades_infos_count: int) -> entity.EntityDetailsCollection:
    price_details = [__create_upgrade_design_data_from_info(item_info, items_data, found_upgrades_for_data=found_upgrades_for_data, no_upgrades_for_data=no_upgrades_for_data, upgrades_infos_count=upgrades_infos_count) for item_info in items_designs_infos]
    result = entity.EntityDetailsCollection(price_details, big_set_threshold=1)
    return result





# ---------- Initilization ----------

items_designs_retriever: entity.EntityRetriever = entity.EntityRetriever(
    ITEM_DESIGN_BASE_PATH,
    ITEM_DESIGN_KEY_NAME,
    ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME,
    'ItemsDesigns',
    fix_data_delegate=__fix_item_name
)

__properties: entity.EntityDetailsCreationPropertiesCollection = {
    'title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME)
    ),
    'title_ingredients': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, entity_property_name=ITEM_DESIGN_DESCRIPTION_PROPERTY_NAME, transform_function=__get_title_ingredients),
    ),
    'description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, entity_property_name='ItemDesignDescription'),
        property_medium=entity.NO_PROPERTY
    ),
    'base': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Rarity', True, entity_property_name='Rarity'),
            entity.EntityDetailProperty('Type', True, transform_function=get_type),
            entity.EntityDetailProperty('Bonus', True, transform_function=__get_item_bonus_type_and_value),
            entity.EntityDetailProperty('Slot', True, transform_function=__get_item_slot),
            entity.EntityDetailProperty('Stat gain chances', True, transform_function=__get_training_mini_details, embed_only=True, for_embed=True),
            entity.EntityDetailProperty('Stat gain chances', True, transform_function=__get_training_mini_details, text_only=True),
            entity.EntityDetailProperty('Market price', True, transform_function=__get_pretty_market_price),
            entity.EntityDetailProperty('Savy\'s Fair price', True, entity_property_name='FairPrice', transform_function=__get_price),
            entity.EntityDetailProperty('Requirements', True, entity_property_name='RequirementString', transform_function=__get_requirements),
        ],
        properties_medium=[
            entity.EntityDetailProperty('Rarity', False, entity_property_name='Rarity'),
            entity.EntityDetailProperty('Bonus', False, transform_function=__get_item_bonus_type_and_value),
            entity.EntityDetailProperty('Slot', False, transform_function=__get_item_slot),
            entity.EntityDetailProperty('Can sell', False, transform_function=__get_can_sell, text_only=True),
            entity.EntityDetailProperty('Market price', False, transform_function=__get_pretty_market_price, embed_only=True),
            entity.EntityDetailProperty('Savy\'s Fair price', True, entity_property_name='FairPrice', transform_function=__get_price),
        ],
        properties_short=[
            entity.EntityDetailProperty('Rarity', False, transform_function=__get_rarity_emoji),
            entity.EntityDetailProperty('Bonus', False, transform_function=__get_item_bonus_type_and_value, use_emojis=True),
            entity.EntityDetailProperty('Slot', False, transform_function=__get_item_slot, use_emojis=True),
        ],
        properties_mini=[]
    ),
    'best': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Rarity', False, entity_property_name='Rarity'),
            entity.EntityDetailProperty('Enhancement value', False, transform_function=__get_enhancement_value),
            entity.EntityDetailProperty('Market price', False, transform_function=__get_pretty_market_price)
        ]
    ),
    'description_ingredients': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Ingredients', False, transform_function=__get_all_ingredients)
    ),
    'price': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Rarity', False, entity_property_name='Rarity', embed_only=True),
            entity.EntityDetailProperty('Market price', True, entity_property_name='MarketPrice', transform_function=__get_price),
            entity.EntityDetailProperty('Savy\'s Fair price', True, entity_property_name='FairPrice', transform_function=__get_price),
            entity.EntityDetailProperty('Can sell', False, transform_function=__get_can_sell)
        ],
        properties_medium=[
            entity.EntityDetailProperty('Rarity', False, entity_property_name='Rarity', embed_only=True),
            entity.EntityDetailProperty('Market price (Fair price)', False, transform_function=__get_item_price)
        ]
    ),
    'upgrade': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Ingredients', False, transform_function=__get_ingredients)
        ]
    ),
    'embed_settings': {
        'image_url': entity.EntityDetailProperty('image_url', False, transform_function=__get_image_url),
        'thumbnail_url': entity.EntityDetailProperty('thumbnail_url', False, entity_property_name='ImageSpriteId', transform_function=sprites.get_download_sprite_link_by_property)
    }
}





async def init() -> None:
    global ALLOWED_ITEM_NAMES
    items_data = await items_designs_retriever.get_data_dict3()
    ALLOWED_ITEM_NAMES = sorted(__get_allowed_item_names(items_data, NOT_ALLOWED_ITEM_NAMES))