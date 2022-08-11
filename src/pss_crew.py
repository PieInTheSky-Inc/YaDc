from collections import Counter
from typing import Dict, List, Optional, Tuple, Union

from discord import Colour, Embed
from discord.ext.commands import Context

from . import pss_assert
from .cache import PssCache
from . import emojis
from . import pss_entity as entity
from .pss_exception import Error, NotFound
from . import pss_lookups as lookups
from . import pss_sprites as sprites
from . import settings
from .typehints import EntitiesData, EntityInfo
from . import utils


# ---------- Constants ----------

CHARACTER_DESIGN_BASE_PATH: str = 'CharacterService/ListAllCharacterDesigns2?languageKey=en'
CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'CharacterDesignName'
CHARACTER_DESIGN_KEY_NAME: str = 'CharacterDesignId'

COLLECTION_DESIGN_BASE_PATH: str = 'CollectionService/ListAllCollectionDesigns?languageKey=en'
COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME: str = 'CollectionName'
COLLECTION_DESIGN_KEY_NAME: str = 'CollectionDesignId'

__PRESTIGE_FROM_BASE_PATH: str = 'CharacterService/PrestigeCharacterFrom?languagekey=en&characterDesignId='
__PRESTIGE_TO_BASE_PATH: str = 'CharacterService/PrestigeCharacterTo?languagekey=en&characterDesignId='





# ---------- Classes ----------

class PrestigeError(Error):
    pass


class PrestigeNoResultsError(PrestigeError):
    pass





# ---------- Crew info ----------

def get_char_details_by_id(char_design_id: str, chars_data: EntitiesData, collections_data: EntitiesData, level: int = None) -> entity.entity.EntityDetails:
    if char_design_id:
        if char_design_id and char_design_id in chars_data.keys():
            return __create_character_details_from_info(chars_data[char_design_id], chars_data, collections_data, level)
    return None


