from json import load as _json_load
import os
from typing import Dict

import utils


PWD = os.getcwd()
if '/src' in PWD:
    PWD = f'{PWD}/pss_data/'
else:
    PWD = f'{PWD}/src/pss_data/'

ID_NAMES_FILEPATH = f'{PWD}id_names.json'

ID_NAMES_INFO: Dict[str, str]

with open(ID_NAMES_FILEPATH) as fp:
    ID_NAMES_INFO = _json_load(fp)