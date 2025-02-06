import configparser
import logging
import os
import time
from collections import defaultdict
from random import randint

import mysql.connector
from PIL import Image

# constants
# maybe move the constants to a separate file
SONG_JACKET_THUMBNAIL_SIZE = (200, 200)
CARD_CROP_SIZE = 250
SONG_JACKET_CROP_SIZE = 150
COMMANDS_PER_PAGE = 6
PATTERN = r'\W+'  # removes all characters that aren't letters or digits; should keep japanese or other languages charas
# wrong for now, change them later
WEEK_ANNOUNCEMENT_CHANNEL = 1186018902413680640
OTHER_ANNOUNCEMENT_CHANNEL = 1186018985947439174
CGL_TWT_ACC_ID = 1596219475019583488
CGL_SERVER_ID = 1074836992384303114
OWNER_ID = 599999906039726090
OWNER_SERVER_ID = 1076494695204659220

UNITS = ["None", "VIRTUAL SINGER", "Leo/need", "MORE MORE JUMP!", "Wonderlands × Showtime", "Vivid BAD SQUAD",
         "25-ji, Nightcord de.", "Other"]
character_id_to_unit = {
    "Leo/need": [1, 2, 3, 4],
    "MORE MORE JUMP!": [5, 6, 7, 8],
    "Vivid BAD SQUAD": [9, 10, 11, 12],
    "Wonderlands × Showtime": [13, 14, 15, 16],
    "25-ji, Nightcord de.": [17, 18, 19, 20],
    "VIRTUAL SINGER": [21, 22, 23, 24, 25, 26]
}
# last is more for fun tbh
unit_aliases = [
    {
        "unit": UNITS[1],
        "aliases": ["virtual_singer", "vs", "virtual_singers", "vocaloid", "vocaloids", "cryptonloids"]
    },
    {
        "unit": UNITS[2],
        "aliases": ["leo/need", "ln", "l/n", "leoni", "leoneed", "leo_need", "band", "light_sound"]
    },
    {
        "unit": UNITS[3],
        "aliases": ["more_more_jump", "mmj", "moremorejump", "momojan", "idol"]
    },
    {
        "unit": UNITS[4],
        "aliases": ["wonderlands×showtime", "wxs", "wonderlandsxshowtime", "wonderlandxshowtime",
                    "wonderlandsshowtime", "wonderlandshowtime", "wandasho", "wonderlands",
                    "wonderland", "clowns", "theme_park"]
    },
    {
        "unit": UNITS[5],
        "aliases": ["vivid_bad_squad", "vbs", "bibibus", "bibibas", "vivid_squad",
                    "vivid_bad", "vividbadsquad", "street_music_group", "street"]
    },
    {
        "unit": UNITS[6],
        "aliases": ["25-ji,_nightcord_de.", "nightcord", "niigo", "25ji",
                    "nightcord_at_25jii", "nightcord_at_25", "music_circle", "school_refusal"]
    },
    {
        "unit": UNITS[7],
        "aliases": ["other", "others", "misc", "miscellaneous"]
    }
]
unit_aliases_list = [alias for unit_dict in unit_aliases for alias in
                     unit_dict["aliases"]]  # gets all aliases and also flattens the lists

FIRST_ANNI = 1632949200
SECOND_ANNI = 1664485200
THIRD_ANNI = 1696021200
FOURTH_ANNI = 1727643600
FIFTH_ANNI = 1759179600
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


def sanrio_filter(cards):
    filtered_cards = [c for c in cards if c["prefix"].strip().startswith("feat.")]
    return filtered_cards


def unit_filter(cards, unit):
    if unit == "None":
        return None
    filtered_cards = []

    unit_to_aliases = {u["unit"] : u["aliases"] for u in unit_aliases}

    # unit based filtering
    filtered_cards = [card for card in cards if card["character_id"] in character_id_to_unit[unit] or card["support_unit"] in unit_to_aliases[unit]]

    return filtered_cards
