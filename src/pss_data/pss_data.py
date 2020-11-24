#!/usr/local/bin/python3

import os
from typing import Dict, List, Tuple

import utility


PWD = os.getcwd()
if '/src' in PWD:
    PWD = f'{PWD}/pss_data/'
else:
    PWD = f'{PWD}/src/pss_data/'

ID_NAMES_FILEPATH = f'{PWD}id_names.json'

ID_NAMES_INFO = Dict[str, str]

# Load id_names information
ID_NAMES_INFO = utility.load_json_from_file(ID_NAMES_FILEPATH)