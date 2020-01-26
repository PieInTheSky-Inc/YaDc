import os


DATABASE_URL = str(os.environ.get('DATABASE_URL'))

DEFAULT_FLOAT_PRECISION = 1
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

GPAT = str(os.environ['GPAT'])

MAXIMUM_CHARACTERS = 1900
MIN_ENTITY_NAME_LENGTH = 3

PREFIX_DEFAULT = '/'
PRINT_DEBUG = False
PSS_ABOUT_FILES = ['src/data/about.json', 'data/about.json']
PSS_LINKS_FILES = ['src/data/links.json', 'data/links.json']

SETTINGS_TABLE_NAME = 'settings'
SETTINGS_TYPES = ['boolean','float','int','text','timestamputc']

USE_EMBEDS = False

VERSION = '1.2.5.6'

WIKIA_BASE_ADDRESS = 'https://pixelstarships.fandom.com/wiki/'












