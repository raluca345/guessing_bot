import configparser
import logging
import os
import re
import time
from collections import defaultdict
from random import randint

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


def sanitize_file_name(file_name):
    """Remove or replace invalid characters in file names."""
    return re.sub(r'[<>:"/\\|?*]', '-', file_name)