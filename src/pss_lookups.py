#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import calendar
import typing

import emojis


ALLIANCE_MEMBERSHIP = {
    'Candidate': 'Candidate',
    'Ensign': 'Ensign',
    'Major': 'Major',
    'Lieutenant': 'Lieutenant',
    'Commander': 'Commander',
    'ViceAdmiral': 'Vice Admiral',
    'FleetAdmiral': 'Fleet Admiral'
}


COLLECTION_PERK_LOOKUP = {
    'BloodThirstSkill': 'Vampirism',
    'EmpSkill': 'EMP Discharge',
    'FreezeAttackSkill': 'Cryo Field',
    'InstantKillSkill': 'Headshot',
    'MedicalSkill': 'Combat Medic',
    'ResurrectSkill': 'Resurrection',
    'SharpShooterSkill': 'Sharpshooter'
}


CURRENCY_EMOJI_LOOKUP = {
    'starbux': emojis.pss_bux,
    'gas': emojis.pss_gas_big,
    'mineral': emojis.pss_min_big,
    'supply': emojis.pss_supply_big,
    'android': 'droids',
    'capacity': 'rounds',
    'equipment': 'items'
}


DMG_TYPES = [
    'SystemDamage',
    'CharacterDamage',
    'ShieldDamage',
    'HullDamage',
    'DirectSystemDamage'
]


DIVISION_CHAR_TO_DESIGN_ID = {
    '-': '0',
    'A': '1',
    'B': '2',
    'C': '3',
    'D': '4'
}


DIVISION_DESIGN_ID_TO_CHAR = dict([(value, key) for key, value in DIVISION_CHAR_TO_DESIGN_ID.items()])


EQUIPMENT_MASK_LOOKUP = {
    1: 'head',
    2: 'body',
    4: 'leg',
    8: 'weapon',
    16: 'accessory',
    32: 'pet'
}


EQUIPMENT_SLOTS_LOOKUP = {
    'head': 'EquipmentHead',
    'hat': 'EquipmentHead',
    'helm': 'EquipmentHead',
    'helmet': 'EquipmentHead',
    'body': 'EquipmentBody',
    'chest': 'EquipmentBody',
    'shirt': 'EquipmentBody',
    'armor': 'EquipmentBody',
    'leg': 'EquipmentLeg',
    'pant': 'EquipmentLeg',
    'pants': 'EquipmentLeg',
    'weapon': 'EquipmentWeapon',
    'hand': 'EquipmentWeapon',
    'gun': 'EquipmentWeapon',
    'accessory': 'EquipmentAccessory',
    'shoulder': 'EquipmentAccessory',
    'pet': 'EquipmentPet'
}


GAS_COSTS_LEGENDARY_LOOKUP = [
    0, 130000, 162500, 195000, 227500,
    260000, 292500, 325000, 357500, 390000,
    422500, 455000, 487500, 520000, 552500,
    585000, 617500, 650000, 682500, 715000,
    747500, 780000, 812500, 845000, 877500,
    910000, 942000, 975000, 1007500, 1040000,
    1072500, 1105000, 1137500, 1170000, 1202500,
    1235000, 1267500, 1300000, 1332500, 1365000]


GAS_COSTS_LOOKUP = [
    0, 0, 17, 33, 65,
    130, 325, 650, 1300, 3200,
    6500, 9700, 13000, 19500, 26000,
    35700, 43800, 52000, 61700, 71500,
    84500, 104000, 117000, 130000, 156000,
    175000, 201000, 227000, 253000, 279000,
    312000, 351000, 383000, 422000, 468000,
    507000, 552000, 604000, 650000, 715000]


GRID_TYPE_MASK_LOOKUP = {
    1: 'A',
    2: 'B'
}


MONTH_NAME_TO_NUMBER = dict({calendar.month_name[number]: number for number in range(1, 13)})
MONTH_SHORT_NAME_TO_NUMBER = dict({calendar.month_abbr[number]: number for number in range(1, 13)})


PROGRESSION_TYPES = {
    'Linear': 1.0,
    'EaseIn': 2.0,
    'EaseOut': 0.5
}


RARITY_ORDER_LOOKUP = {
    'Common': 70,
    'Elite': 60,
    'Unique': 50,
    'Epic': 40,
    'Hero': 30,
    'Special': 20,
    'Legendary': 10
}


