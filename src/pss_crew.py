#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from threading import Thread, Lock

from cache import PssCache
import pss_core as core
import utility as util


collection_designs_cache = None

SPECIAL_ABILITIES_LOOKUP = {
    'AddReload': 'Rush Command',
    'DamageToCurrentEnemy': 'Critical Strike',
    'DamageToRoom': 'Ultra Dismantle',
    'DamageToSameRoomCharacters': 'Poison Gas',
    'DeductReload': 'System Hack',
    'FireWalk': 'Fire Walk',
    'Freeze': 'Freeze',
    'HealRoomHp': 'Urgent Repair',
    'HealSameRoomCharacters': 'Healing Rain',
    'HealSelfHp': 'First Aid',
    'SetFire': 'Arson'}

EQUIPMENT_MASK_LOOKUP = {
    1: 'head',
    2: 'body',
    4: 'leg',
    8: 'weapon',
    16: 'accessory'}


# ---------- Crew info ----------

CHARACTER_DESIGN_KEY_NAME = 'CharacterDesignId'

character_designs_cache = PssCache(
    f'{core.get_base_url()}CharacterService/ListAllCharacterDesigns2?languageKey=en',
    'CharacterDesigns',
    CHARACTER_DESIGN_KEY_NAME)


def get_char_info(char_name, as_embed=False):
    char_info = _get_char_info(char_name)

    if char_info is None:
        return f'Could not find a crew named **{char_name}**.'
    else:
        if as_embed:
            return _get_char_info_as_embed(char_info)
        else:
            return _get_char_info_as_text(char_info)


def _get_char_info(char_name):
    char_design_data = character_designs_cache.get_data()
    char_design_id = _get_char_design_id_from_name(char_name, char_design_data)

    if char_design_id and char_design_id in char_design_data.keys():
        return char_design_data[char_design_id]
    else:
        return None



def _get_char_design_id_from_name(char_name, char_data=None):
    if char_data is None:
        char_data = character_designs_cache.get_data()
    fixed_data = {fix_char_name(char_data[id]['CharacterDesignName']): id for id in char_data}
    fixed_char_name = fix_char_name(char_name)

    if fixed_char_name in fixed_data.keys():
        return fixed_data[fixed_char_name]
    results = [fixed_data[name] for name in fixed_data if fixed_data[name].startswith(fixed_char_name)]

    if len(results) < 1:
        return None
    else:
        return results[0]


def _get_char_info_as_embed(char_info):
    return ''


def _get_char_info_as_text(char_info):
    char_name = char_info['CharacterDesignName']
    special = char_info['SpecialAbilityType']
    if special in SPECIAL_ABILITIES_LOOKUP.keys():
        special = SPECIAL_ABILITIES_LOOKUP[special]
        equipment_slots = _convert_equipment_mask(int(char_info['EquipmentMask']))

    collection_name = 'None'
    collection_id = char_info['CollectionDesignId']
    if collection_id:
        collection_data = collection_designs_cache.get_data()
        if collection_data and collection_id in collection_data.keys():
            collection_name = collection_data[collection_id]['CollectionName']

    lines = ['**{}** ({})'.format(char_name, char_info['Rarity'])]
    lines.append(char_info['CharacterDesignDescription'])
    lines.append('Race: {}, Collection: {}, Gender: {}'.format(
        char_info['RaceType'],
        collection_name,
        char_info['GenderType']))
    lines.append('ability = {} ({})'.format(char_info['SpecialAbilityFinalArgument'], special))
    lines.append('hp = {}'.format(char_info['FinalHp']))
    lines.append('attack = {}'.format(char_info['FinalAttack']))
    lines.append('repair = {}'.format(char_info['FinalRepair']))
    lines.append('pilot = {}'.format(char_info['FinalPilot']))
    lines.append('science = {}'.format(char_info['FinalScience']))
    lines.append('weapon = {}'.format(char_info['FinalWeapon']))
    lines.append('engine = {}'.format(char_info['FinalEngine']))
    lines.append('walk/run speed = {}/{}'.format(char_info['WalkingSpeed'], char_info['RunSpeed']))
    lines.append('fire resist = {}'.format(char_info['FireResistance']))
    lines.append('training capacity = {}'.format(char_info['TrainingCapacity']))
    lines.append('equipment = {}'.format(equipment_slots))

    return '\n'.join(lines)


def _convert_equipment_mask(eqpt_mask):
    result = []
    for k in EQUIPMENT_MASK_LOOKUP.keys():
        if (eqpt_mask & k) != 0:
            result.append(EQUIPMENT_MASK_LOOKUP[k])

    if result:
        return ', '.join(result)
    else:
        return None


def fix_char_name(char_name):
    result = char_name.lower()
    return result


# ---------- Collection Info ----------

collection_designs_cache = PssCache(
    f'{core.get_base_url()}CollectionService/ListAllCollectionDesigns?languageKey=en',
    'CollectionDesigns',
    'CollectionDesignId')

COLLECTION_PERK_LOOKUP = {
    'BloodThirstSkill': 'Vampirism',
    'EmpSkill': 'EMP Discharge',
    'FreezeAttackSkill': 'Cryo Field',
    'InstantKillSkill': 'Headshot',
    'MedicalSkill': 'Combat Medic',
    'ResurrectSkill': 'Resurrection',
    'SharpShooterSkill': 'Sharpshooter'
}


def get_collection_info(collection_name, as_embed=False):
    collection_info = _get_collection_info(collection_name)

    if collection_info is None:
        return f'Could not find a collection named **{collection_name}**.'
    else:
        if as_embed:
            return _get_collection_info_as_embed(collection_info)
        else:
            return _get_collection_info_as_text(collection_info)


