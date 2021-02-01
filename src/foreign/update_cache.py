from xml.etree import ElementTree as ET
import requests
import numpy as np
from PIL import Image, ImageDraw
import uuid
import hashlib
from io import BytesIO
import os

PSS_API_SERVER = "api.pixelstarships.com"
ERASE_CONTENT = False
PATH_CACHE = "Cache"

if not os.path.isdir(PATH_CACHE):
    os.makedirs(PATH_CACHE)

# Retrieve list of sprites
request = requests.get(f'https://{PSS_API_SERVER}/FileService/ListSprites2')
request.encoding = 'UTF-8'
data_sprites = request.text
tree_sprites = ET.fromstring(data_sprites)
file = open(f"Cache/ListSprites2.xml", "w+", encoding="utf-8")
file.write(data_sprites)
file.close()

# Retrieve list of ship designs
request = requests.get(f'https://{PSS_API_SERVER}/ShipService/ListAllShipDesigns2', params={'languageKey': 'en'})
request.encoding = 'UTF-8'
data_ships = request.text
tree_ships = ET.fromstring(data_ships)
file = open(f"Cache/ListAllShipDesigns2.xml", "w+", encoding="utf-8")
file.write(data_ships)
file.close()

for ship in tree_ships.findall(".//ShipDesign"):
    sprite_id = ship.get('InteriorSpriteId')
    image_id = tree_sprites.find(f".//Sprite[@SpriteId='{sprite_id}']").get('ImageFileId')
    
    if ERASE_CONTENT or not os.path.isfile(f"Cache/{image_id}.png"):
        request = requests.get(f'http://datxcu1rnppcg.cloudfront.net/{image_id}.png')
        # img = Image.open(request.raw).convert("RGBA")
        img = Image.open(BytesIO(request.content)).convert("RGBA")
        print(f"Saving Cache/{image_id}.png ({ship.get('ShipDesignName')})")
        img.save(f"Cache/{image_id}.png", "png")


# Retrieve list of rooms
request = requests.get(f'https://{PSS_API_SERVER}/RoomService/ListRoomDesigns2', params={'languageKey': 'en'})
request.encoding = 'UTF-8'
data_rooms = request.text
tree_rooms = ET.fromstring(data_rooms)
file = open(f"Cache/ListRoomDesigns2.xml", "w+", encoding="utf-8")
file.write(data_rooms)
file.close()

for room in tree_rooms.findall(".//RoomDesign"):
    sprite_id = room.get('ImageSpriteId')
    image_id = tree_sprites.find(f".//Sprite[@SpriteId='{sprite_id}']").get('ImageFileId')

    request = requests.get(f'http://datxcu1rnppcg.cloudfront.net/{image_id}.png')
    # img = Image.open(request.raw).convert("RGBA")
    img = Image.open(BytesIO(request.content)).convert("RGBA")
    print(f"Saving Cache/{image_id}.png ({room.get('RoomName')})")
    img.save(f"Cache/{image_id}.png", "png")