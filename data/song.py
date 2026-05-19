from __future__ import annotations

from dataclasses import dataclass
import random

from utility.utility_functions import sanitize_aliases, sanitize_file_name


@dataclass(slots=True)
class Song:
    id: int
    romaji_name: str
    aliases: list[str]
    raw_aliases: list[str]
    unit: str
    english_lyrics: list[str]
    kanji_lyrics: list[str]
    romaji_lyrics: list[str]

    @classmethod
    def from_db_row(cls, row: dict) -> "Song":
        aliases_raw = (row.get("aliases") or "").split(";")
        raw_aliases = [a for a in aliases_raw if a]
        aliases = [a.lower() for a in raw_aliases]
        aliases.append(row["romaji_name"].lower())

        return cls(
            id=row["id"],
            romaji_name=row["romaji_name"],
            aliases=sanitize_aliases(aliases),
            raw_aliases=raw_aliases,
            unit=row["unit"],
            english_lyrics=[line for line in (row.get("english_lyrics") or "").splitlines() if line.strip()],
            kanji_lyrics=[line for line in (row.get("kanji_lyrics") or "").splitlines() if line.strip()],
            romaji_lyrics=[line for line in (row.get("romaji_lyrics") or "").splitlines() if line.strip()],
        )

    def lyrics_for(self, language: str) -> list[str]:
        if language == "en":
            return self.english_lyrics
        if language == "jp":
            return self.kanji_lyrics
        if language == "romaji":
            return self.romaji_lyrics
        raise ValueError(f"Unsupported language: {language}")

    def has_lyrics_for(self, language: str) -> bool:
        return bool(self.lyrics_for(language))

    def jacket_key(self) -> str:
        song_name = sanitize_file_name(self.romaji_name).replace(" ", "-")
        return f"songs/song-{self.id:03d}_{song_name}"

    def random_lyric_pair(self, language: str, rng: random.Random | None = None) -> tuple[str, str]:
        lyrics_pool = self.lyrics_for(language)
        if len(lyrics_pool) == 0:
            return "", ""
        if len(lyrics_pool) == 1:
            return lyrics_pool[0], lyrics_pool[0]
        generator = rng or random
        idx = generator.randint(0, len(lyrics_pool) - 2)
        return lyrics_pool[idx], lyrics_pool[idx + 1]

    def random_lyrics(self, language: str, rng: random.Random | None = None) -> str:
        l1, l2 = self.random_lyric_pair(language, rng)
        return f"{l1}\n{l2}"
