from xml.etree import ElementTree as ET
import requests
import numpy as np
from PIL import Image, ImageDraw
import uuid
import hashlib
from io import BytesIO
import os.path

PSS_API_SERVER = "api.pixelstarships.com"

CACHED = True # run the update_cache.py script first!
PATH_CACHE = "Cache"
USER_ID = 3626318 # Canto de Ossanha

if CACHED and not os.path.isdir(PATH_CACHE):
    print("Check the path of your cache folder or run update_cache.py")
    exit()
    
# Login method used for the inspect ship requests
def login(api_server: str, ) -> str:
    device_key: str = uuid.uuid1().hex[0:16]
    device_type: str = 'DeviceTypeMac'  
    checksum = hashlib.md5((f'{device_key}{device_type}savysoda').encode('utf-8')).hexdigest()
    params = {
        'advertisingKey': '""', 'checksum': checksum,
        'deviceKey': device_key, 'deviceType': device_type,
        'isJailBroken': 'false', 'languageKey': 'en'
    }
    url = f'https://{api_server}/UserService/DeviceLogin8'
    data = requests.post(url, params=params).content.decode('utf-8')
    dataxml = ET.fromstring(data)
    access_token = dataxml.find('UserLogin').attrib['accessToken']
    return access_token

# Retrieve list of sprites
if CACHED:
    file = open(os.path.join(PATH_CACHE,"ListSprites2.xml"), encoding="utf-8")
    data_sprites = file.read()
else:
    request = requests.get('https://api.pixelstarships.com/FileService/ListSprites2')
    request.encoding = 'UTF-8'
    data_sprites = request.text
tree_sprites = ET.fromstring(data_sprites)

# Retrieve list of ships designs
if CACHED:
    file = open(os.path.join(PATH_CACHE,"ListAllShipDesigns2.xml"), encoding="utf-8")
    data_ships = file.read()
else:
    request = requests.get(f'https://{PSS_API_SERVER}/ShipService/ListAllShipDesigns2', params={'languageKey': 'en'})
    request.encoding = 'UTF-8'
    data_ships = request.text
tree_ships = ET.fromstring(data_ships)

# Retrieve list of rooms designs
if CACHED:
    file = open(os.path.join(PATH_CACHE,"ListRoomDesigns2.xml"), encoding="utf-8")
    data_rooms = file.read()
else:
    request = requests.get(f'https://{PSS_API_SERVER}/RoomService/ListRoomDesigns2', params={'languageKey': 'en'})
    request.encoding = 'UTF-8'
    data_rooms = request.text
tree_rooms = ET.fromstring(data_rooms)

access_token = login(PSS_API_SERVER)

# Retrieve user data

params = {'userId': USER_ID, 'accessToken': access_token}
request = requests.get(f'https://{PSS_API_SERVER}/ShipService/InspectShip2', params)
request.encoding = 'UTF-8'
data = request.text
tree = ET.fromstring(data)

ship_design_id = tree.find('.//Ship').get('ShipDesignId')
sprite_id = tree_ships.find(f".//ShipDesign[@ShipDesignId='{ship_design_id}']").get('InteriorSpriteId')
image_id = tree_sprites.find(f".//Sprite[@SpriteId='{sprite_id}']").get('ImageFileId')

if CACHED:
    img = Image.open(os.path.join(PATH_CACHE,f"{image_id}.png")).convert("RGBA")
else:
    request = requests.get(f'http://datxcu1rnppcg.cloudfront.net/{image_id}.png')
    img = Image.open(BytesIO(request.content)).convert("RGBA")

for room in tree.findall('.//Ship/Rooms/Room'):
    # print(f"Room: {room.get('RoomDesignId')}")
    # print(tree_rooms.find(f".//RoomDesign[@RoomDesignId='{room.get('RoomDesignId')}']").get('RoomName'))
    room_design = tree_rooms.find(f".//RoomDesign[@RoomDesignId='{room.get('RoomDesignId')}']")
    sprite_id = room_design.get('ImageSpriteId')

    sprite = tree_sprites.find(f".//Sprite[@SpriteId='{sprite_id}']")
    image_id = tree_sprites.find(f".//Sprite[@SpriteId='{sprite_id}']").get('ImageFileId')
 
    if CACHED:
        img_room = Image.open(os.path.join(PATH_CACHE,f"{image_id}.png")).convert("RGBA")
    else:
        request = requests.get(f'http://datxcu1rnppcg.cloudfront.net/{image_id}.png')
        img_room = Image.open(BytesIO(request.content)).convert("RGBA")
    
    origin_x,origin_y = int(sprite.get('X')),int(sprite.get('Y'))
    offset_x,offset_y = origin_x+int(sprite.get('Width')),origin_y+int(sprite.get('Height'))

    img_crop = img_room.crop([origin_x,origin_y,offset_x,offset_y])
    img.paste(img_crop,(int(room.get('Column'))*25,int(room.get('Row'))*25))

img.show()
img.save(f"{USER_ID}_layout.png", "png")
