#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import datetime
from threading import Thread, Lock
import time
import random

import pss_core as core
import utility as util


class PssCache:
    __UPDATE_INTERVAL = datetime.timedelta(minutes=30)

    def __init__(self, update_url, name, key_name=None):
        self.__update_url = update_url
        self.name = name
        self.__obj_key_name = key_name
        self.__data = None
        self.__modify_date = None
        self.__WRITE_LOCK = Lock()
        self.__READ_LOCK = Lock()
        self.__write_requested = False
        self.__reader_count = 0

    def update_data(self, old_data=None):
        util.dbg_prnt(f'+ PssCache[{self.name}].update_data(old_data)')
        util.dbg_prnt(f'[PssCache[{self.name}].update_data] Fetch data from: {self.__update_url}')
        data = core.get_data_from_url(self.__update_url)
        util.dbg_prnt(f'[PssCache[{self.name}].update_data] Retrieved {len(data)} bytes')
        data_changed = data != old_data
        if data_changed:
            self.__request_write()
            can_write = False
            while not can_write:
                can_write = self.__get_reader_count() == 0
                if not can_write:
                    time.sleep(random.random())
            self.__write_data(data)
            self.__finish_write()
            return True
        return False


    def get_data(self):
        util.dbg_prnt(f'+ PssCache[{self.name}].get_data()')
        if self.__get_is_data_outdated():
            util.dbg_prnt(f'[PssCache[{self.name}].get_data] Data is outdated')
            self.update_data()

        can_read = False
        while not can_read:
            can_read = not self.__get_write_requested()
            if not can_read:
                time.sleep(random.random())

        self.__add_reader()
        result = self.__read_data()
        self.__remove_reader()
        # TODO: copy result
        return result


    def get_data_dict2(self):
        data = self._get_data()
        return core.xmltree_to_dict2(data, self.__obj_key_name)


    def get_data_dict3(self):
        data = self._get_data()
        return core.xmltree_to_dict3(data, self.__obj_key_name)


    def __get_is_data_outdated(self):
        utc_now = util.get_utcnow()
        self.__WRITE_LOCK.acquire()
        modify_date = self.__modify_date
        self.__WRITE_LOCK.release()
        result = modify_date is None or utc_now - modify_date > PssCache.__UPDATE_INTERVAL
        return result


    def __get_reader_count(self):
        self.__READ_LOCK.acquire()
        result = self.__reader_count
        self.__READ_LOCK.release()
        return result


    def __get_write_requested(self):
        self.__WRITE_LOCK.acquire()
        result = self.__write_requested
        self.__WRITE_LOCK.release()
        return result


    def __request_write(self):
        self.__WRITE_LOCK.acquire()
        self.__write_requested = True
        self.__WRITE_LOCK.release()


    def __finish_write(self):
        self.__WRITE_LOCK.acquire()
        self.__write_requested = False
        self.__WRITE_LOCK.release()


    def __write_data(self, data):
        self.__WRITE_LOCK.acquire()
        self.__data = data
        self.__modify_date = util.get_utcnow()
        util.dbg_prnt(f'[PssCache[{self.name}].__write_data] Stored {len(data)} entries on {self.__modify_date}')
        self.__WRITE_LOCK.release()


    def __add_reader(self):
        self.__READ_LOCK.acquire()
        self.__reader_count = self.__reader_count + 1
        self.__READ_LOCK.release()


    def __remove_reader(self):
        self.__READ_LOCK.acquire()
        self.__reader_count = self.__reader_count - 1
        self.__READ_LOCK.release()


    def __read_data(self):
        self.__WRITE_LOCK.acquire()
        result = self.__data
        self.__WRITE_LOCK.release()
        return result
