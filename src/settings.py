from datetime import datetime, timezone
import json
import os
from typing import List


# ---------- Settings ----------

BASE_INVITE_URL: str = 'https://discordapp.com/oauth2/authorize?scope=bot&permissions=388160&client_id='


DATABASE_URL: str = str(os.environ.get('DATABASE_URL'))

DEFAULT_HYPHEN: str = '–'
DEFAULT_PREFIX: str = '/'
DEFAULT_PRODUCTION_SERVER: str = 'api.pixelstarships.com'
DEFAULT_USE_EMOJI_PAGINATOR: bool = True


EXCEL_COLUMN_FORMAT_DATETIME: str = 'YYYY-MM-DD hh:MM:ss'
EXCEL_COLUMN_FORMAT_NUMBER: str = '0'


FLEETS_COMMAND_USERS_RAW: str = os.environ.get('FLEETS_COMMAND_USERS', '[]')
FLEETS_COMMAND_USERS: List[str] = json.loads(str(FLEETS_COMMAND_USERS_RAW))


GDRIVE_CLIENT_EMAIL: str = str(os.environ.get('GDRIVE_SERVICE_CLIENT_EMAIL'))
GDRIVE_CLIENT_ID: str = str(os.environ.get('GDRIVE_SERVICE_CLIENT_ID'))
GDRIVE_FOLDER_ID: str = '10wOZgAQk_0St2Y_jC3UW497LVpBNxWmP'
GDRIVE_PRIVATE_KEY_ID: str = str(os.environ.get('GDRIVE_SERVICE_PRIVATE_KEY_ID'))
GDRIVE_PRIVATE_KEY: str = str(os.environ.get('GDRIVE_SERVICE_PRIVATE_KEY'))
GDRIVE_PROJECT_ID: str = str(os.environ.get('GDRIVE_SERVICE_PROJECT_ID'))
GDRIVE_SERVICE_ACCOUNT_FILE: str = 'client_secrets.json'
GDRIVE_SETTINGS_FILE: str = 'settings.yaml'
GDRIVE_SCOPES: List[str] = ['https://www.googleapis.com/auth/drive']


IGNORE_SERVER_IDS_FOR_COUNTING: List[int] = [
    110373943822540800,
    264445053596991498,
    446425626988249089,
    450100127256936458
]


LATEST_SETTINGS_BASE_PATH: str = 'SettingService/GetLatestVersion3?deviceType=DeviceTypeAndroid&languageKey='


MIN_ENTITY_NAME_LENGTH: int = 3


POST_AUTODAILY_FROM: datetime = datetime(2020, 2, 7, tzinfo=timezone.utc)
PRINT_DEBUG: int = int(os.environ.get('PRINT_DEBUG', '0'))
PRINT_DEBUG_DB: int = int(os.environ.get('PRINT_DEBUG_DB', '0'))
PRINT_DEBUG_COMMAND: int = int(os.environ.get('PRINT_DEBUG_COMMAND', '0'))
PRINT_DEBUG_WEB_REQUESTS: int = int(os.environ.get('PRINT_DEBUG_WEB_REQUESTS', '0'))

PSS_ABOUT_FILES: List[str] = ['src/pss_data/about.json', 'pss_data/about.json']
PSS_LINKS_FILES: List[str] = ['src/pss_data/links.json', 'pss_data/links.json']
PSS_RESOURCES_FILES: List[str] = ['src/pss_data/resources.json', 'pss_data/resources.json']


RAW_COMMAND_USERS_RAW: str = os.environ.get('RAW_COMMAND_USERS', '[]')
RAW_COMMAND_USERS: List[str] = json.loads(str(RAW_COMMAND_USERS_RAW))


SETTINGS_TABLE_NAME: str = 'settings'
SETTINGS_TYPES: List[str] = ['boolean', 'float', 'int', 'text', 'timestamputc']


THROW_COMMAND_ERRORS: int = int(os.environ.get('THROW_COMMAND_ERRORS', '0'))

TOURNAMENT_DATA_START_DATE: datetime = datetime(year=2019, month=10, day=9, hour=12)


USE_EMBEDS: bool = True


VERSION: str = '1.3.2.6'