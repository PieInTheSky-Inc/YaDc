import datetime
import os





API_DATETIME_FORMAT_ISO = '%Y-%m-%dT%H:%M:%S'
API_DATETIME_FORMAT_ISO_DETAILED = '%Y-%m-%dT%H:%M:%S.%f'
API_DATETIME_FORMAT_CUSTOM = '%d.%m.%y %H:%M'


BASE_INVITE_URL = 'https://discordapp.com/oauth2/authorize?scope=bot&permissions=388160&client_id='


DATABASE_URL = str(os.environ.get('DATABASE_URL'))

DEFAULT_PRODUCTION_SERVER = 'api.pixelstarships.com'
DEFAULT_FLOAT_PRECISION = 1
DEFAULT_MODE_REPOST_AUTODAILY = True
DEFAULT_USE_EMOJI_PAGINATOR = True


EMPTY_LINE = '\u200b'


EXCEL_COLUMN_FORMAT_DATETIME = 'YYYY-MM-DD hh:MM:ss'
EXCEL_COLUMN_FORMAT_NUMBER = '0'


GDRIVE_CLIENT_EMAIL = str(os.environ.get('GDRIVE_SERVICE_CLIENT_EMAIL'))
GDRIVE_CLIENT_ID = str(os.environ.get('GDRIVE_SERVICE_CLIENT_ID'))
GDRIVE_FOLDER_ID = '10wOZgAQk_0St2Y_jC3UW497LVpBNxWmP'
GDRIVE_PRIVATE_KEY_ID = str(os.environ.get('GDRIVE_SERVICE_PRIVATE_KEY_ID'))
GDRIVE_PRIVATE_KEY = str(os.environ.get('GDRIVE_SERVICE_PRIVATE_KEY'))
GDRIVE_PROJECT_ID = str(os.environ.get('GDRIVE_SERVICE_PROJECT_ID'))
GDRIVE_SERVICE_ACCOUNT_FILE = 'client_secrets.json'
GDRIVE_SETTINGS_FILE = 'settings.yaml'
GDRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']

LATEST_SETTINGS_BASE_PATH = 'SettingService/GetLatestVersion3?deviceType=DeviceTypeAndroid&languageKey='

MAXIMUM_CHARACTERS = 1900
MIN_ENTITY_NAME_LENGTH = 3

ONE_SECOND: datetime.timedelta = datetime.timedelta(seconds=1)

POST_AUTODAILY_FROM: datetime.datetime = datetime.datetime(2020, 2, 7, tzinfo=datetime.timezone.utc)
PREFIX_DEFAULT = '/'
PRINT_DEBUG = False

PSS_ABOUT_FILES = ['src/data/about.json', 'data/about.json']
PSS_LINKS_FILES = ['src/data/links.json', 'data/links.json']
PSS_RESOURCES_FILES = ['src/data/resources.json', 'data/resources.json']

PSS_START_DATE = datetime.date(year=2016, month=1, day=6)


SETTINGS_TABLE_NAME = 'settings'
SETTINGS_TYPES = ['boolean','float','int','text','timestamputc']


USE_EMBEDS = False

VERSION = '1.2.8.4'


WIKIA_BASE_ADDRESS = 'https://pixelstarships.fandom.com/wiki/'












