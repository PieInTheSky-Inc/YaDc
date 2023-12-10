import calendar
from datetime import datetime, timedelta, timezone
import json
import os
import random
from threading import Lock
import time
from typing import Dict, List, Optional, Tuple, Union
import urllib.parse
import yaml

from discord.ext.commands import Context
import pydrive.auth
import pydrive.drive
import pydrive.files

from . import pss_lookups as lookups
from . import settings
from . import utils
from .typehints import EntitiesData, EntityInfo



# ---------- Classes ----------


class TourneyData(object):
    def __init__(self, data: dict) -> None:
        self.__fleets: EntitiesData = None
        self.__users: EntitiesData = None
        self.__meta: Dict[str, object] = data['meta']

        if not self.__meta.get('schema_version', None):
            self.__meta['schema_version'] = 3

        if self.__meta['schema_version'] >= 9:
            self.__fleets = TourneyData.__create_fleet_data_from_data_v7(data['fleets'], data['users']) # No change to prior schema version
            self.__users = TourneyData.__create_user_dict_from_data_v9(data['users'], self.__fleets)
        elif self.__meta['schema_version'] >= 8:
            self.__fleets = TourneyData.__create_fleet_data_from_data_v7(data['fleets'], data['users']) # No change to prior schema version
            self.__users = TourneyData.__create_user_dict_from_data_v8(data['users'], self.__fleets)
        elif self.__meta['schema_version'] >= 7:
            self.__fleets = TourneyData.__create_fleet_data_from_data_v7(data['fleets'], data['users'])
            self.__users = TourneyData.__create_user_dict_from_data_v6(data['users'], self.__fleets) # No change to prior schema version
        elif self.__meta['schema_version'] >= 6:
            self.__fleets = TourneyData.__create_fleet_data_from_data_v6(data['fleets'], data['users'])
            self.__users = TourneyData.__create_user_dict_from_data_v6(data['users'], self.__fleets)
        elif self.__meta['schema_version'] >= 5:
            self.__fleets = TourneyData.__create_fleet_data_from_data_v4(data['fleets'], data['users']) # No change to prior schema version
            self.__users = TourneyData.__create_user_dict_from_data_v5(data['users'], self.__fleets)
        elif self.__meta['schema_version'] >= 4:
            self.__fleets = TourneyData.__create_fleet_data_from_data_v4(data['fleets'], data['users'])
            self.__users = TourneyData.__create_user_dict_from_data_v4(data['users'], self.__fleets)
        elif self.__meta['schema_version'] >= 3:
            self.__fleets = TourneyData.__create_fleet_data_from_data_v3(data['fleets'], data['users'], data['data'])
            self.__users = TourneyData.__create_user_data_from_data_v3(data['users'], data['data'], self.__fleets)
        self.__retrieved_at: datetime = utils.parse.formatted_datetime(data['meta']['timestamp'], include_tz=False, include_tz_brackets=False)
        self.__data_date: datetime = utils.datetime.convert_to_data_date(self.retrieved_at)
        self.__data_date_key: str = TourneyData.create_data_date_key(self.data_date)

        self.__top_100_users: EntitiesData = {}
        top_users_infos = sorted(list(self.__users.values()), key=lambda user_info: -int(user_info.get('Trophy', 0)))[:100]
        top_users_ids = [user_info['Id'] for user_info in top_users_infos]
        for key, value in self.__users.items():
            if key in top_users_ids:
                self.__top_100_users[key] = value
                top_users_ids.remove(key)
                if not top_users_ids:
                    break


    @property
    def collected_in(self) -> float:
        """
        Number of seconds it took to collect the data.
        """
        return self.__meta['duration']
    
    @property
    def data_date(self) -> datetime:
        """
        Determines the point in time relevant to the data.
        """
        return self.__data_date
    
    @property
    def data_date_key(self) -> str:
        """
        A key used for a cache dict.
        """
        return self.__data_date_key
    
    @property
    def data_day(self) -> int:
        """
        Short for `data_date.day`
        """
        return self.data_date.day
    
    @property
    def data_hour(self) -> int:
        """
        Short for `data_date.hour`
        """
        return self.data_date.hour
    
    @property
    def data_month(self) -> int:
        """
        Short for `data_date.month`
        """
        return self.data_date.month
    
    @property
    def data_year(self) -> int:
        """
        Short for `data_date.year`
        """
        return self.data_date.year

    @property
    def fleet_ids(self) -> List[str]:
        return list(self.__fleets.keys())

    @property
    def fleets(self) -> EntitiesData:
        """
        Copy of fleet data
        """
        return dict({key: dict(value) for key, value in self.__fleets.items()})

    @property
    def max_tournament_battle_attempts(self) -> Optional[int]:
        """
        The maximum number of tournament battle attempts for a day.
        """
        result = self.__meta.get('max_tournament_battle_attempts')
        if result:
            return int(result)
        return None

    @property
    def retrieved_at(self) -> datetime:
        """
        Point in time when the data collection started.
        """
        return self.__retrieved_at

    @property
    def retrieved_day(self) -> int:
        """
        Short for `retrieved_at.day`
        """
        return self.__retrieved_at.day

    @property
    def retrieved_month(self) -> int:
        """
        Short for `retrieved_at.month`
        """
        return self.__retrieved_at.month

    @property
    def retrieved_year(self) -> int:
        """
        Short for `retrieved_at.year`
        """
        return self.__retrieved_at.year

    @property
    def schema_version(self) -> int:
        """
        Data collection schema version. Use to determine which information is available for fleets and users.
        """
        return self.__meta['schema_version']

    @property
    def top_100_users(self) -> EntitiesData:
        """
        Copy of top 100 users
        """
        return dict({key: dict(value) for key, value in self.__top_100_users.items()})

    @property
    def user_ids(self) -> List[str]:
        return list(self.__users.keys())

    @property
    def users(self) -> EntitiesData:
        """
        Copy of user data
        """
        return dict({key: dict(value) for key, value in self.__users.items()})


    def get_fleet_data_by_id(self, fleet_id: str) -> EntityInfo:
        """
        Look up fleet by id
        """
        return dict(self.__fleets.get(fleet_id, None))


    def get_fleet_data_by_name(self, fleet_name: str) -> EntitiesData:
        """
        Looks up fleets having the specified fleet_name in their name.
        Case-insensitive.
        """
        result = {}
        for current_fleet_id, current_fleet_data in self.__fleets.items():
            current_fleet_name = current_fleet_data.get('Name', None)
            if current_fleet_name and fleet_name.lower() in current_fleet_name.lower():
                result[current_fleet_id] = dict(current_fleet_data)
        return result


    def get_user_data_by_id(self, user_id: str) -> EntityInfo:
        """
        Look up user by id
        """
        return dict(self.__users.get(user_id, None))


    def get_user_data_by_name(self, user_name: str) -> EntitiesData:
        """
        Looks up users having the specified user_name in their name.
        Case-insensitive.
        """
        result = {}
        for current_user_id, current_user_data in self.__users.items():
            current_user_name = str(current_user_data.get('Name', '')) or None
            if current_user_name and user_name.lower() in current_user_name.lower():
                result[current_user_id] = dict(current_user_data)
        return result
    

    @staticmethod
    def create_data_date_key(dt: datetime) -> str:
        result = f'{dt.year:04d}-{dt.month:02d}-{dt.day:02d}:{dt.hour:02d}'
        return result


    @staticmethod
    def __create_fleet_data_from_data_v3(fleets_data: List[List[Union[int, str]]], users_data: List[List[Union[int, str]]], data: List[List[Union[int, str]]]) -> EntitiesData:
        result = {}
        for i, entry in enumerate(fleets_data, 1):
            alliance_id = entry[0]
            users = [user_info for user_info in data if user_info[1] == alliance_id]
            if len(entry) == 4:
                division_design_id = entry[3]
            else:
                if i > 50:
                    division_design_id = '4'
                elif i > 20:
                    division_design_id = '3'
                elif i > 8:
                    division_design_id = '2'
                else:
                    division_design_id = '1'
            result[alliance_id] = {
                'AllianceId': alliance_id,
                'AllianceName': entry[1],
                'Score': entry[2],
                'DivisionDesignId': division_design_id,
                'NumberOfMembers': len(users),
            }
        ranked_fleets_infos = sorted(sorted(result.values(), key=lambda fleet_info: int(fleet_info['Score']), reverse=True), key=lambda fleet_info: fleet_info['DivisionDesignId'])
        for i, ranked_fleet_info in enumerate(ranked_fleets_infos, 1):
            result[ranked_fleet_info['AllianceId']]['Ranking'] = str(i)
        return result


    @staticmethod
    def __create_fleet_data_from_data_v4(fleets_data: List[List[Union[int, str]]], users_data: List[List[Union[int, str]]]) -> EntitiesData:
        result = {}
        for i, entry in enumerate(fleets_data, 1):
            alliance_id = str(entry[0])
            users = [user_info for user_info in users_data if user_info[2] == entry[0]]
            result[alliance_id] = {
                'AllianceId': alliance_id,
                'AllianceName': entry[1],
                'Score': str(entry[2]),
                'DivisionDesignId': str(entry[3]),
                'Trophy': str(entry[4]),
                'NumberOfMembers': len(users),
            }
        ranked_fleets_infos = sorted(result.values(), key=lambda fleet_info: (fleet_info['DivisionDesignId'], -int(fleet_info['Score']), -int(fleet_info['Trophy'])))
        for i, ranked_fleet_info in enumerate(ranked_fleets_infos, 1):
            result[ranked_fleet_info['AllianceId']]['Ranking'] = str(i)
        return result


    @staticmethod
    def __create_fleet_data_from_data_v6(fleets_data: List[List[Union[int, str]]], users_data: List[List[Union[int, str]]]) -> EntitiesData:
        result = {}
        for i, entry in enumerate(fleets_data, 1):
            alliance_id = str(entry[0])
            users = [user_info for user_info in users_data if user_info[2] == entry[0]]
            result[alliance_id] = {
                'AllianceId': alliance_id,
                'AllianceName': entry[1],
                'Score': str(entry[2]),
                'DivisionDesignId': str(entry[3]),
                'Trophy': str(entry[4]),
                'NumberOfMembers': len(users),
                'ChampionshipScore': str(entry[5]),
            }
        ranked_fleets_infos = sorted(result.values(), key=lambda fleet_info: (fleet_info['DivisionDesignId'], -int(fleet_info['Score']), -int(fleet_info['Trophy'])))
        for i, ranked_fleet_info in enumerate(ranked_fleets_infos, 1):
            result[ranked_fleet_info['AllianceId']]['Ranking'] = str(i)
        return result


    @staticmethod
    def __create_fleet_data_from_data_v7(fleets_data: List[List[Union[int, str]]], users_data: List[List[Union[int, str]]]) -> EntitiesData:
        result = {}
        for i, entry in enumerate(fleets_data, 1):
            alliance_id = str(entry[0])
            users = [user_info for user_info in users_data if user_info[2] == entry[0]]
            result[alliance_id] = {
                'AllianceId': alliance_id,
                'AllianceName': entry[1],
                'Score': str(entry[2]),
                'DivisionDesignId': str(entry[3]),
                'Trophy': str(entry[4]),
                'NumberOfMembers': len(users) if users else str(entry[6]),
                'ChampionshipScore': str(entry[5]),
                'NumberOfApprovedMembers': str(entry[7])
            }
        ranked_fleets_infos = sorted(result.values(), key=lambda fleet_info: (fleet_info['DivisionDesignId'], -int(fleet_info['Score']), -int(fleet_info['Trophy'])))
        for i, ranked_fleet_info in enumerate(ranked_fleets_infos, 1):
            result[ranked_fleet_info['AllianceId']]['Ranking'] = str(i)
        return result




    @staticmethod
    def __create_user_data_from_data_v3(users: List[List[Union[int, str]]], data: List[List[Union[int, str]]], fleet_data: EntitiesData) -> EntitiesData:
        result = {}
        users_dict = dict(users)
        for entry in data:
            fleet_id = entry[1]
            result[entry[0]] = {
                'Id': entry[0],
                'AllianceId': fleet_id,
                'Trophy': entry[2],
                'AllianceScore': entry[3],
                'AllianceMembership': entry[4],
                'AllianceJoinDate': entry[5],
                'LastLoginDate': entry[6],
                'Name': users_dict[entry[0]],
                'Alliance': {}
            }
            if fleet_id and fleet_id != '0':
                fleet_info = fleet_data.get(fleet_id, {})
                for key, value in fleet_info.items():
                    result[entry[0]]['Alliance'][key] = value

        return result


    @staticmethod
    def __create_user_dict_from_data_v4(users: List[List[Union[int, str]]], fleet_data: EntitiesData) -> EntitiesData:
        result = {}
        for user in users:
            fleet_id = str(user[2])
            user_id = str(user[0])
            result[user_id] = {
                'Id': user_id,
                'AllianceId': fleet_id,
                'Trophy': str(user[3]),
                'AllianceScore': str(user[4]),
                'AllianceMembership': lookups.ALLIANCE_MEMBERSHIP_LOOKUP[user[5]],
                'Name': user[1],
                'CrewDonated': str(user[9]),
                'CrewReceived': str(user[10]),
                'PVPAttackWins': str(user[11]),
                'PVPAttackLosses': str(user[12]),
                'PVPAttackDraws': str(user[13]),
                'PVPDefenceWins': str(user[14]),
                'PVPDefenceLosses': str(user[15]),
                'PVPDefenceDraws': str(user[16]),
                'Alliance': {}
            }
            if fleet_id and fleet_id != '0':
                fleet_info = fleet_data.get(fleet_id, {})
                for key, value in fleet_info.items():
                    result[user_id]['Alliance'][key] = value

        return result


    @staticmethod
    def __create_user_dict_from_data_v5(users: List[List[Union[int, str]]], fleet_data: EntitiesData) -> EntitiesData:
        result = {}
        for user in users:
            fleet_id = str(user[2])
            user_id = str(user[0])
            result[user_id] = {
                'Id': user_id,
                'AllianceId': fleet_id,
                'Trophy': str(user[3]),
                'AllianceScore': str(user[4]),
                'AllianceMembership': lookups.ALLIANCE_MEMBERSHIP_LOOKUP[user[5]],
                'AllianceJoinDate': TourneyData.__convert_timestamp_v4(user[6]) if user[6] else None,
                'LastLoginDate': TourneyData.__convert_timestamp_v4(user[7]),
                'Name': user[1],
                'LastHeartBeatDate': TourneyData.__convert_timestamp_v4(user[8]),
                'CrewDonated': str(user[9]),
                'CrewReceived': str(user[10]),
                'PVPAttackWins': str(user[11]),
                'PVPAttackLosses': str(user[12]),
                'PVPAttackDraws': str(user[13]),
                'PVPDefenceWins': str(user[14]),
                'PVPDefenceLosses': str(user[15]),
                'PVPDefenceDraws': str(user[16]),
                'Alliance': {}
            }
            if fleet_id and fleet_id != '0':
                fleet_info = fleet_data.get(fleet_id, {})
                for key, value in fleet_info.items():
                    result[user_id]['Alliance'][key] = value

        return result


    @staticmethod
    def __create_user_dict_from_data_v6(users: List[List[Union[int, str]]], fleet_data: EntitiesData) -> EntitiesData:
        result = {}
        for user in users:
            fleet_id = str(user[2])
            user_id = str(user[0])
            result[user_id] = {
                'Id': user_id,
                'AllianceId': fleet_id,
                'Trophy': str(user[3]),
                'AllianceScore': str(user[4]),
                'AllianceMembership': lookups.ALLIANCE_MEMBERSHIP_LOOKUP[user[5]],
                'AllianceJoinDate': TourneyData.__convert_timestamp_v4(user[6]) if user[6] else None,
                'LastLoginDate': TourneyData.__convert_timestamp_v4(user[7]),
                'Name': user[1],
                'LastHeartBeatDate': TourneyData.__convert_timestamp_v4(user[8]),
                'CrewDonated': str(user[9]),
                'CrewReceived': str(user[10]),
                'PVPAttackWins': str(user[11]),
                'PVPAttackLosses': str(user[12]),
                'PVPAttackDraws': str(user[13]),
                'PVPDefenceWins': str(user[14]),
                'PVPDefenceLosses': str(user[15]),
                'PVPDefenceDraws': str(user[16]),
                'ChampionshipScore': str(user[17]),
                'Alliance': {}
            }
            if fleet_id and fleet_id != '0':
                fleet_info = fleet_data.get(fleet_id, {})
                for key, value in fleet_info.items():
                    result[user_id]['Alliance'][key] = value

        return result


    @staticmethod
    def __create_user_dict_from_data_v8(users: List[List[Union[int, str]]], fleet_data: EntitiesData) -> EntitiesData:
        result = {}
        for user in users:
            fleet_id = str(user[2])
            user_id = str(user[0])
            result[user_id] = {
                'Id': user_id,
                'AllianceId': fleet_id,
                'Trophy': str(user[3]),
                'AllianceScore': str(user[4]),
                'AllianceMembership': lookups.ALLIANCE_MEMBERSHIP_LOOKUP[user[5]],
                'AllianceJoinDate': TourneyData.__convert_timestamp_v4(user[6]) if user[6] else None,
                'LastLoginDate': TourneyData.__convert_timestamp_v4(user[7]),
                'Name': user[1],
                'LastHeartBeatDate': TourneyData.__convert_timestamp_v4(user[8]),
                'CrewDonated': str(user[9]),
                'CrewReceived': str(user[10]),
                'PVPAttackWins': str(user[11]),
                'PVPAttackLosses': str(user[12]),
                'PVPAttackDraws': str(user[13]),
                'PVPDefenceWins': str(user[14]),
                'PVPDefenceLosses': str(user[15]),
                'PVPDefenceDraws': str(user[16]),
                'ChampionshipScore': str(user[17]),
                'HighestTrophy': str(user[18]),
                'Alliance': {}
            }
            if fleet_id and fleet_id != '0':
                fleet_info = fleet_data.get(fleet_id, {})
                for key, value in fleet_info.items():
                    result[user_id]['Alliance'][key] = value

        return result


    @staticmethod
    def __create_user_dict_from_data_v9(users: List[List[Union[int, str]]], fleet_data: EntitiesData) -> EntitiesData:
        result = {}
        for user in users:
            fleet_id = str(user[2])
            user_id = str(user[0])
            result[user_id] = {
                'Id': user_id,
                'AllianceId': fleet_id,
                'Trophy': str(user[3]),
                'AllianceScore': str(user[4]),
                'AllianceMembership': lookups.ALLIANCE_MEMBERSHIP_LOOKUP[user[5]],
                'AllianceJoinDate': TourneyData.__convert_timestamp_v4(user[6]) if user[6] else None,
                'LastLoginDate': TourneyData.__convert_timestamp_v4(user[7]),
                'Name': user[1],
                'LastHeartBeatDate': TourneyData.__convert_timestamp_v4(user[8]),
                'CrewDonated': str(user[9]),
                'CrewReceived': str(user[10]),
                'PVPAttackWins': str(user[11]),
                'PVPAttackLosses': str(user[12]),
                'PVPAttackDraws': str(user[13]),
                'PVPDefenceWins': str(user[14]),
                'PVPDefenceLosses': str(user[15]),
                'PVPDefenceDraws': str(user[16]),
                'ChampionshipScore': str(user[17]),
                'HighestTrophy': str(user[18]),
                'TournamentBonusScore': str(user[19]),
                'Alliance': {}
            }
            if fleet_id and fleet_id != '0':
                fleet_info = fleet_data.get(fleet_id, {})
                for key, value in fleet_info.items():
                    result[user_id]['Alliance'][key] = value

        return result


    @staticmethod
    def __convert_timestamp_v4(timestamp: int) -> str:
        minutes, seconds = divmod(timestamp, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        td = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        dt = utils.constants.PSS_START_DATETIME + td
        result = utils.format.pss_datetime(dt)
        return result





class TourneyDataClient():
    def __init__(self, project_id: str, private_key_id: str, private_key: str, client_email: str, client_id: str, scopes: List[str], folder_id: str, service_account_file_path: str, settings_file_path: str, earliest_date: datetime) -> None:
        print('Create TourneyDataClient')
        self._client_email: str = client_email
        self._client_id: str = client_id
        self._folder_id: str = folder_id
        self._private_key: str = private_key
        self._private_key_id: str = private_key_id
        self._project_id: str = project_id
        self._scopes: List[str] = list(scopes)
        self._service_account_file_path: str = service_account_file_path
        self._settings_file_path: str = settings_file_path
        self.__earliest_date: datetime = earliest_date
        self.__earliest_data_date: datetime = TourneyDataClient.make_data_date(self.__earliest_date.year, self.__earliest_date.month, self.__earliest_date.day, self.__earliest_date.hour)

        self.__READ_LOCK: Lock = Lock()
        self.__WRITE_LOCK: Lock = Lock()
        self.__write_requested: bool = False
        self.__reader_count: int = 0

        self.__cache: Dict[int, Dict[int, Dict[int, TourneyData]]] = {}

        self.__initialized = False
        self.__initialize()


    @property
    def earliest_data_date(self) -> datetime:
        return self.__earliest_data_date

    @property
    def most_recent_data_date(self) -> datetime:
        utc_now = utils.get_utc_now()
        return TourneyDataClient.make_data_date(utc_now.year, utc_now.month, utc_now.day, utc_now.hour)


    def get_data(self, data_date: datetime, initializing: bool = False) -> TourneyData:
        if data_date < self.earliest_data_date:
            raise ValueError(f'There\'s no data from {data_date}. Earliest data available is from {self.earliest_data_date}.')
        
        most_recent_data_from = self.most_recent_data_date
        if data_date > most_recent_data_from:
            raise ValueError(f'There\'s no data from {data_date}. Most recent data available is from {most_recent_data_from}.')

        result = self.__read_data(data_date)

        if result is None:
            result = self.__retrieve_data(data_date, initializing=initializing)
            self.__cache_data(result)

        return result


    def get_latest_daily_data(self, initializing: bool = False) -> TourneyData:
        utc_now = utils.get_utc_now()
        data_date = utils.datetime.strip_time(utc_now)
        result = self.get_data(data_date, initializing=initializing)
        return result


    def get_latest_monthly_data(self, initializing: bool = False) -> TourneyData:
        utc_now = utils.get_utc_now()
        data_date = datetime(utc_now.year, utc_now.month, 1, tzinfo=timezone.utc)
        result = self.get_data(data_date, initializing=initializing)
        return result


    def get_second_latest_daily_data(self, initializing: bool = False) -> TourneyData:
        utc_now = utils.get_utc_now()
        data_date = utils.datetime.strip_time(utc_now - timedelta(days=1))
        result = self.get_data(data_date, initializing=initializing)
        return result


    def __add_reader(self) -> None:
        with self.__READ_LOCK:
            self.__reader_count = self.__reader_count + 1


    def __assert_initialized(self) -> None:
        if self.__drive is None:
            raise Exception('The __drive object has not been initialized, yet!')


    def __cache_data(self, tourney_data: TourneyData) -> bool:
        if tourney_data:
            self.__request_write()
            can_write = False
            while not can_write:
                can_write = self.__get_reader_count() == 0
                if not can_write:
                    time.sleep(random.random())
                with self.__WRITE_LOCK:
                    self.__cache[tourney_data.data_date_key] = tourney_data
                    self.__write_requested = False
                return True
            return False
        return False


    def __ensure_initialized(self) -> None:
        try:
            self.__drive.ListFile({'q': f'\'{self._folder_id}\' in parents and title contains \'random string\''}).GetList()
        except pydrive.auth.InvalidConfigError:
            self.__initialize()


    def __get_first_file(self, file_name: str) -> pydrive.files.GoogleDriveFile:
        file_list = self.__drive.ListFile({'q': f"'{self._folder_id}' in parents and title = '{file_name}'"}).GetList()
        for file_def in file_list:
            return file_def
        return None


    def __get_latest_file(self, data_date: datetime, initializing: bool = False) -> pydrive.files.GoogleDriveFile:
        if not initializing:
            self.__ensure_initialized()
        
        file_name_prefix = TourneyDataClient.__get_gdrive_file_name_prefix(data_date, include_day=True, include_hour=True)
        file_list = self.__drive.ListFile({'q': f'\'{self._folder_id}\' in parents and title contains \'{file_name_prefix}\''}).GetList()
        if not file_list:
            file_name_prefix = TourneyDataClient.__get_gdrive_file_name_prefix(data_date, include_day=True, include_hour=False)
            file_list = self.__drive.ListFile({'q': f'\'{self._folder_id}\' in parents and title contains \'{file_name_prefix}\''}).GetList()
        if not file_list:
            file_name_prefix = TourneyDataClient.__get_gdrive_file_name_prefix(data_date, include_day=False, include_hour=False)
            file_list = self.__drive.ListFile({'q': f'\'{self._folder_id}\' in parents and title contains \'{file_name_prefix}\''}).GetList()
        if file_list:
            file_list = sorted(file_list, key=lambda f: f['title'], reverse=True)
            return file_list[0]
        return None


    def __get_reader_count(self) -> int:
        with self.__READ_LOCK:
            result = self.__reader_count
        return result


    def __get_write_requested(self) -> bool:
        with self.__WRITE_LOCK:
            result = self.__write_requested
        return result


    def __initialize(self) -> None:
        TourneyDataClient.create_service_account_credential_json(self._project_id, self._private_key_id, self._private_key, self._client_email, self._client_id, self._service_account_file_path)
        TourneyDataClient.create_service_account_settings_yaml(self._settings_file_path, self._service_account_file_path, self._scopes)
        self.__gauth: pydrive.auth.GoogleAuth = pydrive.auth.GoogleAuth(settings_file=self._settings_file_path)
        credentials = pydrive.auth.ServiceAccountCredentials.from_json_keyfile_name(self._service_account_file_path, self._scopes)
        self.__gauth.credentials = credentials
        self.__drive: pydrive.drive.GoogleDrive = pydrive.drive.GoogleDrive(self.__gauth)
        self.get_latest_monthly_data(initializing=True)
        self.get_latest_daily_data(initializing=True)
        self.get_second_latest_daily_data(initializing=True)
        self.__initialized = True


    def __read_data(self, data_date: datetime) -> Optional[TourneyData]:        
        can_read = False
        while not can_read:
            can_read = not self.__get_write_requested()
            if not can_read:
                time.sleep(random.random())

        self.__add_reader()
        result = self.__cache.get(TourneyData.create_data_date_key(data_date))
        self.__remove_reader()
        return result


    def __remove_reader(self) -> None:
        with self.__READ_LOCK:
            self.__reader_count = self.__reader_count - 1


    def __request_write(self) -> None:
        with self.__WRITE_LOCK:
            self.__write_requested = True


    def __retrieve_data(self, data_date: datetime, initializing: bool = False) -> TourneyData:
        if not initializing:
            self.__ensure_initialized()
        g_file = self.__get_latest_file(data_date, initializing=initializing)
        result = None
        if g_file:
            raw_data = g_file.GetContentString()
            data = json.loads(raw_data)
            if data:
                result = TourneyData(data)
        return result


    @staticmethod
    def create_service_account_credential_json(project_id: str, private_key_id: str, private_key: str, client_email: str, client_id: str, service_account_file_path: str) -> None:
        if os.path.exists(service_account_file_path):
            print(f'Using existing service account connection file at: {service_account_file_path}')
            return
        
        contents = {
            'type': 'service_account',
            'project_id': project_id,
            'private_key_id': private_key_id,
            'private_key': private_key,
            'client_email': client_email,
            'client_id': client_id,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
            'client_x509_cert_url': f'https://www.googleapis.com/robot/v1/metadata/x509/{urllib.parse.quote(client_email)}',
        }
        with open(service_account_file_path, 'w+') as service_file:
            json.dump(contents, service_file, indent=2)
        print(f'Created service account connection file at: {service_account_file_path}')


    @staticmethod
    def create_service_account_settings_yaml(settings_file_path: str, service_account_file_path: str, scopes: List[str]) -> None:
        if not os.path.isfile(settings_file_path):
            contents = {}
            contents['client_config_backend'] = 'file'
            contents['client_config_file'] = service_account_file_path
            contents['save_credentials'] = True
            contents['save_credentials_backend'] = 'file'
            contents['save_credentials_file'] = 'credentials.json'
            contents['oauth_scope'] = scopes

            with open(settings_file_path, 'w+') as settings_file:
                yaml.dump(contents, settings_file)
            print(f'Created settings yaml file at: {settings_file_path}')
    

    @staticmethod
    def __get_gdrive_file_name_prefix(data_date: datetime, include_day: bool = True, include_hour: bool = True) -> str:
        data_date = data_date - timedelta(minutes=1)
        result = f'pss-top-100_{data_date.year:04d}{data_date.month:02d}'
        if include_day or include_hour:
            result += f'{data_date.day:02d}'
        if include_hour:
            result += f'-{data_date.hour:02d}'
        return result


    @staticmethod
    def __fix_filename_datetime(dt: datetime) -> datetime:
        dt = datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)
        dt = dt - timedelta(minutes=1)
        return dt


    @staticmethod
    def __get_latest_file_name(dt: datetime) -> str:
        dt = TourneyDataClient.__fix_filename_datetime(dt)
        timestamp = dt.strftime('%Y%m%d-%H%M%S')
        result = f'pss-top-100_{timestamp}.json'
        return result


    @staticmethod
    def __get_last_tourney_year_and_month(dt: datetime) -> Tuple[int, int]:
        dt = TourneyDataClient.__fix_filename_datetime(dt)
        return dt.year, dt.month


    @staticmethod
    def retrieve_past_parameters(ctx: Context, month: str, year: str) -> Tuple[str, str, str]:
        param = None

        if month is not None:
            if year is not None:
                try:
                    int(year)
                except (TypeError, ValueError):
                    year = None
            if utils.datetime.is_valid_month(month) is False:
                try:
                    year = int(month)
                except (TypeError, ValueError):
                    year = None
                if year is not None:
                    year = str(year)
                month = None

        args_provided_count = (0 if month is None else 1) + (0 if year is None else 1)
        if args_provided_count == 1:
            param = month or year
            month = None
            year = None
        else:
            param = utils.discord.get_exact_args(ctx, args_provided_count)
            if not param:
                param = None

        return (month, year, param)


    @staticmethod
    def retrieve_past_day_month_year(month: str, year: str, utc_now: datetime) -> Tuple[int, int]:
        if not utc_now:
            utc_now = utils.get_utc_now()

        if month is None:
            temp_month = utc_now.month - 1
            if not settings.MOST_RECENT_TOURNAMENT_DATA:
                temp_month -= 1
            temp_month = temp_month % 12 + 1
        else:
            month = str(month)
            temp_month = utils.datetime.MONTH_NAME_TO_NUMBER.get(month.lower(), None)
            temp_month = temp_month or utils.datetime.MONTH_SHORT_NAME_TO_NUMBER.get(month.lower(), None)
            if temp_month is None:
                try:
                    temp_month = int(month)
                except:
                    raise ValueError(f'Parameter month got an invalid value: {month}')
        if year is None:
            year = utc_now.year
            if utc_now.month + (1 if settings.MOST_RECENT_TOURNAMENT_DATA else 0) <= temp_month:
                year -= 1
        year = int(year)
        _, day = calendar.monthrange(year, temp_month)
        return day, temp_month, int(year)
    

    @staticmethod
    def make_data_date(year: int, month: int, day: int = None, hour: int = None, make_future_data_date: bool = True) -> datetime:
        if year is None:
            raise ValueError()
        
        if hour is not None:
            if day is None:
                raise Exception()
            
            return datetime(year, month, day, hour, tzinfo=timezone.utc) + make_future_data_date * utils.datetime.ONE_HOUR
        
        if day is not None:
            return datetime(year, month, day, tzinfo=timezone.utc) + make_future_data_date * utils.datetime.ONE_DAY
        
        if month is not None:
            if make_future_data_date:
                #month += 1
                add_years = month // 12
                if add_years:
                    month %= 12
                    year += add_years
                month += 1

            return datetime(year, month, 1, tzinfo=timezone.utc)
        
        return datetime(year + make_future_data_date * 1, 1, 1, tzinfo=timezone.utc)
