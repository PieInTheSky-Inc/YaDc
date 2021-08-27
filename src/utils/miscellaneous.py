import aiohttp as _aiohttp
from jellyfish import jaro_winkler as _jaro_winkler
import subprocess as _subprocess
from threading import get_ident as _get_ident
from typing import Any as _Any, Optional
from typing import Dict as _Dict
from typing import Iterable as _Iterable
from typing import List as _List
from typing import Tuple as _Tuple

import settings as _settings

from . import constants as _constants
from . import datetime as _datetime


# ---------- Functions ----------

async def check_hyperlink(hyperlink: str) -> bool:
    if hyperlink:
        session: _aiohttp.ClientSession
        async with _aiohttp.ClientSession() as session:
            response: _aiohttp.ClientResponse
            async with session.get(hyperlink) as response:
                return response.status == 200
    else:
        return False


def chunk_list(lst: _List[_Any], chunk_size: int) -> _List[_List[_Any]]:
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i+chunk_size]


def compare_versions(version_1: str, version_2: str) -> int:
    """Compares two version strings with format x.x.x.x

    Returns:
    -1, if version_1 is higher than version_2
    0, if version_1 is equal to version_2
    1, if version_1 is lower than version_2 """
    if not version_1:
        return 1
    version_1 = version_1.strip('v')
    version_2 = version_2.strip('v')
    version_1_split = version_1.split('.')
    version_2_split = version_2.split('.')
    for i in range(0, len(version_1_split)):
        if version_1_split[i] < version_2_split[i]:
            return 1
        elif version_1_split[i] > version_2_split[i]:
            return -1
    return 0


def dbg_prnt(text: str) -> None:
    if _settings.PRINT_DEBUG:
        print(f'[{_datetime.get_utc_now()}][{_get_ident()}]: {text}')


def dicts_equal(d1: _Dict[_Any, _Any], d2: _Dict[_Any, _Any]) -> bool:
    """
    Checks, whether the contents of two dicts are equal
    """
    if d1 and d2:
        return d1 == d2
    elif not d1 and not d2:
        return True
    else:
        return False


def escape_escape_sequences(txt: str) -> Optional[str]:
    if txt:
        txt = txt.replace('\\n', '\n')
        txt = txt.replace('\\r', '\r')
        txt = txt.replace('\\t', '\t')

    return txt


def get_changed_value_keys(d1: _Dict[_Any, _Any], d2: _Dict[_Any, _Any], keys_to_check: list = None) -> _List[_Any]:
    if not keys_to_check:
        keys_to_check = list(d1.keys())
    result = []
    for key in keys_to_check:
        if key in d1:
            if key in d2:
                if d1[key] != d2[key]:
                    result.append(key)
    return result


def get_level_and_name(level: str, name: str) -> _Tuple[int, str]:
    if level is None and name is None:
        return level, name

    if level is not None and name is None:
        return None, level

    try:
        level = int(level)
    except:
        if level is not None:
            if name is None:
                name = level
            else:
                name = f'{level} {name}'
        level = None
    return level, name


def get_similarity(value_to_check: str, against: str) -> float:
    result = _jaro_winkler(value_to_check, against)
    if value_to_check.startswith(against):
        result += 1.0
    return result


def get_similarity_map(values_to_check: _Iterable[str], against: str) -> _Dict[float, _List[str]]:
    result = {}
    for value in values_to_check:
        similarity = get_similarity(value, against)
        result.setdefault(similarity, []).append(value)
    return result


async def get_wikia_link(page_name: str) -> str:
    page_name = '_'.join([part for part in page_name.split(' ')])
    page_name = '_'.join([part.lower().capitalize() for part in page_name.split('_')])
    result = f'{_constants.WIKIA_BASE_ADDRESS}{page_name}'

    if not (await check_hyperlink(result)):
        page_name_split = page_name.split('_')
        if len(page_name_split) > 1:
            page_name = f'{page_name_split[0].upper()}_{"_".join(page_name_split[1:])}'
        else:
            page_name = page_name.upper()
    result = f'{_constants.WIKIA_BASE_ADDRESS}{page_name}'

    if not (await check_hyperlink(result)):
        result = ''

    return result


def is_str_in_list(value: str, lst: _List[str], case_sensitive: bool = False) -> bool:
    if value and lst:
        if not case_sensitive:
            value = value.lower()
            lst = [item.lower() for item in lst]
        return value in lst
    return False


def make_dict_value_lists_unique(d: _Dict[str, _Iterable[object]]) -> _Dict[str, _List[object]]:
    for key in d.keys():
        d[key] = list(set(d[key]))
    return d


def shell_cmd(cmd: str) -> str:
    result = _subprocess.run(cmd.split(), stdout=_subprocess.PIPE)
    return result.stdout.decode('utf-8')