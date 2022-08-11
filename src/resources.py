import json
from typing import Any, Dict, List

from . import settings


# ---------- Constants ----------

RESOURCES: Dict[str, Dict[str, str]] = {}





# ---------- Functions ----------

def get_resource(resource_key: str, formats: List[Any] = None, language_key: str = 'en') -> str:
    if language_key not in RESOURCES.keys():
        raise ValueError(f'The requested language key is not supported: {language_key}')
    resources = RESOURCES[language_key]
    if resource_key not in resources.keys():
        raise ValueError(f'The requested resource could not be found for the language key \'{language_key}\': {resource_key}')
    result = resources[resource_key]
    if formats is not None:
        result = result.format(*formats)
    return result





# ---------- Helper functions ----------

def __read_resources_file() -> Dict[str, Dict[str, str]]:
    result = {}
    for pss_about_file in settings.PSS_RESOURCES_FILES:
        try:
            with open(pss_about_file) as f:
                result = json.load(f)
            break
        except:
            pass
    return result





# ---------- Initialization ----------

RESOURCES = __read_resources_file()