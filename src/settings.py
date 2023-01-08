from datetime import datetime, timezone
import json
import os
from typing import List


# ---------- Settings ----------

ACCESS_TOKEN: str = os.environ.get('PSS_ACCESS_TOKEN')


BASE_API_URL: str = 'https://api.pixelstarships.com/'
BASE_INVITE_URL: str = 'https://discordapp.com/oauth2/authorize?scope=applications.commands%20bot&permissions=388160&client_id='


DATABASE_SSL_MODE: str = os.environ.get('DATABASE_SSL_MODE', 'require')
DATABASE_URL: str = f'{os.environ.get("DATABASE_URL")}?sslmode={DATABASE_SSL_MODE}'

DEBUG_GUILDS: List[int] = json.loads(str(os.environ.get('DEBUG_GUILDS', '[]')))
DEFAULT_HYPHEN: str = '–'
DEFAULT_PREFIX: str = '/'
DEFAULT_USE_EMOJI_PAGINATOR: bool = True

DEVICE_LOGIN_CHECKSUM_KEY: str = os.environ.get('PSS_DEVICE_LOGIN_CHECKSUM_KEY')


EXCEL_COLUMN_FORMAT_DATETIME: str = 'YYYY-MM-DD hh:MM:ss'
EXCEL_COLUMN_FORMAT_NUMBER: str = '0'
EXCEL_COLUMN_FORMAT_TEXT: str = '@'


FEATURE_AUTODAILY_ENABLED: int = int(os.environ.get('FEATURE_AUTODAILY_ENABLED', 0))
FEATURE_AUTOTRADER_ENABLED: int = int(os.environ.get('FEATURE_AUTOTRADER_ENABLED', 0))
FEATURE_TOURNEYDATA_ENABLED: int = int(os.environ.get('FEATURE_TOURNEYDATA_ENABLED', 0))

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

INTENT_MESSAGE_CONTENT: bool = int(os.environ.get('INTENT_MESSAGE_CONTENT', '0'))


LATEST_SETTINGS_BASE_PATH: str = 'SettingService/GetLatestVersion3?deviceType=DeviceTypeAndroid&languageKey='


MIN_ENTITY_NAME_LENGTH: int = 3
MOST_RECENT_TOURNAMENT_DATA: bool = bool(int(os.environ.get('MOST_RECENT_TOURNAMENT_DATA', 0)))


OFFER_PREFIXED_COMMANDS: int = int(os.environ.get('OFFER_PREFIXED_COMMANDS', '1'))
OFFER_SLASH_COMMANDS: int = int(os.environ.get('OFFER_SLASH_COMMANDS', '1'))


POST_AUTODAILY_FROM: datetime = datetime(2022, 1, 12, tzinfo=timezone.utc)
PRINT_DEBUG: int = int(os.environ.get('PRINT_DEBUG', '0'))
PRINT_DEBUG_DB: int = int(os.environ.get('PRINT_DEBUG_DB', '0'))
PRINT_DEBUG_COMMAND: int = int(os.environ.get('PRINT_DEBUG_COMMAND', '0'))
PRINT_DEBUG_WEB_REQUESTS: int = int(os.environ.get('PRINT_DEBUG_WEB_REQUESTS', '0'))
PRODUCTION_SERVER: str = os.environ.get('PSS_PRODUCTION_SERVER')

PSS_ABOUT_FILES: List[str] = ['src/pss_data/about.json', 'pss_data/about.json']
PSS_LINKS_FILES: List[str] = ['src/pss_data/links.json', 'pss_data/links.json']
PSS_RESOURCES_FILES: List[str] = ['src/pss_data/resources.json', 'pss_data/resources.json']


RAW_COMMAND_USERS_RAW: str = os.environ.get('RAW_COMMAND_USERS', '[]')
RAW_COMMAND_USERS: List[str] = json.loads(str(RAW_COMMAND_USERS_RAW))


SETTINGS_TABLE_NAME: str = 'settings'
SETTINGS_TYPES: List[str] = ['boolean', 'float', 'int', 'text', 'timestamputc']

SPRITE_CACHE_SUB_PATH: str = 'sprite_cache'


THROW_COMMAND_ERRORS: int = int(os.environ.get('THROW_COMMAND_ERRORS', '0'))

TOURNAMENT_DATA_START_DATE: datetime = datetime(year=2019, month=10, day=9, hour=12)


USE_EMBEDS: bool = True
USE_ACCESS_TOKEN: int = int(os.environ.get('USE_ACCESS_TOKEN', 0))


VERSION: str = '1.4.0.0-b7'


WIKI_COMMAND_GUILDS: List[str] = json.loads(os.environ.get('WIKI_COMMAND_GUILDS', '[]'))
WIKI_COMMAND_USERS: List[str] = json.loads(os.environ.get('WIKI_COMMAND_USERS', '[]'))