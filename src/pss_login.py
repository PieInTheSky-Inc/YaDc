import datetime
import hashlib
import random
import requests
from threading import Lock
from typing import List

import pss_core as core
import utility as util










# ---------- Constants & Internals ----------

FIVE_MINUTES: datetime.timedelta = datetime.timedelta(seconds=299)
FIFTEEN_HOURS: datetime.timedelta = datetime.timedelta(hours=15)
ONE_DAY: datetime.timedelta = datetime.timedelta(days=1)

DEVICES: 'DeviceCollection' = None










# ---------- Classes ----------

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

class Device():
    def __init__(self, device_key: str, checksum: str = None, can_login_until: datetime.datetime = None):
        self.__key: str = device_key
        self.__checksum: str = checksum or create_device_checksum(device_key)
        self.__last_login: datetime.datetime = None
        self.__can_login_until: datetime.datetime = can_login_until
        self.__access_token: str = None
        self.__access_token_expires_at: datetime.datetime = None
        self.__set_access_token_expiry()
        self.__user: dict = None
        self.__token_lock: Lock = Lock()


    @property
    def access_token_expired(self) -> bool:
        if self.__access_token:
            return self.__access_token_expires_at < util.get_utcnow()
        return True

    @property
    def can_login(self) -> bool:
        if self.__can_login_until is None:
            return True
        utc_now = util.get_utcnow()
        if self.__can_login_until <= utc_now and self.__can_login_until.day == utc_now.day:
            return False
        return True

    @property
    def can_login_until(self) -> datetime.datetime:
        return self.__can_login_until

    @property
    def checksum(self) -> str:
        return self.__checksum

    @property
    def key(self) -> str:
        return self.__key


    def get_access_token(self) -> str:
        """
        Returns a valid access token. If there's no valid access token related to this Device, this method will attempt to log in and retrieve an access token via the PSS API.
        """
        with self.__token_lock:
            if self.access_token_expired:
                if self.can_login:
                    self.__login()
                else:
                    raise LoginError('Cannot login currently. Please try again later.')
        return self.__access_token


    def __login(self) -> None:
        utc_now = util.get_utcnow()
        if not self.__key:
            self.__key = create_device_key()
        if not self.__checksum:
            self.__checksum = create_device_checksum(self.__key)

        production_server = core.get_production_server()
        url = f'https://{production_server}/UserService/DeviceLogin8?deviceKey={self.__key}&isJailBroken=false&checksum={self.__checksum}&deviceType=DeviceTypeMac&languageKey=en&advertisingkey=%22%22'
        utc_now = util.get_utcnow()
        data = requests.post(url).content.decode('utf-8')
        result = core.convert_raw_xml_to_dict(data)
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
            self.__access_token_expires_at = self.__last_login + FIVE_MINUTES
        else:
            self.__access_token_expires_at = None


    def __set_can_login_until(self, last_login: datetime.datetime) -> None:
        if not self.__can_login_until or last_login > self.__can_login_until:
            next_day = util.get_next_day(self.__can_login_until)
            login_until = last_login + FIFTEEN_HOURS
            self.__can_login_until = min(login_until, next_day)










