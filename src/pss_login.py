import hashlib
import random
import requests

import pss_core as core
import settings





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

def login(device_key: str = None) -> dict:
    if not device_key:
        device_key: str = create_device_key()

    checksum = create_device_checksum(device_key)

    production_server = core.get_production_server()
    path = f'UserService/DeviceLogin8?deviceKey={device_key}&isJailBroken=false&checksum={checksum}&deviceType=DeviceTypeMac&languageKey=en&advertisingkey=%22%22'
    url = f'https://{production_server}/{path}'
    data = requests.post(url).content.decode('utf-8')
    result = core.convert_raw_xml_to_dict(data)
    return device_key, result