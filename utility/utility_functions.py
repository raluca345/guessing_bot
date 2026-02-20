import configparser
import logging
import os
import re
import time
import numpy as np
from random import randrange, randint
from collections import defaultdict
from io import BytesIO

import mysql.connector
from PIL import Image
from dotenv import load_dotenv

from utility.constants import *
import boto3
from botocore.client import Config


# db configuration

config = configparser.ConfigParser()
config.read('config/config.ini')

# logger set up
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
datefmt = "%Y-%m-%d %H:%M"
formatter.datefmt = datefmt

# log to the console
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

# also log to a file
file_handler = logging.FileHandler(os.getcwd() + "/log/cpy-errors.log")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.ERROR)
logger.addHandler(file_handler)

# flag to check if a guessing session has already been started in the active channel
active_session = defaultdict(bool)

#dict of locks to prevent the active_session dict from not being updated to false at the end of a session
lock = {}

load_dotenv()

# r2 configuration
ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
BUCKET_NAME = os.getenv('BUCKET_NAME')
ENDPOINT_URL = os.getenv('ENDPOINT_URL')

def read_song_from_file(file_name):
    with open(file_name, "r") as f:
        lines = f.readlines()
        return lines


# high level method
def connect():
    config_db = {
        'user': config['mysqlDB']['user'],
        'password': config['mysqlDB']['pass'],
        'host': config['mysqlDB']['host'],
        'database': config['mysqlDB']['db']
    }
    return connect_to_db(config_db, attempts=3, delay=2)

def connect_to_r2_storage():
    s3 = boto3.client('s3',
                      endpoint_url=ENDPOINT_URL,
                      aws_access_key_id=ACCESS_KEY_ID,
                      aws_secret_access_key=SECRET_ACCESS_KEY,
                      config=Config(signature_version='s3v4'))
    return s3


def get_mask_from_r2(s3, bucket, mask_key):
    obj = s3.get_object(Bucket=bucket, Key=mask_key)
    return np.load(BytesIO(obj["Body"].read()))


# low level method
def connect_to_db(config, attempts=3, delay=2):
    attempt = 1
    # connection routine
    while attempt < attempts + 1:
        try:
            return mysql.connector.connect(**config, pool_name="pool", pool_size=5)
        except (mysql.connector.Error, IOError) as e:
            if attempts is attempt:
                # all attempts failed
                logger.error("Failed to connect, exiting without a connection: %s", e)
            logger.info(
                "Connection failed: %s. Retrying (%d/%d)...",
                e,
                attempt,
                attempts - 1,
            )
            # progressive reconnect delay
            time.sleep(delay ** attempt)
            attempt += 1
    return None



def generate_foreground_crop_from_mask(orig_img, alpha, crop_size, min_fg_ratio=0.12):
    width = orig_img.width
    height = orig_img.height

    # same guard idea as normal crop
    if crop_size >= width or crop_size >= height:
        return orig_img.copy()

    ys, xs = np.where(alpha > 0)

    # if mask failed → behave exactly like normal crop
    if len(xs) == 0:
        return generate_img_crop(orig_img, crop_size)

    last_box = None
    for _ in range(4):  # try a few foreground-biased crops
        # pick a random foreground pixel as anchor
        i = randrange(len(xs))
        cx, cy = xs[i], ys[i]

        # convert center → top-left (like normal crop uses x1,y1)
        x1 = cx - crop_size // 2
        y1 = cy - crop_size // 2

        # clamp like bounds-safe random crop
        x1 = max(0, min(x1, width - crop_size))
        y1 = max(0, min(y1, height - crop_size))

        box = (x1, y1, x1 + crop_size, y1 + crop_size)
        last_box = box

        # foreground coverage check
        patch = alpha[y1:y1 + crop_size, x1:x1 + crop_size]
        if (patch > 0).mean() >= min_fg_ratio:
            return orig_img.crop(box)

    # fallback → return the last generated crop
    if last_box is not None:
        return orig_img.crop(last_box)
    return generate_img_crop(orig_img, crop_size)