class DeviceCollection():
    def __init__(self, devices: List[Device] = None):
        self.__devices: List[Device] = devices or []
        self.__position: int = None
        self.__fix_position()
        self.__token_lock: Lock = Lock()


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


    def add_device(self, device: Device) -> None:
        for existing_device in self.__devices:
            if existing_device.key == device.key:
                return
        db_try_store_device(device)
        self.__devices.append(device)
        self.__fix_position()
        # TODO: select added device


    def add_devices(self, devices: List[Device]) -> None:
        for device in devices:
            self.add_device(device)


    def add_device_by_key(self, device_key: str) -> Device:
        for existing_device in self.__devices:
            if existing_device.key == device_key:
                return
        device = Device(device_key)
        db_try_store_device(device)
        self.__devices.append(device)
        self.__fix_position()
        return device


    def create_device(self) -> Device:
        device = Device(create_device_key())
        self.add_device(device)
        return device


    def remove_device(self, device: Device) -> None:
        self.remove_device_by_key(device.key)


    def remove_device_by_key(self, device_key: str) -> None:
        if self.count == 0:
            raise Exception('Cannot remove device. There\'re no devices!')
        for existing_device in self.__devices:
            if existing_device.key == device_key:
                db_try_delete_device(existing_device)
                self.__devices = [device for device in self.__devices if device.key != device_key]
                self.__fix_position()
                return
        raise Exception('Cannot remove device. A device with the specified key does not exist!')


    def select_device(self, device_key: str) -> Device:
        if self.count == 0:
            raise Exception('Cannot select a device. There\'re no devices!')
        for i, device in enumerate(self.__devices):
            if device_key == device.key:
                self.__position = i
                return device
        raise Exception(f'Could not find device with key \'{device_key}\'')



    def get_access_token(self) -> str:
        with self.__token_lock:
            if self.count == 0:
                raise Exception('Cannot get access token. There\'re no devices!')
            result: str = None
            current: Device = None
            tried_devices: int = 0
            while tried_devices < self.count:
                current = self.current
                try:
                    tried_devices += 1
                    result = current.get_access_token()
                    break
                except DeviceInUseError:
                    self.remove_device(current)
                except Exception as err:
                    print(f'[DeviceCollection.get_access_token] Could not log in:\n{err}')
                    self.__select_next()
                current = self.current
            if result is None:
                raise LoginError('Cannot get access token. No device has been able to retrieve one!')
            if current is not None:
                _db_try_update_device(current)
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











# ---------- Static functions ----------

def create_device_key() -> str:
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


def create_device_checksum(device_key: str) -> str:
    result = hashlib.md5((f'{device_key}DeviceTypeMacsavysoda').encode('utf-8')).hexdigest()
    return result










# ---------- DB ----------

def _db_get_device(device_key: str) -> Device:
    where = util.db_get_where_string('key', device_key, is_text_type=True)
    query = f'SELECT * FROM devices WHERE {where}'
    rows = core.db_fetchall(query)
    if rows:
        row = rows[0]
        result = Device(*row)
    else:
        result: Device = None
    return result


def db_get_devices() -> List[Device]:
    query = f'SELECT * FROM devices;'
    rows = core.db_fetchall(query)
    if rows:
        result = [Device(*row) for row in rows]
    else:
        result = []
    return result


def _db_try_create_device(device: Device) -> bool:
    db_key = util.db_convert_text(device.key)
    db_checksum = util.db_convert_text(device.checksum)
    db_login_until = util.db_convert_timestamp(device.can_login_until)
    query = f'INSERT INTO devices VALUES ({db_key}, {db_checksum}, {db_login_until})'
    success = core.db_try_execute(query)
    if success:
        DEVICES.add_device_by_key(device.key)
    return success


def db_try_delete_device(device: Device) -> bool:
    where = util.db_get_where_string('key', device.key, is_text_type=True)
    query = f'DELETE FROM devices WHERE {where}'
    success = core.db_try_execute(query)
    if success:
        DEVICES.remove_device_by_key(device.key)
    return success


def db_try_store_device(device: Device) -> bool:
    current_device: Device = _db_get_device(device.key)
    if current_device:
        success = _db_try_update_device(device)
    else:
        success = _db_try_create_device(device)
    return success


def _db_try_update_device(device: Device) -> bool:
    key = util.db_convert_text(device.key)
    checksum = util.db_convert_text(device.checksum)
    can_login_until = util.db_convert_timestamp(device.can_login_until)
    where = util.db_get_where_string('key', device.key, is_text_type=True)
    query = f'UPDATE devices SET (key, checksum, loginuntil) = ({key}, {checksum}, {can_login_until}) WHERE {where}'
    success = core.db_try_execute(query)
    return success










# ---------- Initialization ----------

def init():
    __devices = db_get_devices()
    global DEVICES
    DEVICES = DeviceCollection(__devices)