REDUCE_TOKENS_LOOKUP = {
    0: '',
    1: 'k',
    2: 'm',
    3: 'g'
}


SALE_ITEM_MASK_LOOKUP = {
    1: ('Clip', 500),
    2: ('Roll', 1200),
    4: ('Stash', 2500),
    8: ('Case', 6500),
    16: ('Vault', 14000)
}


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
    'SetFire': 'Arson'
}


STAT_EMOJI_LOOKUP = {
    'Ability': emojis.pss_stat_ability,
    'Attack': emojis.pss_stat_attack,
    'Engine': emojis.pss_stat_engine,
    'FireResistance': emojis.pss_stat_fireresistance,
    'Hp': emojis.pss_stat_hp,
    'Pilot': emojis.pss_stat_pilot,
    'Repair': emojis.pss_stat_repair,
    'Science': emojis.pss_stat_research,
    'Stamina': emojis.pss_stat_stamina,
    'Weapon': emojis.pss_stat_weapon,
    'Xp': emojis.pss_stat_xp,
}


STAT_TYPES_LOOKUP = {
    'hp': 'HP',
    'health': 'HP',
    'attack': 'Attack',
    'atk': 'Attack',
    'att': 'Attack',
    'damage': 'Attack',
    'dmg': 'Attack',
    'repair': 'Repair',
    'rep': 'Repair',
    'ability': 'Ability',
    'abl': 'Ability',
    'pilot': 'Pilot',
    'plt': 'Pilot',
    'science': 'Science',
    'sci': 'Science',
    'stamina': 'Stamina',
    'stam': 'Stamina',
    'stm': 'Stamina',
    'engine': 'Engine',
    'eng': 'Engine',
    'weapon': 'Weapon',
    'wpn': 'Weapon',
    'fire resistance': 'FireResistance',
    'fire': 'FireResistance',
}


STAT_UNITS_LOOKUP = {
    'Ability': '%',
    'Attack': '%',
    'Engine': '%',
    'FireResistance': '',
    'Hp': '%',
    'Pilot': '%',
    'Repair': '%',
    'Science': '%',
    'Stamina': '',
    'Weapon': '%',
    'Xp': '',
}


STATS_LEFT = [
    'Hp',
    'Attack',
    'Repair',
    'Ability',
    'Stamina'
]


STATS_RIGHT = [
    'Pilot',
    'Science',
    'Engine',
    'Weapon',
    'FireResistance'
]


TRAINING_RANK_ROOM_LOOKUP = {
    1: ('Gym', 'GYM'),
    2: ('Academy', 'ACA')
    # 100: Consumable
}


USER_STATUS = {
    'Attacking': 'Attacking',
    'Defending': 'Defending / Immunity',
    'Offline': 'Offline'
}


USER_TYPE = {
    'Administrator': 'Administrator',
    'Backer': 'Backer',
    'Banned': 'Banned',
    'Mission': 'NPC',
    'Unverified': 'Unverified',
    'UserTypeAlliance': 'Starbase',
    'UserTypeCommunityManager': 'Community Manager',
    'UserTypeJailBroken': 'Jailbroken / Rooted',
    'UserTypePaying': 'Subscribed',
    'Verified': 'Verified'
}


XP_COSTS_LEGENDARY_LOOKUP = [
    0, 0, 810, 1350, 1890,
    2430, 3060, 3690, 4320, 4950,
    5580, 6360, 7090, 7840, 8610,
    9400, 10210, 11040, 11890, 12760,
    13650, 14560, 15490, 16440, 17410,
    18400, 19410, 20440, 21490, 24660,
    23650, 24760, 25890, 27040, 28210,
    29400, 30610, 31840, 33090, 34360]


XP_COSTS_LOOKUP = [
    0, 90, 270, 450, 630,
    810, 1020, 1230, 1440, 1650,
    1860, 2130, 2400, 2670, 2940,
    3210, 3540, 3870, 4200, 4530,
    4860, 5220, 5580, 5940, 6300,
    6660, 7050, 7440, 7830, 8220,
    8610, 9030, 9450, 9870, 10290,
    10710, 11160, 11610, 12060, 12510]










# ----------

def get_lookup_value_or_default(lookup: object, key: object, default: object = None) -> object:
    if key in lookup.keys():
        result = lookup[key]
    else:
        result = default
    return result