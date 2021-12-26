from typing import Dict as _Dict
from typing import List as _List

from pss_entity import EntityInfo as _EntityInfo
from pss_entity import EntitiesData as _EntitiesData
import pss_room as _room


def make_rooms_purchase_table(rooms_per_level: _Dict[int, int]) -> str:
    result = ['{|class="wikitable" style="text-align: center; width: 100%; table-layout: fixed;"']
    result.append('!scope="row"|Ship Level')
    max_level = max(rooms_per_level.keys())
    column_width = int(85 / max_level)
    for level in range(1, max_level + 1):
        result.append(f'!scope="col" style="width: {column_width}%;"|{level}')
    result.append('|-')
    result.append('!scope="row"|Number Available')

    prior_quantity = 0
    for level, quantity in rooms_per_level.items():
        line = ['|']
        if quantity != prior_quantity:
            line.append('style="background: #808080; font-weight: bold;|"')
        line.append(str(quantity))
        prior_quantity = quantity
        result.append(''.join(line))
    return result


def make_room_stat_table(room_infos: _List[_EntityInfo]) -> str:
    raise NotImplemented()
    pass