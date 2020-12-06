import json
import re
from typing import Any, Callable, Dict, List, Union
from xml.etree import ElementTree

import aiohttp

import pss_data
from pss_entity import EntitiesData, EntityInfo
import pss_lookups as lookups
import settings
import utils


# ---------- Typehint definitions ----------

__EntityDict = Union[List['__EntityDict'], Dict[str, '__EntityDict']]





# ---------- Constants ----------

__RX_PROPERTY_FIX_REPLACE: re.Pattern = re.compile(r'[^a-z0-9]', re.IGNORECASE)
__RX_ALLOWED_CANDIDATE_FIX_REPLACE: re.Pattern = re.compile(r'(\(.*?\)|[^a-z0-9 ])', re.IGNORECASE)





# ---------- Public ----------

async def get_data_from_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.text(encoding='utf-8')
    return data


async def get_data_from_path(path: str) -> str:
    if path:
        path = path.strip('/')
    base_url = await get_base_url()
    url = f'{base_url}{path}'
    return await get_data_from_url(url)


def xmltree_to_dict2(raw_text: str) -> EntitiesData:
    return __xmltree_to_dict(raw_text, 2)


def xmltree_to_dict3(raw_text: str) -> EntitiesData:
    return __xmltree_to_dict(raw_text, 3)


def __xmltree_to_dict(raw_text: str, depth: int) -> EntitiesData:
    result = convert_raw_xml_to_dict(raw_text)
    while depth > 0:
        found_new_root = False
        for value in result.values():
            if isinstance(value, dict):
                result = value
                depth -= 1
                found_new_root = True
                break
        if not found_new_root:
            return {}
    return result


def convert_raw_xml_to_dict(raw_xml: str, include_root: bool = True, fix_attributes: bool = True, preserve_lists: bool = False) -> __EntityDict:
    root = ElementTree.fromstring(raw_xml)
    result = _convert_xml_to_dict(root, include_root=include_root, fix_attributes=fix_attributes, preserve_lists=preserve_lists)
    return result


def _convert_xml_to_dict(root: ElementTree.Element, include_root: bool = True, fix_attributes: bool = True, preserve_lists: bool = False) -> __EntityDict:
    if root is None:
        return None

    result = {}
    if root.attrib:
        if include_root:
            if fix_attributes:
                result[root.tag] = _fix_attribute(root.attrib)
            else:
                result[root.tag] = root.attrib
        else:
            if fix_attributes:
                result = _fix_attribute(root.attrib)
            else:
                result = root.attrib
    elif include_root:
        result[root.tag] = {}

    # Retrieve all distinct names of sub tags
    tag_count_map = _get_child_tag_count(root)
    children_dict = {}

    for child in root:
        tag = child.tag
        key = None
        if tag_count_map[tag] > 1:
            id_attr_names = pss_data.ID_NAMES_INFO.get(tag)
            if id_attr_names:
                id_attr_values = [child.attrib[id_attr_name] for id_attr_name in id_attr_names]
                key = '.'.join(sorted(id_attr_values))
        if not key:
            key = tag

        child_dict = _convert_xml_to_dict(child, include_root=False, fix_attributes=fix_attributes, preserve_lists=preserve_lists)
        if key not in children_dict.keys():
            children_dict[key] = child_dict

    if children_dict:
        if preserve_lists:
            if len(children_dict) > 1:
                children_list = list(children_dict.values())
                if include_root:
                    result[root.tag] = children_list
                else:
                    if result:
                        result['Collection'] = children_list
                    else:
                        result = children_list
            else:
                result.setdefault(root.tag, {}).update(children_dict)
        else:
            if include_root:
                # keys get overwritten here
                result[root.tag] = children_dict
            else:
                result.update(children_dict)

    return result


def _get_child_tag_count(root: ElementTree.Element) -> Dict[str, int]:
    if root is None:
        return None

    child_tags = list(set([child_node.tag for child_node in root]))
    result = {}
    for child_tag in child_tags:
        result[child_tag] = sum(1 for child_node in root if child_node.tag == child_tag)

    return result


def _fix_attribute(attribute: Dict[str, str]) -> Dict[str, str]:
    if not attribute:
        return None

    result = {}

    for key, value in attribute.items():
        if key.endswith('Xml') and value:
            raw_xml = value
            fixed_value = convert_raw_xml_to_dict(raw_xml)
            result[key[:-3]] = fixed_value

        result[key] = value

    return result


def _fix_property_value(property_value: str) -> str:
    result = property_value.lower()
    result = result.strip()
    result = __RX_PROPERTY_FIX_REPLACE.sub('', result)
    return result


def fix_allowed_value_candidate(candidate: str) -> str:
    result = candidate.strip()
    result = __RX_ALLOWED_CANDIDATE_FIX_REPLACE.sub('', result)
    return result


