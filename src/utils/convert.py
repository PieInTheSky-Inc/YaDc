from typing import Any as _Any, Dict, List, Union
from urllib.parse import quote as _quote
from xml.etree import ElementTree as _ElementTree

from . import format as _format
from . import parse as _parse

from .. import pss_data as _pss_data
from .. import pss_lookups as _lookups
from ..typehints import EntitiesData


# ---------- Typehint definitions ----------

_EntityDict = Union[List['_EntityDict'], Dict[str, '_EntityDict']]





# ---------- Functions ----------


def hundredth_to_seconds(hundredth: int) -> float:
    if hundredth:
        hundredth = float(hundredth)
        return hundredth / 100.0
    else:
        return 0.0


def iap_options_mask(iap_options_mask: int) -> str:
    result = []
    for flag in _lookups.IAP_OPTIONS_MASK_LOOKUP.keys():
        if (iap_options_mask & flag) != 0:
            item, value = _lookups.IAP_OPTIONS_MASK_LOOKUP[flag]
            result.append(f'_{item}_ ({value})')
    if result:
        if len(result) > 1:
            return f'{", ".join(result[:-1])} or {result[-1]}'
        else:
            return result[0]
    else:
        return ''


def pss_timestamp_to_excel(pss_timestamp: str) -> str:
    if pss_timestamp:
        dt = _parse.pss_datetime(pss_timestamp)
        result = _format.datetime_for_excel(dt)
        return result
    else:
        return ''


def raw_xml_to_dict(raw_xml: str, include_root: bool = True, fix_attributes: bool = True, preserve_lists: bool = False) -> _EntityDict:
    root = _ElementTree.fromstring(raw_xml)
    result = __convert_xml_to_dict(root, include_root=include_root, fix_attributes=fix_attributes, preserve_lists=preserve_lists)
    return result


def ticks_to_seconds(ticks: int) -> float:
    if ticks:
        ticks = float(ticks)
        return ticks / 40.0
    else:
        return 0.0


def to_boolean(value: _Any, default_if_none: bool = False) -> bool:
    if value is None:
        return default_if_none
    if isinstance(value, str):
        try:
            value = bool(value)
        except:
            try:
                value = float(value)
            except:
                try:
                    value = int(value)
                except:
                    return len(value) > 0
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value > 0
    if isinstance(value, float):
        return value > 0.0
    if isinstance(value, (tuple, list, dict, set)):
        return len(value) > 0
    raise NotImplementedError


def url_escape(s: str) -> str:
    if s:
        s = _quote(s, safe=' ')
        s = s.replace(' ', '+')
    return s


def xmltree_to_dict2(raw_text: str) -> EntitiesData:
    return __xmltree_to_dict(raw_text, 2)


def xmltree_to_dict3(raw_text: str) -> EntitiesData:
    return __xmltree_to_dict(raw_text, 3)





# ---------- Helper functions ----------

def __convert_xml_to_dict(root: _ElementTree.Element, include_root: bool = True, fix_attributes: bool = True, preserve_lists: bool = False) -> _EntityDict:
    if root is None:
        return None

    result = {}
    if root.attrib:
        if include_root:
            if fix_attributes:
                result[root.tag] = __fix_attribute(root.attrib)
            else:
                result[root.tag] = root.attrib
        else:
            if fix_attributes:
                result = __fix_attribute(root.attrib)
            else:
                result = root.attrib
    elif include_root:
        result[root.tag] = {}

    # Retrieve all distinct names of sub tags
    tag_count_map = __get_child_tag_count(root)
    children_dict = {}

    for child in root:
        tag = child.tag
        key = None
        if tag_count_map[tag] >= 1:
            id_attr_names = _pss_data.ID_NAMES_INFO.get(tag)
            if id_attr_names:
                id_attr_values = [child.attrib[id_attr_name] for id_attr_name in id_attr_names]
                key = '.'.join(sorted(id_attr_values))
        if not key:
            key = tag

        child_dict = __convert_xml_to_dict(child, include_root=False, fix_attributes=fix_attributes, preserve_lists=preserve_lists)
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


def __fix_attribute(attribute: Dict[str, str]) -> Dict[str, str]:
    if not attribute:
        return None

    result = {}

    for key, value in attribute.items():
        if key.endswith('Xml') and value:
            raw_xml = value
            fixed_value = raw_xml_to_dict(raw_xml)
            result[key[:-3]] = fixed_value

        result[key] = value

    return result


def __get_child_tag_count(root: _ElementTree.Element) -> Dict[str, int]:
    if root is None:
        return None

    child_tags = list(set([child_node.tag for child_node in root]))
    result = {}
    for child_tag in child_tags:
        result[child_tag] = sum(1 for child_node in root if child_node.tag == child_tag)

    return result


def __xmltree_to_dict(raw_text: str, depth: int) -> EntitiesData:
    result = raw_xml_to_dict(raw_text)
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