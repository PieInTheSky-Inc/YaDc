

import pss_core as core


def get_alliance_users(alliance_id):
    path = f'AllianceService/ListUsers?allianceId={alliance_id}&skip=0&take=100'



def search_alliances(alliance_name):
    path = f'AllianceService/SearchAlliances?name={alliance_name}&skip=0&take=100'
    raw_data = core.get_data_from_path(path)
    data = core.xmltree_to_dict3(raw_data)
    result = [data[key] for key in data.keys()]
    return result




# ---------- stars command methods ----------



def get_top_100_raw():
    return None


def get_tournament_fleets_raw():
    return None