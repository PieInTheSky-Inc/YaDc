import json

import settings





# ---------- Constants ----------

RESOURCES = {}





# ---------- Functions ----------

def read_resources_file() -> dict:
    result = {}
    for pss_about_file in settings.PSS_RESOURCES_FILES:
        try:
            with open(pss_about_file) as f:
                result = json.load(f)
            break
        except:
            pass
    return result


def get_resource(resource_key: str, language_key: str = 'en') -> str:
    if language_key not in RESOURCES.keys():
        raise ValueError(f'The requested language key is not supported: {language_key}')
    resources = RESOURCES[language_key]
    if resource_key not in resources.keys():
        raise ValueError(f'The requested resource could not be found for the language key \'{language_key}\': {resource_key}')
    return resources[resource_key]





# ---------- Initialization ----------

RESOURCES = read_resources_file()