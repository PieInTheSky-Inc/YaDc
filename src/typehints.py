from datetime import datetime
from typing import Dict, List, Union


EntityInfo = Dict[str, 'EntityInfo']
EntitiesData = Dict[str, EntityInfo]

SalesCache = List[Dict[str, Union[int, str, datetime]]]