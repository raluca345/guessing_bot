"""Card and song filtering utilities."""
from utility.constants import (
    SECOND_ANNI, THIRD_ANNI, FOURTH_ANNI, FIFTH_ANNI, SIXTH_ANNI,
    SANRIO_CARDS_IDS, ENSTARS_CARDS_IDS, TAMAGOTCHI_CARDS_IDS,
    TOUHOU_MIKU_ID, EVILLIOUS_CARDS_IDS, MOVIE_CARDS_IDS,
    unit_aliases, character_id_to_unit
)

def filter_songs_by_unit(songs, unit):
    """Return songs filtered by unit."""
    if unit == "None":
        return list(songs)
    def get_unit(song):
        return song.get("unit")
    return [s for s in songs if s["unit"] == unit]


# Card filters
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


def get_card_filter(name, cards):
    """Return filtered cards by filter `name` from the in-memory card list."""
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
