import os


DATABASE_URL = os.environ['DATABASE_URL']

DEFAULT_FLOAT_PRECISION = 1

EMPTY_LINE = '\u200b'

GPAT = os.environ['GPAT']

MAXIMUM_CHARACTERS = 1900
MIN_ENTITY_NAME_LENGTH = 3

PSS_ABOUT_FILES = ['src/data/about.txt', 'data/about.txt']
PSS_LINKS_FILES = ['src/data/links.json', 'data/links.json']

SETTINGS_TABLE_NAME = 'settings'
SETTINGS_TYPES = ['boolean','float','int','text','timestamputc']

USE_EMBEDS = False

WIKIA_BASE_ADDRESS = 'https://pixelstarships.fandom.com/wiki/'