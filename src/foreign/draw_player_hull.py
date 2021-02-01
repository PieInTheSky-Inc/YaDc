from xml.etree import ElementTree as ET
import requests
import numpy as np
from PIL import Image, ImageDraw
import uuid
import hashlib
from io import BytesIO

PSS_API_SERVER = "api.pixelstarships.com"

def create_device_checksum(device_key: str, device_type: str) -> str:
    result = hashlib.md5(
        (f'{device_key}{device_type}savysoda').encode('utf-8')).hexdigest()
    return result


def create_device_key() -> str:
    device_id = uuid.uuid1()
    result = device_id.hex[0:16]
    return result


def login(api_server: str, device_key: str = None, device_type: str = 'DeviceTypeMac') -> str:
    if not api_server:
        raise ValueError(
            'parameter \'api_server\' must neither be None nor empty.')
    if not device_key:
        device_key: str = create_device_key()

    params = {
        'advertisingKey': '""',
        'checksum': create_device_checksum(device_key, device_type),
        'deviceKey': device_key,
        'deviceType': device_type,
        'isJailBroken': 'false',
        'languageKey': 'en'
    }
    url = f'https://{PSS_API_SERVER}/UserService/DeviceLogin8'
    data = requests.post(url, params=params).content.decode('utf-8')
    dataxml = ET.fromstring(data)

    access_token = dataxml.find('UserLogin').attrib['accessToken']
    return access_token

# Retrieve ship designs
request = requests.get('https://api.pixelstarships.com/FileService/ListSprites2')
request.encoding = 'UTF-8'
data_sprites = request.text
tree_sprites = ET.fromstring(data_sprites)

# Retrieve list of sprites
request = requests.get(f'https://{PSS_API_SERVER}/ShipService/ListAllShipDesigns2', params={'languageKey': 'en'})
request.encoding = 'UTF-8'
data_designs = request.text
tree_designs = ET.fromstring(data_designs)

# Retrieve list of rooms
request = requests.get(f'https://{PSS_API_SERVER}/RoomService/ListRoomDesigns2', params={'languageKey': 'en'})
request.encoding = 'UTF-8'
data_rooms = request.text
tree_rooms = ET.fromstring(data_rooms)

access_token = login(PSS_API_SERVER)

# Retrieve user data
user_id = 3626318 # Canto de Ossanha
params = {'userId': user_id, 'accessToken': access_token}
request = requests.get(
    f'https://{PSS_API_SERVER}/ShipService/InspectShip2', params)
request.encoding = 'UTF-8'
data = request.text
tree = ET.fromstring(data)

# print(f"Parsing user {user.get('Name')}")

ship_design_id = tree.find('.//Ship').get('ShipDesignId')

sprite_id = tree_designs.find(f".//ShipDesign[@ShipDesignId='{ship_design_id}']").get('InteriorSpriteId')
image_id = tree_sprites.find(f".//Sprite[@SpriteId='{sprite_id}']").get('ImageFileId')

request = requests.get(f'http://datxcu1rnppcg.cloudfront.net/{image_id}.png')
# img = Image.open(request.raw).convert("RGBA")
img = Image.open(BytesIO(request.content)).convert("RGBA")

for room in tree.findall('.//Ship/Rooms/Room'):
    print(f"Room: {room.get('RoomDesignId')}")
    print(tree_rooms.find(f".//RoomDesign[@RoomDesignId='{room.get('RoomDesignId')}']").get('RoomName'))
    
    room_design = tree_rooms.find(f".//RoomDesign[@RoomDesignId='{room.get('RoomDesignId')}']")
    sprite_id = room_design.get('ImageSpriteId')

    sprite = tree_sprites.find(f".//Sprite[@SpriteId='{sprite_id}']")
    image_id = tree_sprites.find(f".//Sprite[@SpriteId='{sprite_id}']").get('ImageFileId')
 
    request = requests.get(f'http://datxcu1rnppcg.cloudfront.net/{image_id}.png')
    img_room = Image.open(BytesIO(request.content)).convert("RGBA")
    
    origin_x,origin_y = int(sprite.get('X')),int(sprite.get('Y'))
    offset_x,offset_y = origin_x+int(sprite.get('Width')),origin_y+int(sprite.get('Height'))

    img_crop = img_room.crop([origin_x,origin_y,offset_x,offset_y])
    img.paste(img_crop,(int(room.get('Column'))*25,int(room.get('Row'))*25))

img.show()
# img.save(f"{ship_design_id}_overlay.png", "png")
