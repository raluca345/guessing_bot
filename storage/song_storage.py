from data.song import Song
from storage.base_storage import BaseStorage


class SongStorage(BaseStorage):

    def __init__(self) -> None:
        super().__init__(use_dictionary=True)
        self.song_data: list[Song] = []
        self.song_by_name: dict[str, Song] = {}
        self.refresh()

    def get_song_data(self):
        """Backward-compatible alias; prefers `refresh()`."""
        self.refresh()

    def refresh(self):
        query = (
            "SELECT id, romaji_name, aliases, unit, english_lyrics, "
            "kanji_lyrics, romaji_lyrics FROM songs"
        )
        rows = self._load(query)
        self.song_data = []
        self.song_by_name = {}

        for row in rows:
            if not row or row == {}:
                continue
            song = Song.from_db_row(row)
            self.song_data.append(song)
            self.song_by_name[song.romaji_name] = song

    def songs_for_unit(self, unit: str) -> list[Song]:
        if unit == "None":
            return list(self.song_data)
        return [song for song in self.song_data if song.unit == unit]

    def songs_with_lyrics(self, language: str, unit: str = "None") -> list[Song]:
        return [song for song in self.songs_for_unit(unit) if song.has_lyrics_for(language)]

    def add_song_alias(self, song_name: str, new_alias: str) -> bool:
        song = self.song_by_name.get(song_name)
        alias_lower = new_alias.lower()
        if not song or alias_lower in song.aliases:
            return False

        query = "UPDATE songs SET aliases = CONCAT(aliases, %s) WHERE romaji_name = %s"
        self.execute_insert(query, (";" + new_alias, song_name))

        song.aliases.append(alias_lower)
        return True
