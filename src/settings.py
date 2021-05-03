from datetime import datetime, timezone
import json
import yaml
import os
from typing import List

# ----- Class Private Variables -----
YADC_SETTINGS_FILE: str = os.path.normcase('settings/yadc_settings.yaml')
__useEnv: bool = None
__cachedSettings = {}
#print("Use Enviroment Variables: " + str(__useEnv) + "could load file: " + str(not os.path.isfile(YADC_SETTINGS_FILE)) + " returned: " + str(_loadFileAndCache(YADC_SETTINGS_FILE)['USE_OS_VARIABLES']))
# ----- Helper -----
def _loadSetting(tag, fileLoc, default):
    try:
        settings = _loadFileAndCache(fileLoc)
        loaded = str(os.environ.get(tag)) if __useEnv else settings[tag]
        if loaded is None:
            print("Loaded (Default): " + str(default))
            return default
        #print("Loaded <" + str(tag) + ">: " + str(loaded)) #Debug only, dissabled for obvious security ishues
        return loaded
    except:
        locationString = "Enviroment" if __useEnv else fileLoc
        print("Could not load setting: " + tag + " from: " + locationString + " Will attempt to return default")
        return default

def _loadFileAndCache(fileLoc):  # Opens the supplied .yaml or .json file and stores it in memory for future requests
    if fileLoc in __cachedSettings:
        return __cachedSettings[fileLoc]

    print("Loading File: " + fileLoc + " ...", end='')
    if os.path.isfile(fileLoc):
        print("Found!")
        with open(fileLoc) as file:
            if fileLoc.endswith('yaml'):
                __cachedSettings[fileLoc] = yaml.full_load(file)
                print("Caching: " + fileLoc)
            elif fileLoc.endswith('json'):
                __cachedSettings[fileLoc] = json.load(file)
                print("Caching: " + fileLoc)
    return __cachedSettings[fileLoc]

# ----- Init -----
__useEnv: bool = True if not os.path.isfile(YADC_SETTINGS_FILE) else _loadFileAndCache(YADC_SETTINGS_FILE)['USE_OS_VARIABLES']
print("Use Enviroment Variables: " + str(__useEnv))
# ---------- Settings ----------
# ----- Config files -----
GDRIVE_SERVICE_ACCOUNT_FILE: str = os.path.normcase(_loadSetting('GDRIVE_SERVICE_ACCOUNT_FILE', YADC_SETTINGS_FILE, 'creds/service_account_creds.json'))
GDRIVE_SETTINGS_FILE: str = os.path.normcase(_loadSetting('GDRIVE_SETTINGS_FILE', YADC_SETTINGS_FILE, 'settings.yaml'))
__gdriveService = GDRIVE_SERVICE_ACCOUNT_FILE
__gdriveSettings = GDRIVE_SETTINGS_FILE
__yadcSettings = YADC_SETTINGS_FILE

# ----- Database Settings -----
DATABASE_SSL_MODE: str = _loadSetting('DATABASE_SSL_MODE', __yadcSettings, "require")
DATABASE_URL: str = _loadSetting('DATABASE_URL', __yadcSettings,"") + '?sslmode=' + DATABASE_SSL_MODE
SETTINGS_TABLE_NAME: str = _loadSetting('SETTINGS_TABLE_NAME', __yadcSettings,'settings')
SETTINGS_TYPES: List[str] = ['boolean', 'float', 'int', 'text', 'timestamputc']

DEFAULT_HYPHEN: str = _loadSetting('DEFAULT_HYPHEN', __yadcSettings,'–')
DEFAULT_PREFIX: str = _loadSetting('DEFAULT_PREFIX', __yadcSettings,'/')


# ----- PSS Settings -----
DEFAULT_PRODUCTION_SERVER: str = _loadSetting('DEFAULT_PRODUCTION_SERVER', __yadcSettings, 'api.pixelstarships.com')
MIN_ENTITY_NAME_LENGTH: int = _loadSetting('MIN_ENTITY_NAME_LENGTH', __yadcSettings, 3)
LATEST_SETTINGS_BASE_PATH: str = _loadSetting('LATEST_SETTINGS_BASE_PATH', __yadcSettings, 'SettingService/GetLatestVersion3?deviceType=DeviceTypeAndroid&languageKey=')

# ----- Excel Settings -----
EXCEL_COLUMN_FORMAT_DATETIME: str = _loadSetting('EXCEL_COLUMN_FORMAT_DATETIME', __yadcSettings, 'YYYY-MM-DD hh:MM:ss')
EXCEL_COLUMN_FORMAT_NUMBER: str = _loadSetting('EXCEL_COLUMN_FORMAT_NUMBER', __yadcSettings,'0')


