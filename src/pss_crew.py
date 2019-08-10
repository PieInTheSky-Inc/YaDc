#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from cache import PssCache
import pss_core as core
import utility as util


character_design_cache = None
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

character_design_cache = PssCache(
    f'{core.get_base_url()}CharacterService/ListAllCharacterDesigns2?languageKey=en',
    'CharacterDesigns',
    'CharacterDesignId')

collection_designs_cache = PssCache(
    f'{core.get_base_url()}CollectionService/ListAllCollectionDesigns?languageKey=en',
    'CollectionDesigns',
    'CollectionDesignId')


# ---------- Functions ----------

def get_stats(char_name, as_embed=False):
    char_data = character_design_cache.get_data()
    char_design_id = get_char_design_id_from_name(char_data, char_name)
    if as_embed:
        return _get_stats_as_embed(char_data, char_design_id)
    else:
        return _get_stats_as_text(char_data, char_design_id)


def get_char_design_id_from_name(char_data, char_name):
    fixed_data = {char_data[id]['CharacterDesignName'].lower(): id for id in char_data}
    fixed_char_name = char_name.lower()
    result = None
    if fixed_char_name in fixed_data.keys():
        return fixed_data[fixed_char_name]

    results = [fixed_data[name] for name in fixed_data if fixed_data[name].startswith(fixed_char_name)]

    if len(results) < 1:
        return None
    else:
        return results[0]


def _get_stats_as_embed(char_data, char_design_id):
    return ''


def _get_stats_as_text(char_data, char_design_id):
    stats = char_data[char_design_id]
    char_name = stats['CharacterDesignName']
    special = stats['SpecialAbilityType']
    if special in SPECIAL_ABILITIES_LOOKUP.keys():
        special = SPECIAL_ABILITIES_LOOKUP[special]
        equipment_slots = _convert_equipment_mask(int(stats['EquipmentMask']))

    collection_name = 'None'
    collection_id = stats['CollectionDesignId']
    if collection_id:
        collection_data = collection_designs_cache.get_data()
        if collection_data and collection_id in collection_data.keys():
            collection_name = collection_data[collection_id]['CollectionName']

    lines = ['**{}** ({})'.format(char_name, stats['Rarity'])]
    lines.append(stats['CharacterDesignDescription'])
    lines.append('Race: {}, Collection: {}, Gender: {}'.format(
        stats['RaceType'],
        collection_name,
        stats['GenderType']))
    lines.append('ability = {} ({})'.format(stats['SpecialAbilityFinalArgument'], special))
    lines.append('hp = {}'.format(stats['FinalHp']))
    lines.append('attack = {}'.format(stats['FinalAttack']))
    lines.append('repair = {}'.format(stats['FinalRepair']))
    lines.append('pilot = {}'.format(stats['FinalPilot']))
    lines.append('science = {}'.format(stats['FinalScience']))
    lines.append('weapon = {}'.format(stats['FinalWeapon']))
    lines.append('engine = {}'.format(stats['FinalEngine']))
    lines.append('walk/run speed = {}/{}'.format(stats['WalkingSpeed'], stats['RunSpeed']))
    lines.append('fire resist = {}'.format(stats['FireResistance']))
    lines.append('training capacity = {}'.format(stats['TrainingCapacity']))
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