def generate_img_crop(img: Image.Image, crop_size):
    width = img.width
    height = img.height
    x1 = randint(0, width - crop_size - 1)
    y1 = randint(0, height - crop_size - 1)
    box = (x1, y1, x1 + crop_size, y1 + crop_size)
    return img.crop(box)


def four_star_filter(cards):
    filtered_cards = [c for c in cards if c["card_rarity_type"] == "rarity_4"]
    return filtered_cards


def three_star_filter(cards):
    filtered_cards = [c for c in cards if c["card_rarity_type"] == "rarity_3"]
    return filtered_cards


def no_two_star_filter(cards):
    filtered_cards = [c for c in cards if c["card_rarity_type"] != "rarity_2"]
    return filtered_cards


def two_star_filter(cards):
    filtered_cards = [c for c in cards if c["card_rarity_type"] == "rarity_2"]
    return filtered_cards


def birthday_filter(cards):
    filtered_cards = [c for c in cards if c["card_rarity_type"] == "rarity_birthday"]
    return filtered_cards


def birthday1_filter(cards):
    filtered_cards = [c for c in cards if
                      c["card_rarity_type"] == "rarity_birthday" and c["release_at"] < SECOND_ANNI * 1000]
    return filtered_cards


def birthday2_filter(cards):
    filtered_cards = [c for c in cards if
                      c["card_rarity_type"] == "rarity_birthday" and THIRD_ANNI * 1000 > c["release_at"] > SECOND_ANNI * 1000]
    return filtered_cards


def birthday3_filter(cards):
    filtered_cards = [c for c in cards if
                      c["card_rarity_type"] == "rarity_birthday" and FOURTH_ANNI * 1000 > c["release_at"] > THIRD_ANNI * 1000]
    return filtered_cards


def birthday4_filter(cards):
    filtered_cards = [c for c in cards if
                      c["card_rarity_type"] == "rarity_birthday" and FIFTH_ANNI * 1000 > c["release_at"] > FOURTH_ANNI * 1000]
    return filtered_cards

def birthday5_filter(cards):
    filtered_cards = [c for c in cards if
                      c["card_rarity_type"] == "rarity_birthday" and SIXTH_ANNI * 1000 > c["release_at"] > FIFTH_ANNI * 1000]
    return filtered_cards


def sanrio_filter(cards):
    filtered_cards = [c for c in cards if c["id"] in SANRIO_CARDS_IDS]
    return filtered_cards


def enstars_filter(cards):
    filtered_cards = [c for c in cards if c["id"] in ENSTARS_CARDS_IDS]
    return filtered_cards


def tamagotchi_filter(cards):
    filtered_cards = [c for c in cards if c["id"] in TAMAGOTCHI_CARDS_IDS]
    return filtered_cards


def touhou_miku(cards):
    filtered_cards = [c for c in cards if c["id"] == TOUHOU_MIKU_ID]
    return filtered_cards


def evillious_filter(cards):
    filtered_cards = [c for c in cards if c["id"] in EVILLIOUS_CARDS_IDS]
    return filtered_cards


def collab_filter(cards):
    filtered_cards = sanrio_filter(cards) + enstars_filter(cards) + tamagotchi_filter(cards) + touhou_miku(cards) + evillious_filter(cards)
    return filtered_cards


def movie_filter(cards):
    filtered_cards = [c for c in cards if c["id"] in MOVIE_CARDS_IDS]
    return filtered_cards


def unit_filter(cards, unit):
    if unit == "None":
        return None
    try:
        unit_to_aliases = {u["unit"]: set(u["aliases"]) for u in unit_aliases}
    except Exception:
        unit_to_aliases = {}

    aliases_set = unit_to_aliases.get(unit, set())
    char_id_list = character_id_to_unit.get(unit, [])
    char_id_set = set(char_id_list)

    filtered_cards = [
        card for card in cards
        if card.get("character_id") in char_id_set or card.get("support_unit") in aliases_set
    ]

    return filtered_cards


def sanitize_file_name(file_name):
    """Remove or replace invalid characters in file names."""
    return re.sub(r'[<>:"/\\|?*]', '-', file_name)


song_unit_cache = {}
mask_cache = {}


