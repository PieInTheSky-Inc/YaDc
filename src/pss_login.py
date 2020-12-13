from datetime import datetime, timedelta
import hashlib
import random
from typing import List, Optional

import aiohttp
from asyncio import Lock

import database as db
import pss_core as core
import utils


# ---------- Constants & Internals ----------

ACCESS_TOKEN_TIMEOUT: timedelta = timedelta(hours=11, minutes=30)

DEFAULT_DEVICE_TYPE: str = 'DeviceTypeMac'
DEVICES: 'DeviceCollection' = None





# ---------- Empty Classes ----------

class LoginError(Exception):
    """
    Raised, when an error occurs during login.
    """
    pass


class DeviceInUseError(LoginError):
    """
    Raised, when a device belongs to a real account.
    """
    pass





# ---------- Classes ----------

class Device():
    def __init__(self, device_key: str, checksum: str = None, can_login_until: datetime = None, device_type: str = None) -> None:
        self.__key: str = device_key
        self.__device_type = device_type or DEFAULT_DEVICE_TYPE
        self.__checksum: str = checksum or __create_device_checksum(self.__key, self.__device_type)
        self.__last_login: datetime = None
        self.__can_login_until: datetime = can_login_until
        self.__access_token: str = None
        self.__access_token_expires_at: datetime = None
        self.__set_access_token_expiry()
        self.__user: dict = None
        self.__token_lock: Lock = Lock()
        self.__update_lock: Lock = Lock()
        self.__login_path: str = f'UserService/DeviceLogin8?deviceKey={self.__key}&isJailBroken=false&checksum={self.__checksum}&deviceType=DeviceTypeMac&languageKey=en&advertisingkey=%22%22'
        self.__can_login_until_changed: bool = False


    @property
    def access_token_expired(self) -> bool:
        if self.__access_token and self.__access_token_expires_at:
            return self.__access_token_expires_at < utils.get_utc_now()
        return True

    @property
    def can_login(self) -> bool:
        if self.__can_login_until is None:
            return True
        utc_now = utils.get_utc_now()
        if self.__can_login_until <= utc_now and self.__can_login_until.date == utc_now.date:
            return False
        return True

    @property
    def can_login_until(self) -> datetime:
        return self.__can_login_until

    @property
    def checksum(self) -> str:
        return self.__checksum

    @property
    def key(self) -> str:
        return self.__key


    async def get_access_token(self) -> str:
        """
        Returns a valid access token. If there's no valid access token related to this Device, this method will attempt to log in and retrieve an access token via the PSS API.
        """
        async with self.__token_lock:
            if self.access_token_expired:
                if self.can_login:
                    await self.__login()
                else:
                    raise LoginError('Cannot login currently. Please try again later.')
            return self.__access_token


    async def update_device(self) -> bool:
        async with self.__update_lock:
            if self.__can_login_until_changed:
                self.__can_login_until_changed = False
                result = await __db_try_update_device(self)
                return result
            return True


    async def __login(self) -> None:
        utc_now = utils.get_utc_now()
        if not self.__key:
            self.__key = __create_device_key()
        if not self.__checksum:
            self.__checksum = __create_device_checksum(self.__key, self.__device_type)

        base_url = await core.get_base_url()
        url = f'{base_url}{self.__login_path}'
        utc_now = utils.get_utc_now()
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                data = await response.text(encoding='utf-8')

        result = utils.convert.raw_xml_to_dict(data)
        self.__last_login = utc_now
        if 'UserService' in result.keys():
            user = result['UserService']['UserLogin']['User']

            if user.get('Name', None):
                self.__user = None
                self.__access_token = None
                raise DeviceInUseError('Cannot login. The device is already in use.')
            self.__user = user
            self.__access_token = result['UserService']['UserLogin']['accessToken']
            self.__set_can_login_until(utc_now)
        else:
            self.__access_token = None
        self.__set_access_token_expiry()


    def __set_access_token_expiry(self) -> None:
        if self.__last_login and self.__access_token:
            self.__access_token_expires_at = self.__last_login + ACCESS_TOKEN_TIMEOUT
        else:
            self.__access_token_expires_at = None


    def __set_can_login_until(self, last_login: datetime) -> None:
        if not self.__can_login_until or last_login > self.__can_login_until:
            next_day = utils.datetime.get_next_day(self.__can_login_until) - utils.datetime.ONE_SECOND
            login_until = last_login + utils.datetime.FIFTEEN_HOURS
            self.__can_login_until = min(login_until, next_day)
            self.__can_login_until_changed = True






