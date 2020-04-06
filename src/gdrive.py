#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta, timezone
import json
import os
import pydrive.auth
import pydrive.drive
import pydrive.files
import random
from threading import Lock
import time
import urllib.parse
import yaml

import utility as util



class TourneyData():
    def __init__(self, project_id: str, private_key_id: str, private_key: str, client_email: str, client_id: str, scopes: list, folder_id: str, service_account_file_path: str, settings_file_path: str):
        self._client_email: str = client_email
        self._client_id: str = client_id
        self._folder_id: str = folder_id
        self._private_key: str = private_key
        self._private_key_id: str = private_key_id
        self._project_id: str = project_id
        self._scopes: list = list(scopes)
        self._service_account_file_path: str = service_account_file_path
        self._settings_file_path: str = settings_file_path

        self.__READ_LOCK: Lock = Lock()
        self.__WRITE_LOCK: Lock = Lock()
        self.__read_requestes: bool = False
        self.__write_requested: bool = False
        self.__reader_count: int = 0

        self.__retrieved_date: datetime = None
        self.__fleet_data: dict = None
        self.__user_data: dict = None
        self.__data_date: dict = None

        self.__initialized = False
        self.__initialize()


    def get_data(self) -> (dict, dict, datetime):
        utc_now = util.get_utcnow()
        if self.__is_data_outdated(utc_now):
            self.__update_data()

        can_read = False
        while not can_read:
            can_read = not self.__get_write_requested()
            if not can_read:
                time.sleep(random.random())

        self.__add_reader()
        result = self.__read_data()
        self.__remove_reader()
        return result


    def get_data_date(self) -> datetime:
        self.__WRITE_LOCK.acquire()
        result = self.__data_date
        self.__WRITE_LOCK.release()
        return result


    def get_retrieved_date(self) -> datetime:
        self.__WRITE_LOCK.acquire()
        result = self.__retrieved_date
        self.__WRITE_LOCK.release()
        return result


    def __add_reader(self) -> None:
        self.__READ_LOCK.acquire()
        self.__reader_count = self.__reader_count + 1
        self.__READ_LOCK.release()


    def __assert_initialized(self) -> None:
        if self.__drive is None:
            raise Exception('The __drive object has not been initialized, yet!')


    def __create_service_account_credential_json(self, project_id: str, private_key_id: str, private_key: str, client_email: str, client_id: str, service_account_file_path: str) -> None:
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


    def __create_service_account_settings_yaml(self, settings_file_path: str, service_account_file_path: str, scopes: list) -> None:
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


    def __ensure_initialized(self) -> None:
        self.__initialize()


    def __finish_write(self) -> None:
        self.__WRITE_LOCK.acquire()
        self.__write_requested = False
        self.__WRITE_LOCK.release()


    def __get_first_file(self, file_name: str) -> pydrive.files.GoogleDriveFile:
        file_list = self.__drive.ListFile({'q': f"'{self._folder_id}' in parents and title = '{file_name}'"}).GetList()
        for file_def in file_list:
            return file_def
        return None


    def __get_reader_count(self) -> int:
        self.__READ_LOCK.acquire()
        result = self.__reader_count
        self.__READ_LOCK.release()
        return result


    def __get_write_requested(self) -> bool:
        self.__WRITE_LOCK.acquire()
        result = self.__write_requested
        self.__WRITE_LOCK.release()
        return result


    def __initialize(self):
        self.__create_service_account_credential_json(self._project_id, self._private_key_id, self._private_key, self._client_email, self._client_id, self._service_account_file_path)
        self.__create_service_account_settings_yaml(self._settings_file_path, self._service_account_file_path, self._scopes)
        self.__gauth: pydrive.auth.GoogleAuth = pydrive.auth.GoogleAuth(settings_file=self._settings_file_path)
        credentials = pydrive.auth.ServiceAccountCredentials.from_json_keyfile_name(self._service_account_file_path, self._scopes)
        self.__gauth.credentials = credentials
        self.__drive: pydrive.drive.GoogleDrive = pydrive.drive.GoogleDrive(self.__gauth)
        self.__update_data(initializing=True)
        self.__initialized = True


    def __is_data_outdated(self, utc_now: datetime) -> bool:
        retrieved_date = self.get_retrieved_date()
        result = retrieved_date is None or (retrieved_date < utc_now and (retrieved_date.month < utc_now.month or retrieved_date.year < utc_now.year))
        return result


    def __read_data(self) -> (dict, dict, datetime):
        self.__WRITE_LOCK.acquire()
        result = (dict(self.__fleet_data), dict(self.__user_data), self.__data_date)
        self.__WRITE_LOCK.release()
        return result


    def __remove_reader(self) -> None:
        self.__READ_LOCK.acquire()
        self.__reader_count = self.__reader_count - 1
        self.__READ_LOCK.release()


    def __request_write(self) -> None:
        self.__WRITE_LOCK.acquire()
        self.__write_requested = True
        self.__WRITE_LOCK.release()


    def __update_data(self, initializing: bool = False) -> bool:
        if not initializing:
            self.__initialize()

        utc_now = util.get_utcnow()
        g_file_name = TourneyData.__get_latest_file_name(utc_now)
        g_file = self.__get_first_file(g_file_name)
        raw_data = g_file.GetContentString()
        data = json.loads(raw_data)
        new_fleet_data = TourneyData.__create_fleet_dict_from_data(data['fleets'])
        new_user_data = TourneyData.__create_user_dict_from_data(data['users'], data['data'])
        data_date = util.parse_formatted_datetime(data['meta']['timestamp'], include_tz=False, include_tz_brackets=False)

        self.__request_write()
        can_write = False
        while not can_write:
            can_write = self.__get_reader_count() == 0
            if not can_write:
                time.sleep(random.random())
            self.__write_data(new_fleet_data, new_user_data, utc_now, data_date)
            self.__finish_write()
            return True
        return False


    def __write_data(self, fleet_data: dict, user_data: dict, retrieved_date: datetime, data_date: datetime) -> None:
        self.__WRITE_LOCK.acquire()
        self.__fleet_data = fleet_data
        self.__user_data = user_data
        self.__retrieved_date = retrieved_date
        self.__data_date = data_date
        self.__WRITE_LOCK.release()


    @staticmethod
    def __create_fleet_dict_from_data(fleet_data: list) -> dict:
        result = {}
        for i, entry in enumerate(fleet_data):
            result[entry[0]] = {
                'AllianceId': entry[0],
                'AllianceName': entry[1],
                'Score': entry[2]
            }
            if len(entry) == 4:
                division_design_id = entry[3]
            else:
                if i >= 50:
                    division_design_id = 4
                elif i >= 20:
                    division_design_id = 3
                elif i >= 8:
                    division_design_id = 2
                else:
                    division_design_id = 1
            result[entry[0]]['DivisionDesignId'] = division_design_id
        return result


    @staticmethod
    def __create_user_dict_from_data(users: list, data: list) -> dict:
        result = {}
        users_dict = dict(users)
        for entry in data:
            result[entry[0]] = {
                'Id': entry[0],
                'AllianceId': entry[1],
                'Trophy': entry[2],
                'AllianceScore': entry[3],
                'AllianceMembership': entry[4],
                'AllianceJoinDate': entry[5],
                'LastLoginDate': entry[6],
                'Name': users_dict[entry[0]]
            }
        return result


    @staticmethod
    def __fix_filename_datetime(dt: datetime) -> datetime:
        dt = datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)
        dt = dt - timedelta(minutes=1)
        return dt


    @staticmethod
    def __get_latest_file_name(dt: datetime) -> str:
        dt = TourneyData.__fix_filename_datetime(dt)
        timestamp = dt.strftime('%Y%m%d-%H%M%S')
        result = f'pss-top-100_{timestamp}.json'
        return result
