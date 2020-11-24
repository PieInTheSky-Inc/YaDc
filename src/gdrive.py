#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import calendar
from datetime import datetime, timedelta, timezone
from discord.ext.commands import Context
import json
import os
import pydrive.auth
import pydrive.drive
import pydrive.files
import random
from threading import Lock
import time
from typing import Dict, List, Tuple, Union
import urllib.parse
import yaml

from pss_entity import EntitiesData, EntityInfo
import pss_fleet as fleet
import pss_lookups as lookups
import pss_user as user
import settings
import utility as util





# ---------- Classes ----------

class TourneyData(object):
    def __init__(self, raw_data: str) -> None:
        data = json.loads(raw_data)

        self.__fleets: EntitiesData
        self.__users: EntitiesData
        self.__meta: Dict[str, object] = data['meta']
        if not self.__meta.get('schema_version', None):
            self.__meta['schema_version'] = 3
        if self.__meta['schema_version'] == 3:
            self.__fleets = TourneyData.__create_fleet_data_from_data_v3(data['fleets'])
            self.__users = TourneyData.__create_user_data_from_data_v3(data['users'], data['data'], self.__fleets)
        elif self.__meta['schema_version'] == 4:
            self.__fleets = TourneyData.__create_fleet_data_from_data_v4(data['fleets'])
            self.__users = TourneyData.__create_user_dict_from_data_v4(data['users'], self.__fleets)
        elif self.__meta['schema_version'] == 5:
            self.__fleets = TourneyData.__create_fleet_data_from_data_v5(data['fleets'])
            self.__users = TourneyData.__create_user_dict_from_data_v5(data['users'], self.__fleets)
        self.__data_date: datetime = util.parse_formatted_datetime(data['meta']['timestamp'], include_tz=False, include_tz_brackets=False)


    @property
    def collected_in(self) -> float:
        """
        Number of seconds it took to collect the data.
        """
        return self.__meta['duration']

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
    def month(self) -> int:
        """
        Short for data_date.month
        """
        return self.__data_date.month

    @property
    def retrieved_at(self) -> datetime:
        """
        Point in time when the data collection started.
        """
        return self.__data_date

    @property
    def schema_version(self) -> int:
        """
        Data collection schema version. Use to determine which information is available for fleets and users.
        """
        return self.__meta['schema_version']

    @property
    def user_ids(self) -> List[str]:
        return list(self.__users.keys())

    @property
    def users(self) -> EntitiesData:
        """
        Copy of user data
        """
        return dict({key: dict(value) for key, value in self.__users.items()})

    @property
    def year(self) -> int:
        """
        Short for data_date.year
        """
        return self.__data_date.year


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
            current_fleet_name = current_fleet_data.get(user.USER_DESCRIPTION_PROPERTY_NAME, None)
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
            current_user_name = current_user_data.get(user.USER_DESCRIPTION_PROPERTY_NAME, None)
            if current_user_name and user_name.lower() in current_user_name.lower():
                result[current_user_id] = dict(current_user_data)
        return result


    @staticmethod
    def __create_fleet_data_from_data_v3(fleet_data: List[List[Union[int, str]]]) -> EntitiesData:
        result = {}
        for i, entry in enumerate(fleet_data, 1):
            alliance_id = entry[0]
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
                'DivisionDesignId': division_design_id
            }
        ranked_fleets_infos = sorted(sorted(result.values(), key=lambda fleet_info: int(fleet_info['Score']), reverse=True), key=lambda fleet_info: fleet_info['DivisionDesignId'])
        for i, ranked_fleet_info in enumerate(ranked_fleets_infos, 1):
            result[ranked_fleet_info[fleet.FLEET_KEY_NAME]]['Ranking'] = str(i)
        return result


    @staticmethod
    def __create_fleet_data_from_data_v4(fleet_data: List[List[Union[int, str]]]) -> EntitiesData:
        result = {}
        for i, entry in enumerate(fleet_data, 1):
            alliance_id = str(entry[0])
            result[alliance_id] = {
                'AllianceId': alliance_id,
                'AllianceName': entry[1],
                'Score': str(entry[2]),
                'DivisionDesignId': str(entry[3]),
                'Trophy': str(entry[4])
            }
        ranked_fleets_infos = sorted(result.values(), key=lambda fleet_info: (fleet_info['DivisionDesignId'], -int(fleet_info['Score']), -int(fleet_info['Trophy'])))
        for i, ranked_fleet_info in enumerate(ranked_fleets_infos, 1):
            result[ranked_fleet_info[fleet.FLEET_KEY_NAME]]['Ranking'] = str(i)
        return result


    @staticmethod
    def __create_fleet_data_from_data_v5(fleet_data: List[List[Union[int, str]]]) -> EntitiesData:
        return TourneyData.__create_fleet_data_from_data_v4(fleet_data)


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
                'AllianceJoinDate': TourneyData.__convert_timestamp_v4(user[6]),
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
    def __convert_timestamp_v4(timestamp: int) -> str:
        minutes, seconds = divmod(timestamp, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        td = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        dt = settings.PSS_START_DATETIME + td
        result = util.format_pss_datetime(dt)
        return result









class TourneyDataClient():
    def __init__(self, project_id: str, private_key_id: str, private_key: str, client_email: str, client_id: str, scopes: List[str], folder_id: str, service_account_file_path: str, settings_file_path: str, earliest_date: datetime) -> None:
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

        self.__READ_LOCK: Lock = Lock()
        self.__WRITE_LOCK: Lock = Lock()
        self.__write_requested: bool = False
        self.__reader_count: int = 0

        self.__cache: Dict[int, Dict[int, TourneyData]] = {}

        self.__initialized = False
        self.__initialize()


    @property
    def from_month(self) -> int:
        return self.__earliest_date.month

    @property
    def from_year(self) -> int:
        return self.__earliest_date.year

    @property
    def to_month(self) -> int:
        return max(self.__cache.get(self.to_year, {}).keys())

    @property
    def to_year(self) -> int:
        return max(self.__cache.keys())


    def get_data(self, year: int, month: int, initializing: bool = False) -> TourneyData:
        if year < self.from_year:
            raise ValueError(f'There\'s no data from {year}. Earliest data available is from {calendar.month_name[self.from_month]} {self.from_year}.')
        if year == self.from_year:
            if month < self.from_month:
                raise ValueError(f'There\'s no data from {calendar.month_name[month]} {year}. Earliest data available is from {calendar.month_name[self.from_month]} {self.from_year}.')
        if not initializing:
            if year > self.to_year or (year == self.to_year and month > self.to_month):
                utc_now = util.get_utc_now()
                if utc_now.year <= self.to_year and utc_now.month - 1 <= self.to_month:
                    raise ValueError(f'There\'s no data from {calendar.month_name[month]} {year}. Most recent data available is from {calendar.month_name[self.to_month]} {self.to_year}.')

        result = self.__read_data(year, month)

        if result is None:
            result = self.__retrieve_data(year, month, initializing=initializing)
            self.__cache_data(result)

        return result


    def get_latest_data(self, initializing: bool = False) -> TourneyData:
        utc_now = util.get_utc_now()
        year, month = TourneyDataClient.__get_tourney_year_and_month(utc_now)
        result = None
        while year > self.from_year or month >= self.from_month:
            result = self.get_data(year, month, initializing=initializing)
            if result:
                break
            month -= 1
            if month == 0:
                year -= 1
                month = 12
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
                    self.__cache.setdefault(tourney_data.year, {})[tourney_data.month] = tourney_data
                    self.__write_requested = False
                return True
            return False
        return False


    def __ensure_initialized(self) -> None:
        try:
            self.__drive.ListFile({'q': f'\'{self._folder_id}\' in parents and title contains \'highaöegjoyödfmj giod\''}).GetList()
        except pydrive.auth.InvalidConfigError:
            self.__initialize()


    def __get_first_file(self, file_name: str) -> pydrive.files.GoogleDriveFile:
        file_list = self.__drive.ListFile({'q': f"'{self._folder_id}' in parents and title = '{file_name}'"}).GetList()
        for file_def in file_list:
            return file_def
        return None


    def __get_latest_file(self, year: int, month: int, day: int = None, initializing: bool = False) -> pydrive.files.GoogleDriveFile:
        self.__ensure_initialized()
        file_name_part: str = f'{year:04d}{month:02d}'
        if day is not None:
            file_name_part += f'{day:02d}'
        file_list = self.__drive.ListFile({'q': f'\'{self._folder_id}\' in parents and title contains \'pss-top-100_{file_name_part}\''}).GetList()
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
        self.get_latest_data(initializing=True)
        self.__initialized = True


    def __read_data(self, year: int, month: int) -> TourneyData:
        can_read = False
        while not can_read:
            can_read = not self.__get_write_requested()
            if not can_read:
                time.sleep(random.random())

        self.__add_reader()
        result = self.__cache.get(year, {}).get(month, None)
        self.__remove_reader()
        return result


    def __remove_reader(self) -> None:
        with self.__READ_LOCK:
            self.__reader_count = self.__reader_count - 1


    def __request_write(self) -> None:
        with self.__WRITE_LOCK:
            self.__write_requested = True


    def __retrieve_data(self, year: int, month: int, initializing: bool = False) -> TourneyData:
        self.__ensure_initialized()
        g_file = self.__get_latest_file(year, month, initializing=initializing)
        if g_file:
            raw_data = g_file.GetContentString()
            result = TourneyData(raw_data)
        else:
            result = None
        return result


    @staticmethod
    def create_service_account_credential_json(project_id: str, private_key_id: str, private_key: str, client_email: str, client_id: str, service_account_file_path: str) -> None:
        contents = {}
        contents['type'] = 'service_account'
        contents['project_id'] = project_id
        contents['private_key_id'] = private_key_id
        contents['private_key'] = private_key
        contents['client_email'] = client_email
        contents['client_id'] = client_id
        contents['auth_uri'] = 'https://accounts.google.com/o/oauth2/auth'
        contents['token_uri'] = 'https://oauth2.googleapis.com/token'
        contents['auth_provider_x509_cert_url'] = 'https://www.googleapis.com/oauth2/v1/certs'
        contents['client_x509_cert_url'] = f'https://www.googleapis.com/robot/v1/metadata/x509/{urllib.parse.quote(client_email)}'
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
    def __get_tourney_year_and_month(dt: datetime) -> Tuple[int, int]:
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
            if util.is_valid_month(month) is False:
                try:
                    year = int(month)
                except (TypeError, ValueError):
                    year = None
                if year is not None:
                    year = str(year)
                month = None

        args_provided_count = (0 if month is None else 1) + (0 if year is None else 1)
        param = util.get_exact_args(ctx, args_provided_count)
        if not param:
            param = None

        return (month, year, param)


    @staticmethod
    def retrieve_past_month_year(month: str, year: str, utc_now: datetime) -> Tuple[int, int]:
        if not utc_now:
            utc_now = util.get_utc_now()

        if month is None:
            temp_month = (utc_now.month - 2) % 12 + 1
        else:
            temp_month = lookups.MONTH_NAME_TO_NUMBER.get(month.lower(), None)
            temp_month = temp_month or lookups.MONTH_SHORT_NAME_TO_NUMBER.get(month.lower(), None)
            if temp_month is None:
                try:
                    temp_month = int(month)
                except:
                    raise ValueError(f'Parameter month got an invalid value: {month}')
        if year is None:
            year = utc_now.year
            if utc_now.month < temp_month:
                year -= 1
        return temp_month, int(year)