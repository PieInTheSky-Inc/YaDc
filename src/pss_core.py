from datetime import datetime
import json
import re
from typing import Any, Callable, Dict, List, Optional

import aiohttp

import pss_entity as entity
import settings
from typehints import EntitiesData, EntityInfo
import utils


# ---------- Constants ----------

__RX_PROPERTY_FIX_REPLACE: re.Pattern = re.compile(r'[^a-z0-9]', re.IGNORECASE)
__RX_ALLOWED_CANDIDATE_FIX_REPLACE: re.Pattern = re.compile(r'(\(.*?\)|[^a-z0-9 ])', re.IGNORECASE)





# ---------- Functions ----------

def filter_entities_data(data: EntitiesData, by: Dict[str, str], ignore_case: bool = False) -> Optional[EntitiesData]:
    """Parameter 'data':
       - A dict with entity ids as keys and entity info as values.
       Parameter 'by':
       - Keys are names of entity fields to filter by.
       - Values are values that each respective field should have. """
    result = data
    if by:
        for key, value in by.items():
            result = __filter_data_dict(result, key, value, ignore_case)
    return result


def fix_allowed_value_candidate(candidate: str) -> str:
    result = candidate.strip()
    result = __RX_ALLOWED_CANDIDATE_FIX_REPLACE.sub('', result)
    return result


async def get_base_url() -> str:
    production_server = await __get_production_server()
    result = f'https://{production_server}/'
    return result


async def get_data_from_path(path: str) -> str:
    if path:
        path = path.strip('/')
    base_url = await get_base_url()
    url = f'{base_url}{path}'
    return await __get_data_from_url(url)


async def get_latest_settings(language_key: str = 'en', base_url: str = None) -> EntityInfo:
    if not language_key:
        language_key = 'en'
    base_url = base_url or await get_base_url()
    url = f'{base_url}{settings.LATEST_SETTINGS_BASE_PATH}{language_key}'
    raw_text = await __get_data_from_url(url)
    result = utils.convert.xmltree_to_dict3(raw_text)
    return result


def get_ids_from_property_value(data: EntitiesData, property_name: str, property_value: str, fix_data_delegate: Callable[[str], str] = None, match_exact: bool = False) -> List[str]:
    # data structure: {id: content}
    # fixed_data structure: {description: id}
    if not data or not property_name or not property_value:
        print(f'- get_ids_from_property_value: invalid data or property info. Return empty list.')
        return []

    if not fix_data_delegate:
        fix_data_delegate = __fix_property_value

    fixed_value = fix_data_delegate(property_value)
    fixed_data = {entry_id: fix_data_delegate(entry_data[property_name]) for entry_id, entry_data in data.items() if entry_data[property_name]}

    if match_exact:
        results = [key for key, value in fixed_data.items() if value == fixed_value]
    else:
        similarity_map = {}
        for entry_id, entry_property in fixed_data.items():
            if entry_property.startswith(fixed_value) or fixed_value in entry_property:
                similarity_value = utils.get_similarity(entry_property, fixed_value)
                if similarity_value in similarity_map.keys():
                    similarity_map[similarity_value].append((entry_id, entry_property))
                else:
                    similarity_map[similarity_value] = [(entry_id, entry_property)]
        for similarity_value, entries in similarity_map.items():
            similarity_map[similarity_value] = sorted(entries, key=lambda entry: entry[1])
        similarity_values = sorted(list(similarity_map.keys()), reverse=True)
        results = []
        for similarity_value in similarity_values:
            if not match_exact or (match_exact is True and similarity_value.is_integer()):
                entry_ids = [entry_id for (entry_id, _) in similarity_map[similarity_value]]
                results.extend(entry_ids)

    return results


def read_about_file(language_key: str = 'en') -> Dict[str, Any]:
    result = {}
    for pss_about_file in settings.PSS_ABOUT_FILES:
        try:
            with open(pss_about_file) as f:
                result = json.load(f)
            break
        except:
            pass
    return result.get(language_key)


def read_links_file(language_key: str = 'en') -> Dict[str, List[List[str]]]:
    links = {}
    for pss_links_file in settings.PSS_LINKS_FILES:
        try:
            with open(pss_links_file) as f:
                links = json.load(f)
            break
        except:
            pass
    return links.get(language_key)


def transform_pss_datetime(*args, **kwargs) -> datetime:
    dt = __parse_entity_datetime(*args, **kwargs)
    result = None
    if dt:
        result = f'{utils.format.datetime(dt, include_tz_brackets=False)}'
    return result


def transform_pss_datetime_with_timespan(*args, **kwargs) -> datetime:
    dt = __parse_entity_datetime(*args, **kwargs)
    include_seconds_in_timespan = kwargs.get('include_seconds_in_timespan', True)
    omit_time_if_zero = kwargs.get('omit_time_if_zero', False)
    utc_now = kwargs.get('utc_now')
    result = None
    if dt and utc_now:
        time_is_zero = dt.hour == 0 and dt.minute == 0 and dt.second == 0
        include_time = not (omit_time_if_zero and time_is_zero)
        td = dt - utc_now
        result = f'{utils.format.datetime(dt, include_time=include_time, include_tz_brackets=False)} ({utils.format.timedelta(td, include_seconds=include_seconds_in_timespan)})'
    return result


def transform_get_value(*args, **kwargs) -> Optional[str]:
    entity_property = kwargs.get('entity_property')
    if entity.entity_property_has_value(entity_property):
        return entity_property
    else:
        return None


def transform_sanitize_text(*args, **kwargs) -> Optional[str]:
    entity_property = kwargs.get('entity_property')
    if entity_property:
        result = utils.escape_escape_sequences(entity_property)
        while '\n\n' in result:
            result = result.replace('\n\n', '\n')
        return result
    else:
        return None


def __filter_data_dict(data: EntitiesData, by_key: Any, by_value: Any, ignore_case: bool) -> Optional[EntitiesData]:
    """Parameter 'data':
       - A dict with entity ids as keys and entity info as values. """
    if data:
        result = {}
        for key, entry in data.items():
            entry_value = entry[by_key]
            value = by_value
            if ignore_case:
                entry_value = str(entry_value).lower()
                value = str(value).lower()
            if isinstance(by_value, list):
                if entry_value in value:
                    result[key] = entry
            elif entry_value == value:
                    result[key] = entry
        return result
    else:
        return data


def __fix_property_value(property_value: str) -> str:
    result = property_value.lower()
    result = result.strip()
    result = __RX_PROPERTY_FIX_REPLACE.sub('', result)
    return result


async def __get_data_from_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.text(encoding='utf-8')
    return data


async def __get_production_server(language_key: str = 'en') -> str:
    if settings.PRODUCTION_SERVER:
        return settings.PRODUCTION_SERVER
    latest_settings = await get_latest_settings(language_key=language_key, base_url=settings.BASE_API_URL)
    return latest_settings['ProductionServer']


def __parse_entity_datetime(*args, **kwargs) -> Optional[datetime]:
    result = None
    entity_property = kwargs.get('entity_property')
    if entity_property:
        result = utils.parse.pss_datetime(entity_property)
    return result