def build_song_unit_cache(songs):
    """Precompute and store filtered song lists for each unit."""
    global song_unit_cache
    song_unit_cache = {}
    try:
        for u in UNITS:
                if u == "None":
                    song_unit_cache[u] = list(songs)
                else:
                    song_unit_cache[u] = [s for s in songs if s.get("unit") == u]
        pass
    except Exception:
        song_unit_cache = {"None": list(songs)}
    return song_unit_cache


def clear_song_unit_cache():
    """Clear the precomputed cache.

    Use this before rebuilding or if you need to force recomputation.
    """
    global song_unit_cache
    song_unit_cache.clear()



def filter_songs_by_unit(songs, unit):
    """Return a list of songs filtered by `unit`, using cache if available.

    If the cache is empty, this will compute the filtered list on-the-fly
    (so callers still work before cache build).
    """
    if song_unit_cache:
        cached = song_unit_cache.get(unit)
        if cached is not None:
            return list(cached)
    if unit == "None":
        return list(songs)
    computed = [s for s in songs if s.get("unit") == unit]
    return computed


# Card filter cache and helpers
card_filter_cache = {}


def build_card_filter_cache(cards):
    """Precompute and store commonly used card filter lists.

    Cached keys:
    - 'four_star', 'three_star', 'two_star', 'no_two_star', 'sanrio'
    - 'birthday', 'birthday1'..'birthday5'
    - 'unit:{unit}' for each unit in UNITS
    """
    global card_filter_cache
    card_filter_cache = {}
    try:
        card_filter_cache['four_star'] = four_star_filter(cards)
        card_filter_cache['three_star'] = three_star_filter(cards)
        card_filter_cache['two_star'] = two_star_filter(cards)
        card_filter_cache['no_two_star'] = no_two_star_filter(cards)
        card_filter_cache['sanrio'] = sanrio_filter(cards)
        card_filter_cache['tamagotchi'] = tamagotchi_filter(cards)
        card_filter_cache['collab'] = collab_filter(cards)
        card_filter_cache['movie'] = movie_filter(cards)

        card_filter_cache['birthday'] = birthday_filter(cards)
        card_filter_cache['birthday1'] = birthday1_filter(cards)
        card_filter_cache['birthday2'] = birthday2_filter(cards)
        card_filter_cache['birthday3'] = birthday3_filter(cards)
        card_filter_cache['birthday4'] = birthday4_filter(cards)
        card_filter_cache['birthday5'] = birthday5_filter(cards)

        try:
            for u in UNITS:
                key = f"unit:{u}"
                if u == "None":
                    card_filter_cache[key] = list(cards)
                else:
                    # unit_filter already returns None for "None" unit, or a filtered list
                    filtered = unit_filter(cards, u) or list(cards)
                    card_filter_cache[key] = filtered
        except Exception:
            pass
    except Exception:
        card_filter_cache = {}
    return card_filter_cache


def clear_card_filter_cache():
    global card_filter_cache
    card_filter_cache.clear()




def get_cached_card_filter(name, cards=None):
    """Return cached filtered card list by name, or compute on-the-fly if cache missing.

    `name` examples: 'four_star', 'birthday2', 'unit:MyUnit'
    """
    if card_filter_cache:
        res = card_filter_cache.get(name)
        if res is not None:
            return list(res)
    # Fallbacks: compute using existing filter functions if available
    if cards is None:
        return []
    if name == 'four_star':
        return four_star_filter(cards)
    if name == 'three_star':
        return three_star_filter(cards)
    if name == 'two_star':
        return two_star_filter(cards)
    if name == 'no_two_star':
        return no_two_star_filter(cards)
    if name == 'sanrio':
        return sanrio_filter(cards)
    if name == 'birthday':
        return birthday_filter(cards)
    if name.startswith('birthday') and name[8:].isdigit():
        idx = name[8:]
        func = globals().get(f'birthday{idx}_filter')
        if callable(func):
            return func(cards)
        return []
    if name.startswith('unit:'):
        unit = name.split(':', 1)[1]
        return unit_filter(cards, unit) or list(cards)
    if name == 'tamagotchi':
        return tamagotchi_filter(cards)
    if name == 'collab':
        return collab_filter(cards)
    if name == 'movie':
        return movie_filter(cards)
    return []