# ----- gdrive Settings -----
GDRIVE_CLIENT_SECRETS_FILE: str = os.path.normcase(_loadSetting('GDRIVE_CLIENT_SECRETS_FILE', __yadcSettings,'client_secrets.json'))

GDRIVE_CLIENT_EMAIL: str = _loadSetting('client_email', __gdriveService,'')
GDRIVE_CLIENT_ID: str = _loadSetting('client_id', __gdriveService,'')
GDRIVE_FOLDER_ID: str = _loadSetting('GDRIVE_FOLDER_ID', __yadcSettings,'')
GDRIVE_PRIVATE_KEY_ID: str = _loadSetting('private_key_id', __gdriveService,'')
GDRIVE_PRIVATE_KEY: str = _loadSetting('private_key', __gdriveService,'')
GDRIVE_PROJECT_ID: str = _loadSetting('project_id', __gdriveService,'')
GDRIVE_SCOPES: List[str] = (_loadSetting('GDRIVE_SCOPES', __yadcSettings, ['https://www.googleapis.com/auth/drive']))


# ----- Discord Settings -----
DISCORD_BOT_TOKEN= _loadSetting('DISCORD_BOT_TOKEN', __yadcSettings, "")
BASE_INVITE_URL: str = _loadSetting('BASE_INVITE_URL', __yadcSettings, 'https://discordapp.com/oauth2/authorize?scope=bot&permissions=388160&client_id=')
USE_EMBEDS: bool = _loadSetting('USE_EMBEDS', __yadcSettings, True)
DEFAULT_USE_EMOJI_PAGINATOR: bool = _loadSetting('DEFAULT_USE_EMOJI_PAGINATOR', __yadcSettings, True)
FEATURE_AUTODAILY_ENABLED: int = _loadSetting('FEATURE_AUTODAILY_ENABLED', __yadcSettings, 0)
POST_AUTODAILY_FROM: datetime = datetime.strptime(_loadSetting('POST_AUTODAILY_FROM', __yadcSettings, datetime(year=2019, month=10, day=9, hour=12)), '%d/%m/%y %H:%M:%S %Z')
TOURNAMENT_DATA_START_DATE: datetime = datetime.strptime(_loadSetting('TOURNAMENT_DATA_START_DATE', __yadcSettings, datetime(year=2019, month=10, day=9, hour=12)), '%d/%m/%y %H:%M:%S %Z')
FLEETS_COMMAND_USERS_RAW: str = _loadSetting('FLEETS_COMMAND_USERS_RAW', __yadcSettings, [])
FLEETS_COMMAND_USERS: List[str] = json.loads(str(FLEETS_COMMAND_USERS_RAW))
RAW_COMMAND_USERS_RAW: str = _loadSetting('RAW_COMMAND_USERS_RAW', __yadcSettings, [])
RAW_COMMAND_USERS: List[str] = json.loads(str(RAW_COMMAND_USERS_RAW))
__IGNORE_SERVER_IDS_FOR_COUNTING_DEFAULT: List[int] = [
    110373943822540800,
    264445053596991498,
    446425626988249089,
    450100127256936458
]
IGNORE_SERVER_IDS_FOR_COUNTING: List[int] = _loadSetting('USE_EMBEDS', __yadcSettings, __IGNORE_SERVER_IDS_FOR_COUNTING_DEFAULT)


# ----- File Settings -----
PSS_ABOUT_FILES: List[str] = _loadSetting('PSS_ABOUT_FILES', __yadcSettings, ['src/pss_data/about.json', 'pss_data/about.json'])
PSS_LINKS_FILES: List[str] = _loadSetting('PSS_LINKS_FILES', __yadcSettings, ['src/pss_data/links.json', 'pss_data/links.json'])
PSS_RESOURCES_FILES: List[str] = _loadSetting('PSS_RESOURCES_FILES', __yadcSettings, ['src/pss_data/resources.json', 'pss_data/resources.json'])
SPRITE_CACHE_SUB_PATH: str = _loadSetting('SPRITE_CACHE_SUB_PATH', __yadcSettings, 'sprite_cache')

# ----- Debug Settings -----
PRINT_DEBUG: int = int(_loadSetting('PRINT_DEBUG', __yadcSettings, '0'))
PRINT_DEBUG_DB: int = int(_loadSetting('PRINT_DEBUG_DB', __yadcSettings, '0'))
PRINT_DEBUG_COMMAND: int = int(_loadSetting('PRINT_DEBUG_COMMAND', __yadcSettings, '0'))
PRINT_DEBUG_WEB_REQUESTS: int = int(_loadSetting('PRINT_DEBUG_WEB_REQUESTS', __yadcSettings, '0'))
THROW_COMMAND_ERRORS: int = int(_loadSetting('THROW_COMMAND_ERRORS', __yadcSettings, '0'))

# ----- Ref -----
VERSION: str = '1.3.4.1'