async def get_char_details_by_name(ctx: Context, char_name: str, level: int, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(char_name, 'char_name', min_length=2)
    pss_assert.parameter_is_valid_integer(level, 'level', min_value=1, max_value=40, allow_none=True)

    chars_data = await characters_designs_retriever.get_data_dict3()
    char_info = await characters_designs_retriever.get_entity_info_by_name(char_name, chars_data)

    if char_info is None:
        raise NotFound(f'Could not find a crew named `{char_name}`.')
    else:
        collections_data = await collections_designs_retriever.get_data_dict3()
        characters_details_collection = __create_characters_details_collection_from_infos([char_info], chars_data, collections_data, level)
        if as_embed:
            return (await characters_details_collection.get_entities_details_as_embed(ctx))
        else:
            return (await characters_details_collection.get_entities_details_as_text())





# ---------- Collection Info ----------

async def get_collection_details_by_name(ctx: Context, collection_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(collection_name, parameter_name='collection_name', allow_none_or_empty=True)

    print_all = not collection_name
    collections_data = await collections_designs_retriever.get_data_dict3()
    characters_data = await characters_designs_retriever.get_data_dict3()
    collections_designs_infos = []
    if print_all:
        collections_designs_infos = collections_data.values()
    else:
        collection_info = await collections_designs_retriever.get_entity_info_by_name(collection_name, collections_data)
        if collection_info:
            collections_designs_infos.append(collection_info)

    if not collections_designs_infos:
        if print_all:
            raise Error(f'An error occured upon retrieving collection info. Please try again later.')
        else:
            raise NotFound(f'Could not find a collection named `{collection_name}`.')
    else:
        collections_designs_infos = sorted(collections_designs_infos, key=lambda x: x[COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME])
        collections_designs_infos = collections_designs_infos if print_all else [collections_designs_infos[0]]
        collections_details_collection = __create_collections_details_collection_from_infos(collections_designs_infos, collections_data, characters_data)

        if as_embed:
            return (await collections_details_collection.get_entities_details_as_embed(ctx))
        else:
            return (await collections_details_collection.get_entities_details_as_text())





# ---------- Prestige from Info ----------

async def get_prestige_from_info(ctx: Context, char_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(char_name, 'char_name', min_length=2)

    chars_data = await characters_designs_retriever.get_data_dict3()
    char_from_info = await characters_designs_retriever.get_entity_info_by_name(char_name, chars_data)

    if not char_from_info:
        raise NotFound(f'Could not find a crew named `{char_name}`.')
    else:
        rarity = char_from_info.get('Rarity')
        if rarity in ['Legendary', 'Special']:
            raise PrestigeError(f'{char_from_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]} can\'t be prestiged to, due to **{rarity}** rarity.')
        prestige_from_ids, recipe_count = await __get_prestige_from_ids_and_recipe_count(char_from_info)
        utils.make_dict_value_lists_unique(prestige_from_ids)
        prestige_from_infos = sorted(__prepare_prestige_infos(chars_data, prestige_from_ids), key=lambda prestige_from_info: prestige_from_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME])
        if prestige_from_infos:
            prestige_from_details_collection = __create_prestige_from_details_collection_from_infos(prestige_from_infos)

            if as_embed:
                title = f'{char_from_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]} ({recipe_count} prestige combinations)'
                thumbnail_url = await sprites.get_download_sprite_link(char_from_info['ProfileSpriteId'])
                return (await prestige_from_details_collection.get_entities_details_as_embed(ctx, custom_title=title, custom_thumbnail_url=thumbnail_url, display_inline=False))
            else:
                title = f'**{char_from_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]}** ({recipe_count} prestige combinations)'
                return (await prestige_from_details_collection.get_entities_details_as_text(custom_title=title, big_set_details_type=entity.EntityDetailsType.LONG))
        else:
            raise PrestigeNoResultsError(f'There are no prestige recipes using this crew: `{char_from_info.get(CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME)}`')


def __create_and_add_prestige_from_cache(char_design_id: str) -> PssCache:
    cache = __create_prestige_from_cache(char_design_id)
    __prestige_from_cache_dict[char_design_id] = cache
    return cache


def __create_prestige_from_cache(char_design_id: str) -> PssCache:
    url = f'{__PRESTIGE_FROM_BASE_PATH}{char_design_id}'
    name = f'PrestigeFrom{char_design_id}'
    result = PssCache(url, name, None)
    return result


async def __get_prestige_from_ids_and_recipe_count(char_info: EntityInfo) -> Tuple[Dict[str, List[str]], int]:
    char_design_id = char_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in __prestige_from_cache_dict.keys():
        prestige_from_cache = __prestige_from_cache_dict[char_design_id]
    else:
        prestige_from_cache = __create_and_add_prestige_from_cache(char_design_id)
    raw_data_dict = await prestige_from_cache.get_raw_data_dict()
    prestige_from_infos = list(raw_data_dict['CharacterService']['PrestigeCharacterFrom']['Prestiges'].values())
    result = {}
    recipe_count = 0
    for value in prestige_from_infos:
        result.setdefault(value['ToCharacterDesignId'], []).append(value['CharacterDesignId2'])
        recipe_count += 1
    result = {char_to_id: list(set(chars_2_ids)) for char_to_id, chars_2_ids in result.items()}
    return result, recipe_count





# ---------- Prestige to Info ----------

async def get_prestige_to_info(ctx: Context, char_name: str, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    pss_assert.valid_entity_name(char_name, 'char_name', min_length=2)

    chars_data = await characters_designs_retriever.get_data_dict3()
    char_to_info = await characters_designs_retriever.get_entity_info_by_name(char_name, chars_data)

    if not char_to_info:
        raise NotFound(f'Could not find a crew named `{char_name}`.')
    else:
        rarity = char_to_info.get('Rarity')
        if rarity in ['Common', 'Special']:
            raise PrestigeError(f'{char_to_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]} can\'t be prestiged into, due to **{rarity}** rarity.')
        prestige_to_ids, recipe_count = await __get_prestige_to_ids_and_recipe_count(char_to_info)
        utils.make_dict_value_lists_unique(prestige_to_ids)
        prestige_to_infos = sorted(__prepare_prestige_infos(chars_data, prestige_to_ids), key=lambda prestige_to_info: prestige_to_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME])
        if prestige_to_infos:
            prestige_to_details_collection = __create_prestige_to_details_collection_from_infos(prestige_to_infos)

            if as_embed:
                title = f'{char_to_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]} ({recipe_count} prestige recipes)'
                thumbnail_url = await sprites.get_download_sprite_link(char_to_info['ProfileSpriteId'])
                return (await prestige_to_details_collection.get_entities_details_as_embed(ctx, custom_title=title, custom_thumbnail_url=thumbnail_url, display_inline=False))
            else:
                title = f'**{char_to_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]}** ({recipe_count} prestige recipes)'
                return (await prestige_to_details_collection.get_entities_details_as_text(custom_title=title, big_set_details_type=entity.EntityDetailsType.LONG))
        else:
            raise PrestigeNoResultsError(f'There are no prestige recipes yielding this crew: `{char_to_info.get(CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME)}`')


def __create_and_add_prestige_to_cache(char_design_id: str) -> PssCache:
    cache = __create_prestige_to_cache(char_design_id)
    __prestige_to_cache_dict[char_design_id] = cache
    return cache


def __create_prestige_to_cache(char_design_id: str) -> PssCache:
    url = f'{__PRESTIGE_TO_BASE_PATH}{char_design_id}'
    name = f'PrestigeTo{char_design_id}'
    result = PssCache(url, name, None)
    return result


async def __get_prestige_to_ids_and_recipe_count(char_info: EntityInfo) -> Tuple[Dict[str, List[str]], int]:
    char_design_id = char_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in __prestige_to_cache_dict.keys():
        prestige_to_cache = __prestige_to_cache_dict[char_design_id]
    else:
        prestige_to_cache = __create_and_add_prestige_to_cache(char_design_id)
    raw_data_dict = await prestige_to_cache.get_raw_data_dict()
    prestige_to_infos = list(raw_data_dict['CharacterService']['PrestigeCharacterTo']['Prestiges'].values())
    recipe_count = len(prestige_to_infos)
    all_recipes = []
    for value in prestige_to_infos:
        all_recipes.append((value['CharacterDesignId1'], value['CharacterDesignId2']))
        all_recipes.append((value['CharacterDesignId2'], value['CharacterDesignId1']))
    all_recipes = list(set(all_recipes))
    result = __normalize_prestige_to_data(all_recipes)
    for char_1_id in result.keys():
        for char_2_id, char_1_ids in result.items():
            if char_1_id != char_2_id and char_1_id in char_1_ids:
                result[char_1_id].append(char_2_id)
    return result, recipe_count


def __normalize_prestige_to_data(all_recipes: List[Tuple[str, str]]) -> Dict[str, List[str]]:
    all_recipes = list(all_recipes)
    all_char_ids = [recipe[0] for recipe in all_recipes]
    char_id_counts = sorted([(char_id, count) for char_id, count in dict(Counter(all_char_ids)).items()], key=lambda x: x[1], reverse=True)
    result = {}
    for char_id, _ in char_id_counts:
        for recipe in list(all_recipes):
            if recipe[0] == char_id:
                if recipe[1] not in result.get(char_id, []):
                    result.setdefault(char_id, []).append(recipe[1])
                all_recipes.remove(recipe)
            elif recipe[1] == char_id:
                if recipe[0] not in result.get(char_id, []):
                    result.setdefault(char_id, []).append(recipe[0])
                all_recipes.remove(recipe)
    return result





# ---------- Level Info ----------

def get_level_costs(ctx: Context, from_level: int, to_level: int = None, as_embed: bool = settings.USE_EMBEDS) -> Union[List[Embed], List[str]]:
    if from_level:
        pss_assert.parameter_is_valid_integer(from_level, 'from_level', 1, to_level - 1)
        pss_assert.parameter_is_valid_integer(to_level, 'to_level', from_level + 1, 40)
    else:
        pss_assert.parameter_is_valid_integer(to_level, 'to_level', 2, 40)
        from_level = 1

    crew_costs = __get_crew_costs(from_level, to_level, lookups.GAS_COSTS_LOOKUP, lookups.XP_COSTS_LOOKUP)
    legendary_crew_costs = __get_crew_costs(from_level, to_level, lookups.GAS_COSTS_LEGENDARY_LOOKUP, lookups.XP_COSTS_LEGENDARY_LOOKUP)

    crew_cost_txt = __get_crew_costs_as_text(from_level, to_level, crew_costs)
    legendary_crew_cost_txt = __get_crew_costs_as_text(from_level, to_level, legendary_crew_costs)

    if as_embed:
        embed_color = utils.discord.get_bot_member_colour(ctx.bot, ctx.guild)
        fields = [
            ('Non-legendary crew', '\n'.join(crew_cost_txt), False),
            ('Legendary crew', '\n'.join(legendary_crew_cost_txt), False)
        ]
        result = [utils.discord.create_embed(title='Level costs', fields=fields, colour=embed_color, footer='Note: Gas costs are higher, if "Advanced Training 7" hasn\'t been reseached, yet.')]
    else:
        result = ['**Level costs** (non-legendary crew, max research)']
        result.extend(crew_cost_txt)
        result.append(utils.discord.ZERO_WIDTH_SPACE)
        result.append('**Level costs** (legendary crew, max research)')
        result.extend(legendary_crew_cost_txt)
        result.append(utils.discord.ZERO_WIDTH_SPACE)
        result.append('**Note:** Gas costs are higher, if **Advanced Training 7** hasn\'t been reseached, yet.')
    return result


def __get_crew_costs(from_level: int, to_level: int, gas_costs_lookup: List[int], xp_cost_lookup: List[int]) -> Tuple[int, int, int, int]:
    gas_cost = gas_costs_lookup[to_level - 1]
    xp_cost = xp_cost_lookup[to_level - 1]
    gas_cost_from = sum(gas_costs_lookup[from_level:to_level])
    xp_cost_from = sum(xp_cost_lookup[from_level:to_level])

    if from_level > 1:
        return (None, None, gas_cost_from, xp_cost_from)
    else:
        return (gas_cost, xp_cost, gas_cost_from, xp_cost_from)


def __get_crew_costs_as_text(from_level: int, to_level: int, costs: Tuple[int, int, int, int]) -> List[str]:
    result = []
    if from_level == 1:
        result.append(f'Getting from level {to_level - 1:d} to {to_level:d} requires {costs[1]:,} {emojis.pss_stat_xp} and {costs[0]:,}{emojis.pss_gas_big}.')
    result.append(f'Getting from level {from_level:d} to {to_level:d} requires {costs[3]:,} {emojis.pss_stat_xp} and {costs[2]:,}{emojis.pss_gas_big}.')

    return result





# ---------- Transformation functions ----------

def __get_ability(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, level: int, **kwargs) -> Optional[str]:
    if entity.entity_property_has_value(character_info['SpecialAbilityType']):
        result = lookups.SPECIAL_ABILITIES_LOOKUP.get(character_info['SpecialAbilityType'], character_info['SpecialAbilityType'])
    else:
        result = None
    return result


def __get_ability_stat(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, level: int, **kwargs) -> Optional[str]:
    value = __get_stat(character_info, characters_data, collections_data, level, stat_name='SpecialAbilityArgument')
    if character_info['SpecialAbilityType']:
        special_ability = lookups.SPECIAL_ABILITIES_LOOKUP.get(character_info['SpecialAbilityType'], character_info['SpecialAbilityType'])
    else:
        special_ability = None
    if special_ability:
        result = f'{value} ({special_ability})'
    else:
        result = value
    return result


def __get_collection_hyperlink(collection_info: EntityInfo, collections_data: EntitiesData, characters_data: EntitiesData, **kwargs) -> Optional[str]:
    return '<https://pixelstarships.fandom.com/wiki/Category:Crew_Collections>'


def __get_collection_member_count(collection_info: EntityInfo, collections_data: EntitiesData, characters_data: EntitiesData, **kwargs) -> Optional[str]:
    collection_id = collection_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_infos = [characters_data[char_id] for char_id in characters_data.keys() if characters_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = len(chars_designs_infos)
    return f'{result} members'


def __get_collection_member_names(collection_info: EntityInfo, collections_data: EntitiesData, characters_data: EntitiesData, **kwargs) -> Optional[str]:
    collection_id = collection_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_infos = [characters_data[char_id] for char_id in characters_data.keys() if characters_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = [char_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME] for char_info in chars_designs_infos]
    result.sort()
    return ', '.join(result)


def __get_collection_name(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, **kwargs) -> Optional[str]:
    result = None
    collection_id = character_info[COLLECTION_DESIGN_KEY_NAME]
    if collection_id and int(collection_id):
        result = collections_data[collection_id][COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME]
    return result


def __get_collection_perk(collection_info: EntityInfo, collections_data: EntitiesData, characters_data: EntitiesData, **kwargs) -> Optional[str]:
    enhancement_type = collection_info['EnhancementType']
    result = lookups.COLLECTION_PERK_LOOKUP.get(enhancement_type, enhancement_type)
    return result


def __get_crew_card_hyperlink(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, level: int, **kwargs) -> Optional[str]:
    crew_name: str = character_info.get(CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME)
    if crew_name:
        crew_name_escaped = utils.convert.url_escape(crew_name)
        url = f'https://pixelperfectguide.com/crew/cards/?CrewName={crew_name_escaped}'
        result = f'<{url}>'
        return result
    else:
        return None


def __get_pixel_prestige_hyperlink(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, level: int, **kwargs) -> Optional[str]:
    crew_id: str = character_info.get(CHARACTER_DESIGN_KEY_NAME)
    if crew_id:
        url = f'https://pixel-prestige.com/crew.php?nId={crew_id}'
        return f'<{url}>'
    else:
        return None


def __get_embed_color(collection_info: EntityInfo, collections_data: EntitiesData, characters_data: EntitiesData, **kwargs) -> Colour:
    color_string = collection_info.get('ColorString')
    if entity.entity_property_has_value(color_string):
        result = utils.discord.convert_color_string_to_embed_color(color_string)
    else:
        result = Embed.Empty
    return result


def __get_enhancement(collection_info: EntityInfo, collections_data: EntitiesData, characters_data: EntitiesData, **kwargs) -> Optional[str]:
    base_enhancement_value = collection_info['BaseEnhancementValue']
    step_enhancement_value = collection_info['StepEnhancementValue']
    result = f'{base_enhancement_value} (Base), {step_enhancement_value} (Step)'
    return result


def __get_level(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, level: int, **kwargs) -> Optional[str]:
    if level is None:
        return None
    else:
        return str(level)


def __get_members_count_display_name(collection_info: EntityInfo, collections_data: EntitiesData, characters_data: EntitiesData, **kwargs) -> Optional[str]:
    collection_id = collection_info[COLLECTION_DESIGN_KEY_NAME]
    chars_designs_infos = [characters_data[char_id] for char_id in characters_data.keys() if characters_data[char_id][COLLECTION_DESIGN_KEY_NAME] == collection_id]
    result = f'Members ({len(chars_designs_infos)})'
    return result


def __get_min_max_combo(collection_info: EntityInfo, collections_data: EntitiesData, characters_data: EntitiesData, **kwargs) -> Optional[str]:
    min_combo = collection_info['MinCombo']
    max_combo = collection_info['MaxCombo']
    result = f'{min_combo}...{max_combo}'
    return result


def __get_name_with_level(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, level: int, **kwargs) -> Optional[str]:
    result = character_info.get(CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME)
    if level:
        result += f' {settings.DEFAULT_HYPHEN} Level {level}'
    return result


def __get_prestige_from_title(character_info: EntityInfo, for_embed: bool = None, **kwargs) -> Optional[str]:
    char_name = character_info.get(CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME)
    if for_embed:
        result = f'To {char_name} with'
    else:
        result = f'To {char_name} with:'
    return result


def __get_prestige_names(character_info: EntityInfo, separator: str = ', ', **kwargs) -> Optional[str]:
    result = sorted([prestige_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME] for prestige_info in character_info['Prestige']])
    return separator.join(result)


def __get_prestige_to_title(character_info: EntityInfo, for_embed: bool = None, **kwargs) -> Optional[str]:
    char_name = character_info.get(CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME)
    if for_embed:
        result = f'{char_name} with'
    else:
        result = f'{char_name} with:'
    return result


def __get_rarity(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, **kwargs) -> Optional[str]:
    rarity = character_info.get('Rarity')
    result = f'{rarity} {lookups.RARITY_EMOJIS_LOOKUP.get(rarity)}'
    return result


def __get_slots(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, **kwargs) -> Optional[str]:
    result = []
    equipment_mask = int(character_info['EquipmentMask'])
    for k in lookups.EQUIPMENT_MASK_LOOKUP.keys():
        if (equipment_mask & k) != 0:
            result.append(lookups.EQUIPMENT_MASK_LOOKUP[k])

    result = ', '.join(result) if result else settings.DEFAULT_HYPHEN
    return result


def __get_speed(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, **kwargs) -> Optional[str]:
    walk_speed = character_info['WalkingSpeed']
    run_speed = character_info['RunSpeed']
    result = f'{walk_speed}/{run_speed}'
    return result


def __get_stat(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, level: int, stat_name: str, **kwargs) -> Optional[str]:
    is_special_stat = stat_name.lower().startswith('specialability')
    if is_special_stat:
        max_stat_name = 'SpecialAbilityFinalArgument'
    else:
        max_stat_name = f'Final{stat_name}'
    min_value = float(character_info[stat_name])
    max_value = float(character_info[max_stat_name])
    progression_type = character_info['ProgressionType']
    result = __get_stat_value(min_value, max_value, level, progression_type)
    return result





# ---------- Create entity.entity.EntityDetails ----------

def __create_character_details_from_info(character_info: EntityInfo, characters_data: EntitiesData, collections_data: EntitiesData, level: int) -> entity.entity.EntityDetails:
    return entity.entity.EntityDetails(character_info, __properties['character_title'], __properties['character_description'], __properties['character_properties'], __properties['character_embed_settings'], characters_data, collections_data, level=level)


def __create_characters_details_collection_from_infos(characters_designs_infos: List[EntityInfo], characters_data: EntitiesData, collections_data: EntitiesData, level: int) -> entity.EntityDetailsCollection:
    characters_details = [__create_character_details_from_info(character_info, characters_data, collections_data, level) for character_info in characters_designs_infos]
    result = entity.EntityDetailsCollection(characters_details, big_set_threshold=2)
    return result



def __create_collection_details_from_info(collection_info: EntityInfo, collections_data: EntitiesData, characters_data: EntitiesData) -> entity.entity.EntityDetails:
    return entity.entity.EntityDetails(collection_info, __properties['collection_title'], __properties['collection_description'], __properties['collection_properties'], __properties['collection_embed_settings'], collections_data, characters_data)


def __create_collections_details_collection_from_infos(collections_infos: List[EntityInfo], collections_data: EntitiesData, characters_data: EntitiesData) -> entity.EntityDetailsCollection:
    collections_details = [__create_collection_details_from_info(collection_info, collections_data, characters_data) for collection_info in collections_infos]
    result = entity.EntityDetailsCollection(collections_details, big_set_threshold=2)
    return result



def __create_prestige_from_details_from_info(character_info: EntityInfo) -> entity.entity.EntityDetails:
    result = entity.entity.EntityDetails(character_info, __properties['prestige_from_title'], entity.NO_PROPERTY, __properties['prestige_from_properties'], __properties['character_embed_settings'], prefix='> ')
    return result


def __create_prestige_from_details_collection_from_infos(characters_infos: List[EntityInfo]) -> entity.EntityDetailsCollection:
    characters_details = [__create_prestige_from_details_from_info(character_info) for character_info in characters_infos]
    result = entity.EntityDetailsCollection(characters_details, big_set_threshold=2, add_empty_lines=False)
    return result



def __create_prestige_to_details_from_info(character_info: EntityInfo) -> entity.entity.EntityDetails:
    result = entity.entity.EntityDetails(character_info, __properties['prestige_to_title'], entity.NO_PROPERTY, __properties['prestige_to_properties'], __properties['character_embed_settings'], prefix='> ')
    return result


def __create_prestige_to_details_collection_from_infos(characters_infos: List[EntityInfo]) -> entity.EntityDetailsCollection:
    characters_details = [__create_prestige_to_details_from_info(character_info) for character_info in characters_infos]
    result = entity.EntityDetailsCollection(characters_details, big_set_threshold=2, add_empty_lines=False)
    return result





# ---------- Helper functions ----------

def get_crew_search_details(character_info: EntityInfo) -> str:
    result = character_info[CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME]
    return result


def __calculate_stat_value(min_value: float, max_value: float, level: int, progression_type: str) -> float:
    exponent = lookups.PROGRESSION_TYPES[progression_type]
    result = min_value + (max_value - min_value) * ((level - 1) / 39) ** exponent
    return result


def __get_stat_value(min_value: float, max_value: float, level: int, progression_type: str) -> str:
    if level is None or level < 1 or level > 40:
        return f'{min_value:0.1f} - {max_value:0.1f}'
    else:
        return f'{__calculate_stat_value(min_value, max_value, level, progression_type):0.1f}'


def __prepare_prestige_infos(characters_data: EntitiesData, prestige_ids: Dict[str, List[str]]) -> List[EntityInfo]:
    result = []
    for char_1_id, chars_2_ids in prestige_ids.items():
        char_1_info = characters_data[char_1_id]
        char_1_info['Prestige'] = [characters_data[char_2_id] for char_2_id in chars_2_ids]
        result.append(char_1_info)
    return result





# ---------- Initilization ----------

__prestige_from_cache_dict = {}
__prestige_to_cache_dict = {}

characters_designs_retriever = entity.EntityRetriever(
    CHARACTER_DESIGN_BASE_PATH,
    CHARACTER_DESIGN_KEY_NAME,
    CHARACTER_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='CharacterDesigns'
)


collections_designs_retriever = entity.EntityRetriever(
    COLLECTION_DESIGN_BASE_PATH,
    COLLECTION_DESIGN_KEY_NAME,
    COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME,
    cache_name='CollectionDesigns'
)


__properties: entity.EntityDetailsCreationPropertiesCollection = {
    'character_title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, transform_function=__get_name_with_level)
    ),
    'character_description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, omit_if_none=False, entity_property_name='CharacterDesignDescription'),
        property_short=entity.NO_PROPERTY
    ),
    'character_properties': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Rarity', True, transform_function=__get_rarity),
            entity.EntityDetailProperty('Race', True, entity_property_name='RaceType'),
            entity.EntityDetailProperty('Collection', True, transform_function=__get_collection_name),
            entity.EntityDetailProperty('Gender', True, entity_property_name='GenderType'),
            entity.EntityDetailProperty('Ability', True, transform_function=__get_ability_stat),
            entity.EntityDetailProperty('HP', True, transform_function=__get_stat, stat_name='Hp'),
            entity.EntityDetailProperty('Attack', True, transform_function=__get_stat, stat_name='Attack'),
            entity.EntityDetailProperty('Repair', True, transform_function=__get_stat, stat_name='Repair'),
            entity.EntityDetailProperty('Pilot', True, transform_function=__get_stat, stat_name='Pilot'),
            entity.EntityDetailProperty('Science', True, transform_function=__get_stat, stat_name='Science'),
            entity.EntityDetailProperty('Engine', True, transform_function=__get_stat, stat_name='Engine'),
            entity.EntityDetailProperty('Weapon', True, transform_function=__get_stat, stat_name='Weapon'),
            entity.EntityDetailProperty('Walk/run speed', True, transform_function=__get_speed),
            entity.EntityDetailProperty('Fire resist', True, entity_property_name='FireResistance'),
            entity.EntityDetailProperty('Training cap', True, entity_property_name='TrainingCapacity'),
            entity.EntityDetailProperty('Slots', True, transform_function=__get_slots),
            entity.EntityDetailProperty('Role scores', True, transform_function=__get_pixel_prestige_hyperlink)
        ],
        properties_short=[
            entity.EntityDetailProperty('Rarity', False, entity_property_name='Rarity'),
            entity.EntityDetailProperty('Ability', False, transform_function=__get_ability),
            entity.EntityDetailProperty('Collection', True, transform_function=__get_collection_name)
        ]),
    'character_embed_settings': {
        'thumbnail_url': entity.EntityDetailProperty('thumbnail_url', False, entity_property_name='ProfileSpriteId', transform_function=sprites.get_download_sprite_link_by_property)
    },
    'collection_title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, entity_property_name=COLLECTION_DESIGN_DESCRIPTION_PROPERTY_NAME)
    ),
    'collection_description': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Description', False, entity_property_name='CollectionDescription'),
        property_short=entity.NO_PROPERTY
    ),
    'collection_properties': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('Combo Min...Max', True, transform_function=__get_min_max_combo),
            entity.EntityDetailProperty(__get_collection_perk, True, transform_function=__get_enhancement),
            entity.EntityDetailTextOnlyProperty(__get_members_count_display_name, True, transform_function=__get_collection_member_names),
            entity.EntityDetailEmbedOnlyProperty(__get_members_count_display_name, True, transform_function=__get_collection_member_names, display_inline=False),
            entity.EntityDetailProperty('Hyperlink', False, transform_function=__get_collection_hyperlink)
        ],
        properties_short=[
            entity.EntityDetailProperty('Perk', False, transform_function=__get_collection_perk),
            entity.EntityDetailProperty('Member count', False, transform_function=__get_collection_member_count)
        ]),
    'collection_embed_settings': {
        'color': entity.EntityDetailProperty('color', False, transform_function=__get_embed_color),
        'image_url': entity.EntityDetailProperty('image_url', False, entity_property_name='SpriteId', transform_function=sprites.get_download_sprite_link_by_property),
        'thumbnail_url': entity.EntityDetailProperty('thumbnail_url', False, entity_property_name='IconSpriteId', transform_function=sprites.get_download_sprite_link_by_property)
    },
    'prestige_from_title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, transform_function=__get_prestige_from_title, for_embed=False),
        property_embed=entity.EntityDetailEmbedOnlyProperty('Title', False, omit_if_none=False, transform_function=__get_prestige_from_title, for_embed=True),
    ),
    'prestige_from_properties': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('2nd crew', False, transform_function=__get_prestige_names)
        ]
    ),
    'prestige_to_title': entity.EntityDetailPropertyCollection(
        entity.EntityDetailProperty('Title', False, omit_if_none=False, transform_function=__get_prestige_to_title, for_embed=False),
        property_embed=entity.EntityDetailEmbedOnlyProperty('Title', False, omit_if_none=False, transform_function=__get_prestige_to_title, for_embed=True),
    ),
    'prestige_to_properties': entity.EntityDetailPropertyListCollection(
        [
            entity.EntityDetailProperty('2nd crew', False, transform_function=__get_prestige_names)
        ]
    )
}





async def init() -> None:
    pass