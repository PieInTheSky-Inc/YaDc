#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from cache import PssCache
import pss_core as core
import utility as util


character_designs_cache = None
collection_designs_cache = None
prestige_from_cache_dict = {}
prestige_to_cache_dict = {}

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


# ---------- Initialization ----------

character_designs_cache = PssCache(
    f'{core.get_base_url()}CharacterService/ListAllCharacterDesigns2?languageKey=en',
    'CharacterDesigns',
    'CharacterDesignId')

collection_designs_cache = PssCache(
    f'{core.get_base_url()}CollectionService/ListAllCollectionDesigns?languageKey=en',
    'CollectionDesigns',
    'CollectionDesignId')


# ---------- Crew info ----------

def get_char_info(char_name, as_embed=False):
    char_data = character_designs_cache.get_data()
    char_design_id = _get_char_design_id_from_name(char_data, char_name)

    if char_design_id in char_data.keys():
        char_info = char_data[char_design_id]
        if as_embed:
            return _get_char_info_as_embed(char_info)
        else:
            return _get_char_info_as_text(char_info)
    else:
        return f'Could not find a crew named {char_name}'


def _get_char_design_id_from_name(char_data, char_name):
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
    collection_data = collection_designs_cache.get_data()
    collection_design_id = _get_collection_design_id_from_name(collection_data, collection_name)

    if collection_design_id in collection_data.keys():
        collection_info = collection_data[collection_design_id]
        if as_embed:
            return _get_collection_info_as_embed(collection_info)
        else:
            return _get_collection_info_as_text(collection_info)
    else:
        return f'Could not find a collection named {collection_name}'


def _get_collection_design_id_from_name(collection_data, collection_name):
    fixed_data = {fix_char_name(collection_data[id]['CollectionDesignName']): id for id in collection_data}
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
    collection_id = collection_info['CollectionDesignId']
    char_data = character_designs_cache.get_data()
    char_infos = [char_data[char_id] for char_id in char_data.keys() if char_data[char_id]['CollectionId'] == collection_id]
    result = [char_info['CharacterDesignName'] for char_info in char_infos]
    return result


def fix_collection_name(collection_name):
    result = collection_name.lower()
    return result