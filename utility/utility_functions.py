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


def _get_filler_words() -> set[str]:
    """Return a set of filler words to exclude from token matching."""
    return {
        "ni", "no", "to", "wa", "ga", "o", "de", "kara", "made", "mo",
        "and", "the", "of", "a", "an", "in", "is", "are", "be", "by",
        "for", "on", "at", "with", "from", "as", "or", "but",
    }


def _normalize_for_comparison(text: str) -> str:
    """Normalize text by removing punctuation, lowercasing, and collapsing spaces.
    
    Preserves word boundaries for tokenization.
    """
    normalized = text.strip().lower()
    normalized = re.sub(pattern=PATTERN, string=normalized, repl=" ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _tokenize_normalized(text: str) -> set[str]:
    """Tokenize a normalized string and return meaningful tokens.
    
    Args:
        text: Normalized text (lowercase, punctuation removed)
    
    Returns:
        Set of meaningful tokens, with filler words removed
    """
    tokens = text.split()
    filler = _get_filler_words()
    return {t for t in tokens if t and t not in filler}


def sanitize_guess(raw_guess: str) -> str:
    """Sanitize a user's raw guess for character-by-character comparison.
    
    Removes special characters (?, !, ', etc.) and normalizes whitespace.
    """
    guessed = re.sub(pattern=PATTERN, string=raw_guess.strip().lower(), repl="")
    guessed = guessed.replace(" ", "")
    return guessed.strip()


def sanitize_aliases(aliases: list[str]) -> list[str]:
    """Sanitize song aliases for character-by-character comparison.
    
    Removes special characters and converts to lowercase.
    """
    return [re.sub(pattern=PATTERN, repl="", string=s.lower()).replace(" ", "") for s in aliases]


def guess_matches(raw_guess: str, romaji_name: str, aliases: list[str]) -> bool:
    """Check if a user's guess matches the song name or any alias.
    
    Supports multiple matching strategies in order of precision:
    1. Exact character match (after full sanitization) - most strict
    2. Token-based shorthand match - allows meaningful word subsets
    3. Paraphrase/semantic alias match - allows meaning-based guesses
    
    Examples:
    - "hoshi basho" matches "Hoshi ni Ichiban Chikai Basho" (shorthand)
    - "we are resonating" matches "we are resonating" alias (semantic)
    - "ready steady?" matches "Ready Steady" (exact, ignoring punctuation)
    
    Args:
        raw_guess: The raw user guess
        romaji_name: The canonical romaji name of the song
        aliases: List of aliases (including semantic paraphrases) for the song
    
    Returns:
        True if the guess matches via any strategy, False otherwise
    """
    # Strategy 1: Exact character match (existing behavior, most precise)
    # This handles punctuation variations and is the strict baseline
    guessed = sanitize_guess(raw_guess)
    clean_aliases = sanitize_aliases(aliases)
    
    if guessed == sanitize_guess(romaji_name) or guessed in clean_aliases:
        return True
    
    # Strategy 2: Token-based shorthand match
    # Allows players to guess with a subset of meaningful words
    # Example: "hoshi basho" for "Hoshi ni Ichiban Chikai Basho"
    guess_normalized = _normalize_for_comparison(raw_guess)
    guess_tokens = _tokenize_normalized(guess_normalized)
    
    if len(guess_tokens) == 0:
        return False
    
    # Only apply token matching for meaningful guesses:
    # - 2+ tokens (e.g., "hoshi basho"), OR
    # - 1 token that's at least 4 chars (e.g., "blade", "resonance")
    # Note: Single-word tokens are already filtered for filler words
    if len(guess_tokens) >= 2 or (len(guess_tokens) == 1 and len(list(guess_tokens)[0]) >= 4):
        # Try to match against title tokens
        title_normalized = _normalize_for_comparison(romaji_name)
        title_tokens = _tokenize_normalized(title_normalized)
        
        # Accept if all guess tokens appear in title tokens (subset match)
        if guess_tokens.issubset(title_tokens):
            return True
        
        # Try matching against alias tokens (covers semantic paraphrases)
        for alias in aliases:
            alias_normalized = _normalize_for_comparison(alias)
            alias_tokens = _tokenize_normalized(alias_normalized)
            
            if guess_tokens.issubset(alias_tokens):
                return True
    
    return False


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