def _get_collection_info(collection_name):
    collection_data = collection_designs_cache.get_data()
    collection_design_id = _get_collection_design_id_from_name(collection_data, collection_name)

    if collection_design_id and collection_design_id in collection_data.keys():
        return collection_data[collection_design_id]
    else:
        return None


def _get_collection_design_id_from_name(collection_data, collection_name):
    fixed_data = {fix_char_name(collection_data[id]['CollectionName']): id for id in collection_data}
    fixed_collection_name = fix_collection_name(collection_name)

    if fixed_collection_name in fixed_data.keys():
        return fixed_data[fixed_collection_name]

    results = [fixed_data[name] for name in fixed_data if fixed_data[name].startswith(fixed_collection_name)]
    if len(results) < 1:
        return None
    else:
        return results[0]


def _get_collection_info_as_embed(collection_info):
    # Use collection_info['ColorString'] for embed color
    return ''


def _get_collection_info_as_text(collection_info):
    collection_crew = _get_collection_crew(collection_info)
    collection_perk = collection_info['EnhancementType']
    if collection_perk in COLLECTION_PERK_LOOKUP.keys():
        collection_perk = COLLECTION_PERK_LOOKUP[collection_perk]

    lines = []
    lines.append('**{}**'.format(collection_info['CollectionName']))
    lines.append('{}'.format(collection_info['CollectionDescription']))
    lines.append('Combo Min...Max: {}...{}'.format(collection_info['MinCombo'], collection_info['MaxCombo']))
    lines.append('{}: {} (Base), {} (Step)'.format(collection_perk, collection_info['BaseEnhancementValue'], collection_info['StepEnhancementValue']))
    lines.append('Characters: {}'.format(', '.join(collection_crew)))

    return '\n'.join(lines)


def _get_collection_crew(collection_info):
    #util.dbg_prnt(f'+ _get_collection_crew(collection_info[{collection_info['CollectionName']}])')
    collection_id = collection_info['CollectionDesignId']
    char_data = character_designs_cache.get_data()
    char_infos = [char_data[char_id] for char_id in char_data.keys() if char_data[char_id]['CollectionDesignId'] == collection_id]
    result = [char_info['CharacterDesignName'] for char_info in char_infos]
    result.sort()
    return result


def fix_collection_name(collection_name):
    result = collection_name.lower()
    return result


# ---------- Prestige Info ----------

prestige_from_cache_dict = {}
prestige_to_cache_dict = {}

PRESTIGE_FROM_BASE_URL = f'{core.get_base_url}CharacterService/PrestigeCharacterFrom?languagekey=en&characterDesignId='
PRESTIGE_TO_BASE_URL = f'{core.get_base_url}CharacterService/PrestigeCharacterTo?languagekey=en&characterDesignId='


def get_prestige_from_info(char_name, as_embed=False):
    prestige_data = _get_prestige_from_data(char_name)

    if prestige_data is None:
        return f'Could not find prestige paths requiring **{char_name}**'
    else:
        if as_embed:
            return get_prestige_from_info_as_embed(prestige_data)
        else:
            return get_prestige_from_info_as_txt(prestige_data)


def get_prestige_to_info(char_name, as_embed=False):
    prestige_data = _get_prestige_to_data(char_name)

    if prestige_data is None:
        return f'Could not find prestige paths leading to **{char_name}**'
    else:
        if as_embed:
            return get_prestige_to_info_as_embed(prestige_data)
        else:
            return get_prestige_to_info_as_txt(prestige_data)


def get_prestige_from_info_as_embed(prestige_from_data):
    return ''


def get_prestige_from_info_as_txt(prestige_from_data):
    # Format: '+ {id2} = {toid}


    lines = []
    lines.append('**{} can be prestiged to'.format(prestige_from_data))


def get_prestige_to_info_as_embed(prestige_to_data):
    return ''


def get_prestige_to_info_as_txt(prestige_to_data):
    # Format: '{id1} + {id2}
    i = 0


def _get_prestige_from_data(char_name):
    char_info = _get_char_info(char_name)
    if char_info is None:
        return None

    char_design_id = char_info[CHARACTER_DESIGN_KEY_NAME]
    if char_design_id in prestige_from_cache_dict.keys():
        prestige_from_cache = prestige_from_cache_dict[char_info[CHARACTER_DESIGN_KEY_NAME]]
    else:
        prestige_from_cache = _create_and_add_prestige_from_cache(char_info[CHARACTER_DESIGN_KEY_NAME])
    return prestige_from_cache.get_data()


def _get_prestige_to_data(char_name):
    char_info = _get_char_info(char_name)
    if char_info is None:
        return None

    if char_design_id in prestige_to_cache_dict.keys():
        prestige_to_cache = prestige_to_cache_dict[char_info[CHARACTER_DESIGN_KEY_NAME]]
    else:
        prestige_to_cache = _create_and_add_prestige_to_cache(char_info[CHARACTER_DESIGN_KEY_NAME])
    return prestige_to_cache.get_data()


def _create_and_add_prestige_from_cache(char_design_id):
    cache = _create_prestige_from_cache(char_design_id)
    prestige_from_cache_dict[char_design_id] = cache
    return cache


def _create_and_add_prestige_to_cache(char_design_id):
    cache = _create_prestige_to_cache(char_design_id)
    prestige_to_cache_dict[char_design_id] = cache
    return cache


def _create_prestige_from_cache(char_design_id):
    url = f'{PRESTIGE_FROM_BASE_URL}{char_design_id}'
    name = f'PrestigeFrom{char_design_id}'
    result = PssCache(url, name, None)
    return result


def _create_prestige_to_cache(char_design_id):
    url = f'{PRESTIGE_TO_BASE_URL}{char_design_id}'
    name = f'PrestigeTo{char_design_id}'
    result = PssCache(url, name, None)
    return result