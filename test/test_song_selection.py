"""Test that random song selection is uniformly distributed."""

import random
from collections import Counter

import pytest
from scipy import stats

from utility.filters import filter_songs_by_unit


def _make_song(song_id: int, name: str, unit: str = "Leo/need") -> dict:
    """Create a minimal in-memory song record."""
    return {
        "id": song_id,
        "romaji_name": name,
        "aliases": [name.lower()],
        "unit": unit,
        "english_lyrics": ["line1"],
        "kanji_lyrics": ["line1"],
        "romaji_lyrics": ["line1"],
    }


# Build a fake song database with 20 songs spread across units
SONG_DB = [
    _make_song(1, "Song A", "Leo/need"),
    _make_song(2, "Song B", "Leo/need"),
    _make_song(3, "Song C", "Leo/need"),
    _make_song(4, "Song D", "Leo/need"),
    _make_song(5, "Song E", "MORE MORE JUMP!"),
    _make_song(6, "Song F", "MORE MORE JUMP!"),
    _make_song(7, "Song G", "MORE MORE JUMP!"),
    _make_song(8, "Song H", "Vivid BAD SQUAD"),
    _make_song(9, "Song I", "Vivid BAD SQUAD"),
    _make_song(10, "Song J", "Vivid BAD SQUAD"),
    _make_song(11, "Song K", "Wonderlands × Showtime"),
    _make_song(12, "Song L", "Wonderlands × Showtime"),
    _make_song(13, "Song M", "25-ji, Nightcord de."),
    _make_song(14, "Song N", "25-ji, Nightcord de."),
    _make_song(15, "Song O", "25-ji, Nightcord de."),
    _make_song(16, "Song P", "VIRTUAL SINGER"),
    _make_song(17, "Song Q", "VIRTUAL SINGER"),
    _make_song(18, "Song R", "VIRTUAL SINGER"),
    _make_song(19, "Song S", "VIRTUAL SINGER"),
    _make_song(20, "Song T", "Other"),
]

PICKS = 1000
# Significance level for the chi-squared test (α = 0.01 to avoid flaky failures)
ALPHA = 0.01


class TestSongSelectionUniformity:
    """Verify that random.choice produces a roughly uniform distribution."""

    @staticmethod
    def _pick_songs(pool: list[dict], n: int) -> Counter:
        """Pick n songs from pool using random.choice and return counts."""
        return Counter(random.choice(pool)["romaji_name"] for _ in range(n))

    @staticmethod
    def _assert_uniform(counts: Counter, pool_size: int, n: int):
        """Run a chi-squared goodness-of-fit test for uniformity.

        H0: all songs are equally likely.
        Reject H0 if p-value < ALPHA.
        """
        expected = n / pool_size
        observed = [counts.get(name, 0) for name in sorted(counts)]
        chi2, p_value = stats.chisquare(observed)
        assert p_value >= ALPHA, (
            f"Distribution is NOT uniform (chi2={chi2:.2f}, p={p_value:.4f}). "
            f"Expected ~{expected:.1f} per song, got: "
            + ", ".join(f"{k}: {v}" for k, v in counts.most_common())
        )

    def test_all_songs_uniform(self):
        """Picking from all 20 songs should be uniform."""
        pool = filter_songs_by_unit(SONG_DB, "None")
        assert len(pool) == 20
        counts = self._pick_songs(pool, PICKS)
        self._assert_uniform(counts, len(pool), PICKS)

    def test_leoneed_uniform(self):
        """Picking from Leo/need (4 songs) should be uniform."""
        pool = filter_songs_by_unit(SONG_DB, "Leo/need")
        assert len(pool) == 4
        counts = self._pick_songs(pool, PICKS)
        self._assert_uniform(counts, len(pool), PICKS)

    def test_mmj_uniform(self):
        """Picking from MORE MORE JUMP! (3 songs) should be uniform."""
        pool = filter_songs_by_unit(SONG_DB, "MORE MORE JUMP!")
        assert len(pool) == 3
        counts = self._pick_songs(pool, PICKS)
        self._assert_uniform(counts, len(pool), PICKS)

    def test_vbs_uniform(self):
        """Picking from Vivid BAD SQUAD (3 songs) should be uniform."""
        pool = filter_songs_by_unit(SONG_DB, "Vivid BAD SQUAD")
        assert len(pool) == 3
        counts = self._pick_songs(pool, PICKS)
        self._assert_uniform(counts, len(pool), PICKS)

    def test_nightcord_uniform(self):
        """Picking from 25-ji, Nightcord de. (3 songs) should be uniform."""
        pool = filter_songs_by_unit(SONG_DB, "25-ji, Nightcord de.")
        assert len(pool) == 3
        counts = self._pick_songs(pool, PICKS)
        self._assert_uniform(counts, len(pool), PICKS)

    def test_every_song_picked_at_least_once(self):
        """With 1000 picks from 20 songs, every song should appear."""
        pool = filter_songs_by_unit(SONG_DB, "None")
        counts = self._pick_songs(pool, PICKS)
        missing = [s["romaji_name"] for s in pool if s["romaji_name"] not in counts]
        assert not missing, f"Songs never picked: {missing}"

    def test_single_song_unit(self):
        """A unit with 1 song should always return that song."""
        pool = filter_songs_by_unit(SONG_DB, "Other")
        assert len(pool) == 1
        counts = self._pick_songs(pool, PICKS)
        assert counts["Song T"] == PICKS
