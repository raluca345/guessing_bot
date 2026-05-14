"""Card and song filtering utilities with caching."""
from utility.constants import (
    SECOND_ANNI, THIRD_ANNI, FOURTH_ANNI, FIFTH_ANNI, SIXTH_ANNI,
    SANRIO_CARDS_IDS, ENSTARS_CARDS_IDS, TAMAGOTCHI_CARDS_IDS,
    TOUHOU_MIKU_ID, EVILLIOUS_CARDS_IDS, MOVIE_CARDS_IDS,
    UNITS, unit_aliases, character_id_to_unit
)


# Song caching
song_unit_cache = {}


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
    """Clear the card filter cache."""
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
