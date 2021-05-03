from json import load as _json_load
import os
from typing import Dict

import utils


PWD = os.getcwd()
if (os.path.sep + 'src') in PWD:
    PWD = os.path.join(os.getcwd(), "pss_data")
else:
    PWD = os.path.join(os.getcwd(), "src", "pss_data")

ID_NAMES_FILEPATH = os.path.join(PWD, "id_names.json")

ID_NAMES_INFO: Dict[str, str]

with open(ID_NAMES_FILEPATH) as fp:
    ID_NAMES_INFO = _json_load(fp)
