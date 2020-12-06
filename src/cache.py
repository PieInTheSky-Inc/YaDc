import datetime
import random
from threading import Lock
import time
from typing import Dict, Optional

import pss_core as core
from pss_entity import EntitiesData
import utils


# ---------- Classes ----------

class PssCache:
    def __init__(self, update_path: str, name: str, key_name: str = None, update_interval: int = 15) -> None:
        self.__update_path: str = update_path
        self.__name: str = name
        self.__obj_key_name: str = key_name
        self.__UPDATE_INTERVAL: datetime.timedelta = datetime.timedelta(minutes=update_interval)
        self.__UPDATE_INTERVAL_ORIG: int = update_interval

        self.__data: str = None
        self.__modify_date: datetime.datetime = None
        self.__WRITE_LOCK: Lock = Lock()
        self.__READ_LOCK: Lock = Lock()
        self.__write_requested: bool = False
        self.__reader_count: int = 0


    @property
    def name(self) -> Optional[str]:
        return self.__name


    async def update_data(self, old_data: str = None) -> bool:
        utils.dbg_prnt(f'+ PssCache[{self.name}].update_data(old_data)')
        utils.dbg_prnt(f'[PssCache[{self.name}].update_data] Fetch data from path: {self.__update_path}')
        data = await core.get_data_from_path(self.__update_path)
        utils.dbg_prnt(f'[PssCache[{self.name}].update_data] Retrieved {len(data)} bytes')
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


    async def get_raw_data(self) -> str:
        utils.dbg_prnt(f'+ PssCache[{self.name}].get_data()')
        if self.__get_is_data_outdated():
            utils.dbg_prnt(f'[PssCache[{self.name}].get_data] Data is outdated')
            await self.update_data()

        can_read = False
        while not can_read:
            can_read = not self.__get_write_requested()
            if not can_read:
                time.sleep(random.random())

        self.__add_reader()
        result = self.__read_data()
        self.__remove_reader()
        return result


    async def get_raw_data_dict(self) -> Dict:
        raw_data = await self.get_raw_data()
        result = core.convert_raw_xml_to_dict(raw_data)
        return result


    async def get_data_dict3(self) -> EntitiesData:
        data = await self.get_raw_data()
        return core.xmltree_to_dict3(data)


    def __get_is_data_outdated(self) -> bool:
        if self.__UPDATE_INTERVAL_ORIG == 0:
            return True

        utc_now = utils.get_utc_now()
        self.__WRITE_LOCK.acquire()
        modify_date = self.__modify_date
        self.__WRITE_LOCK.release()
        result = modify_date is None or utc_now - modify_date > self.__UPDATE_INTERVAL
        return result


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


    def __request_write(self) -> None:
        self.__WRITE_LOCK.acquire()
        self.__write_requested = True
        self.__WRITE_LOCK.release()


    def __finish_write(self) -> None:
        self.__WRITE_LOCK.acquire()
        self.__write_requested = False
        self.__WRITE_LOCK.release()


    def __write_data(self, data: str) -> None:
        self.__WRITE_LOCK.acquire()
        self.__data = data
        self.__modify_date = utils.get_utc_now()
        utils.dbg_prnt(f'[PssCache[{self.name}].__write_data] Stored {len(data)} bytes on {self.__modify_date}')
        self.__WRITE_LOCK.release()


    def __add_reader(self) -> None:
        self.__READ_LOCK.acquire()
        self.__reader_count = self.__reader_count + 1
        self.__READ_LOCK.release()


    def __remove_reader(self) -> None:
        self.__READ_LOCK.acquire()
        self.__reader_count = self.__reader_count - 1
        self.__READ_LOCK.release()


    def __read_data(self) -> str:
        self.__WRITE_LOCK.acquire()
        result = self.__data
        self.__WRITE_LOCK.release()
        return result