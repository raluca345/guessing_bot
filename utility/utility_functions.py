"""Core utility functions and logging setup."""
import configparser
import logging
import os
import re
from collections import defaultdict

from utility.constants import PATTERN

# Logger setup
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

# DB configuration
config = configparser.ConfigParser()
config.read('config/config.ini')

# Active session state
active_session = defaultdict(bool)
lock = {}


def get_active_session_lock(channel_id: int):
    """Get or create an asyncio Lock for a channel."""
    import asyncio
    existing = lock.get(channel_id)
    if existing is None:
        existing = asyncio.Lock()
        lock[channel_id] = existing
    return existing



def sanitize_file_name(file_name):
    """Remove or replace invalid characters in file names."""
    return re.sub(r'[<>:"/\\|?*]', '-', file_name)


def sanitize_guess(raw_guess: str) -> str:
    """Sanitize a user's raw guess for comparison.
    
    Removes special characters (?, !, ', etc.) and normalizes whitespace.
    """
    guessed = re.sub(pattern=PATTERN, string=raw_guess.strip().lower(), repl="")
    guessed = guessed.replace(" ", "")
    return guessed.strip()


def sanitize_aliases(aliases: list[str]) -> list[str]:
    """Sanitize song aliases for comparison.
    
    Removes special characters and converts to lowercase.
    """
    return [re.sub(pattern=PATTERN, repl="", string=s.lower()) for s in aliases]


def guess_matches(raw_guess: str, romaji_name: str, aliases: list[str]) -> bool:
    """Check if a user's guess matches the song name or any alias.
    
    Args:
        raw_guess: The raw user guess
        romaji_name: The canonical romaji name of the song
        aliases: List of aliases for the song
    
    Returns:
        True if the guess matches the song name or an alias (after sanitization)
    """
    guessed = sanitize_guess(raw_guess)
    clean_aliases = sanitize_aliases(aliases)
    return guessed in clean_aliases or guessed == romaji_name.lower()


def find_wrong_but_valid(raw_guess: str, song_pool: list) -> str | None:
    """Find if a guess matches another song in a pool.

    Useful for providing hints to the player when they guess a song name
    that exists in the pool but isn't the target song.

    Args:
        raw_guess: The raw user guess
        song_pool: List of song objects with romaji_name and aliases attributes

    Returns:
        The romaji_name of the matched song if found, None otherwise
    """
    return next(
        (
            s.romaji_name
            for s in song_pool
            if guess_matches(raw_guess, s.romaji_name, s.aliases)
        ),
        None,
    )