def get_ids_from_property_value(data: EntitiesData, property_name: str, property_value: str, fix_data_delegate: Callable[[str], str] = None, match_exact: bool = False) -> List[str]:
    # data structure: {id: content}
    # fixed_data structure: {description: id}
    if not data or not property_name or not property_value:
        print(f'- get_ids_from_property_value: invalid data or property info. Return empty list.')
        return []

    if not fix_data_delegate:
        fix_data_delegate = _fix_property_value

    fixed_value = fix_data_delegate(property_value)
    fixed_data = {entry_id: fix_data_delegate(entry_data[property_name]) for entry_id, entry_data in data.items() if entry_data[property_name]}

    if match_exact:
        results = [key for key, value in fixed_data.items() if value == property_value]
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


def filter_data_list(data: List[EntityInfo], by: Dict[str, str], ignore_case: bool = False) -> List[EntityInfo]:
    """Parameter 'data':
       - A list of entity dicts
       Parameter 'by':
       - Keys are names of entity fields to filter by.
       - Values are values that each respective field should have."""
    result = data
    if by:
        for key, value in by.items():
            result = _filter_data_list(result, key, value, ignore_case)
    return result


def _filter_data_list(data: List[EntityInfo], by_key: Any, by_value: Any, ignore_case: bool) -> List[EntityInfo]:
    """Parameter 'data':
       - A list of entity dicts """
    if data:
        result = []
        for entry in data:
            entry_value = entry[by_key]
            value = by_value
            if ignore_case:
                entry_value = str(entry_value).lower()
                value = str(value).lower()
            if isinstance(by_value, list):
                if entry_value in value:
                    result.append(entry)
            elif entry_value == value:
                    result.append(entry)
        return result
    else:
        return data


def filter_entities_data(data: EntitiesData, by: Dict[str, str], ignore_case: bool = False) -> EntitiesData:
    """Parameter 'data':
       - A dict with entity ids as keys and entity info as values.
       Parameter 'by':
       - Keys are names of entity fields to filter by.
       - Values are values that each respective field should have. """
    result = data
    if by:
        for key, value in by.items():
            result = _filter_data_dict(result, key, value, ignore_case)
    return result


def _filter_data_dict(data: EntitiesData, by_key: Any, by_value: Any, ignore_case: bool) -> EntitiesData:
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


def group_data_list(data: List[EntityInfo], by_key: Any, ignore_case: bool = False) -> Dict[str, List[EntityInfo]]:
    """Parameter 'data':
       - A dict with entity ids as keys and entity info as values. """
    if data:
        result = {}
        for entry in data:
            entry_value = entry[by_key]
            if ignore_case:
                entry_value = str(entry_value).lower()
            if entry_value in result.keys():
                result[entry_value].append(entry)
            else:
                result[entry_value] = [entry]
        return result
    else:
        return data


def group_data_dict(data: EntitiesData, by_key: Any, ignore_case: bool = False) -> Dict[str, EntitiesData]:
    """Parameter 'data':
       - A dict with entity ids as keys and entity info as values. """
    if data:
        result = {}
        for key, entry in data.items():
            entry_value = entry[by_key]
            if ignore_case:
                entry_value = str(entry_value).lower()
            if entry_value in result.keys():
                result[entry_value][key] = entry
            else:
                new_group = {key: entry}
                result[entry_value] = new_group
        return result
    else:
        return data


def convert_iap_options_mask(iap_options_mask: int) -> str:
    result = []
    for flag in lookups.IAP_OPTIONS_MASK_LOOKUP.keys():
        if (iap_options_mask & flag) != 0:
            item, value = lookups.IAP_OPTIONS_MASK_LOOKUP[flag]
            result.append(f'_{item}_ ({value})')
    if result:
        if len(result) > 1:
            return f'{", ".join(result[:-1])} or {result[-1]}'
        else:
            return result[0]
    else:
        return ''










# ---------- Get Production Server ----------

async def get_latest_settings(language_key: str = 'en', use_default: bool = False) -> EntityInfo:
    if not language_key:
        language_key = 'en'
    base_url = await get_base_url(use_default=use_default)
    url = f'{base_url}{settings.LATEST_SETTINGS_BASE_PATH}{language_key}'
    raw_text = await get_data_from_url(url)
    result = xmltree_to_dict3(raw_text)
    return result


async def get_production_server(language_key: str = 'en') -> str:
    latest_settings = await get_latest_settings(language_key=language_key, use_default=True)
    return latest_settings['ProductionServer']


async def get_base_url(use_default: bool = False) -> str:
    if use_default is True:
        production_server = settings.DEFAULT_PRODUCTION_SERVER
    else:
        production_server = await get_production_server()
    result = f'https://{production_server}/'
    return result










# ---------- Links ----------
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
