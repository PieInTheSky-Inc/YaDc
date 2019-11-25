import os


DATABASE_URL = os.environ['DATABASE_URL']

DEFAULT_FLOAT_PRECISION = 1
DEFAULT_USE_EMOJI_PAGINATOR = True

EMPTY_LINE = '\u200b'

EXCEL_COLUMN_FORMAT_DATETIME = 'YYYY-MM-DD hh:MM:ss'
EXCEL_COLUMN_FORMAT_NUMBER = '0'

GPAT = os.environ['GPAT']

MAXIMUM_CHARACTERS = 1900
MIN_ENTITY_NAME_LENGTH = 3

PREFIX_DEFAULT = '/'
PSS_ABOUT_FILES = ['src/data/about.txt', 'data/about.txt']
PSS_LINKS_FILES = ['src/data/links.json', 'data/links.json']

SETTINGS_TABLE_NAME = 'settings'
SETTINGS_TYPES = ['boolean','float','int','text','timestamputc']

USE_EMBEDS = False

VERSION = '1.2.2.3'

WIKIA_BASE_ADDRESS = 'https://pixelstarships.fandom.com/wiki/'