class DeviceCollection():
    def __init__(self, devices: List[Device] = None) -> None:
        self.__devices: List[Device] = devices or []
        self.__position: int = None
        self.__fix_position()
        self.__token_lock: Lock = Lock()
        if not self.__devices:
            self.__devices.append(Device(__create_device_key()))


    @property
    def count(self) -> int:
        return len(self.__devices)

    @property
    def current(self) -> Device:
        if self.count == 0:
            raise Exception('Cannot return current device. There\'re no devices!')
        else:
            return self.__devices[self.__position]

    @property
    def devices(self) -> List[Device]:
        return list(self.__devices)


    async def add_device(self, device: Device) -> None:
        for existing_device in self.__devices:
            if existing_device.key == device.key:
                return
        await __db_try_store_device(device)
        self.__devices.append(device)
        self.select_device_by_key(device.key)


    async def add_devices(self, devices: List[Device]) -> None:
        for device in devices:
            await self.add_device(device)


    async def add_device_by_key(self, device_key: str) -> Device:
        for existing_device in self.__devices:
            if existing_device.key == device_key:
                return existing_device
        device = Device(device_key)
        await __db_try_store_device(device)
        self.__devices.append(device)
        self.__fix_position()
        return device


    async def create_device(self) -> Device:
        device = Device(__create_device_key())
        await self.add_device(device)
        return device


    async def remove_device(self, device: Device) -> None:
        await self.remove_device_by_key(device.key)


    async def remove_device_by_key(self, device_key: str) -> None:
        if self.count == 0:
            raise Exception('Cannot remove device. There\'re no devices!')
        for existing_device in self.__devices:
            if existing_device.key == device_key:
                await __db_try_delete_device(existing_device)
                self.__devices = [device for device in self.__devices if device.key != device_key]
                self.__fix_position()
                return
        raise Exception('Cannot remove device. A device with the specified key does not exist!')


    def select_device_by_key(self, device_key: str) -> Device:
        if self.count == 0:
            raise Exception('Cannot select a device. There\'re no devices!')
        for i, device in enumerate(self.__devices):
            if device_key == device.key:
                self.__position = i
                return device
        raise Exception(f'Could not find device with key \'{device_key}\'')


    async def get_access_token(self) -> str:
        async with self.__token_lock:
            if self.count == 0:
                raise Exception('Cannot get access token. There\'re no devices!')
            result = None
            current_device = None
            tried_devices_count = 0
            current_can_login_until = False
            while tried_devices_count < self.count:
                current_device = self.current
                current_can_login_until = current_device.can_login_until
                try:
                    tried_devices_count += 1
                    result = await current_device.get_access_token()
                    break
                except DeviceInUseError:
                    await self.remove_device(current_device)
                except Exception as err:
                    print(f'[DeviceCollection.get_access_token] Could not log in:\n{err}')
                    self.__select_next()
                current_device = self.current
            if result is None:
                raise LoginError('Cannot get access token. No device has been able to retrieve one!')
            if current_device is not None and current_can_login_until != current_device.can_login_until:
                await __db_try_update_device(current_device)
            return result


    def __fix_position(self) -> None:
        if self.__position is None or self.__position >= self.count:
            self.__position = 0


    def __select_next(self) -> None:
        count = self.count
        if count == 0:
            raise Exception('Cannot increase current position. There\'re no devices!')
        else:
            if self.__position is None:
                self.__position = 0
            else:
                self.__position = (self.__position + 1) % count






# ---------- Helper functions ----------

def __create_device_key() -> str:
    h = '0123456789abcdef'
    result = ''.join(
        random.choice(h)
        + random.choice('26ae')
        + random.choice(h)
        + random.choice(h)
        + random.choice(h)
        + random.choice(h)
        + random.choice(h)
        + random.choice(h)
        + random.choice(h)
        + random.choice(h)
        + random.choice(h)
        + random.choice(h)
    )
    return result


def __create_device_checksum(device_key: str, device_type: str) -> str:
    result = hashlib.md5((f'{device_key}{device_type}savysoda').encode('utf-8')).hexdigest()
    return result





# ---------- DB ----------

async def __db_get_device(device_key: str) -> Optional[Device]:
    query = f'SELECT * FROM devices WHERE key = $1'
    rows = await db.fetchall(query, [device_key])
    if rows:
        row = rows[0]
        result = Device(*row)
    else:
        result = None
    return result


async def __db_get_devices() -> List[Device]:
    query = f'SELECT * FROM devices;'
    rows = await db.fetchall(query)
    if rows:
        result = [Device(*row) for row in rows]
    else:
        result = []
    return result


async def __db_try_create_device(device: Device) -> bool:
    query = f'INSERT INTO devices VALUES ($1, $2, $3)'
    success = await db.try_execute(query, [device.key, device.checksum, device.can_login_until])
    return success


async def __db_try_delete_device(device: Device) -> bool:
    query = f'DELETE FROM devices WHERE key = $1'
    success = await db.try_execute(query, [device.key])
    return success


async def __db_try_store_device(device: Device) -> bool:
    current_device: Device = await __db_get_device(device.key)
    if current_device:
        success = await __db_try_update_device(device)
    else:
        success = await __db_try_create_device(device)
    return success


async def __db_try_update_device(device: Device) -> bool:
    query = f'UPDATE devices SET (key, checksum, loginuntil) = ($1, $2, $3) WHERE key = $1'
    success = await db.try_execute(query, [device.key, device.checksum, device.can_login_until])
    return success





# ---------- Initialization ----------

async def init() -> None:
    __devices = await __db_get_devices()
    global DEVICES
    DEVICES = DeviceCollection(__devices)