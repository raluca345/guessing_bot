import re

from utility.utility_functions import connect, logger

class SongStorage:

    def __init__(self) -> None:
        self.connection = connect()
        self.cursor = self.connection.cursor(dictionary=True)
        self.song_data = []
        self.song_by_name = {}
        self.get_song_data()

    def _ensure_connection(self):
        try:
            self.connection.ping(reconnect=True, attempts=3, delay=2)
        except Exception:
            logger.warning("Database connection lost, reconnecting...")
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = connect()
        self.cursor = self.connection.cursor(dictionary=True)

    def get_song_data(self):
        self._ensure_connection()

        query = ("SELECT id, romaji_name, aliases, unit, english_lyrics, "
                 "kanji_lyrics, romaji_lyrics FROM songs")
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        for row in rows:
            if not row or row == {}:
                continue
            aliases = row["aliases"].split(";")
            aliases.append(row["romaji_name"])
            aliases = [x.lower() for x in aliases]

            row["aliases"] = aliases

            english_lyrics = re.split(r'\r\n|\n', row["english_lyrics"])
            english_lyrics = [x for x in english_lyrics]
            row["english_lyrics"] = english_lyrics

            kanji_lyrics = re.split(r'\r\n|\n', row["kanji_lyrics"])
            kanji_lyrics = [x for x in kanji_lyrics]
            row["kanji_lyrics"] = kanji_lyrics

            romaji_lyrics = re.split(r'\r\n|\n', row["romaji_lyrics"])
            romaji_lyrics = [x for x in romaji_lyrics]
            row["romaji_lyrics"] = romaji_lyrics
            
            self.song_data.append(row)
            self.song_by_name[row["romaji_name"]] = row

    def add_song_alias(self, song_name: str, new_alias: str) -> bool:
        song = self.song_by_name.get(song_name)
        if not song or new_alias.lower() in song["aliases"]:
            return False

        self._ensure_connection()
        query = "UPDATE songs SET aliases = CONCAT(aliases, %s) WHERE romaji_name = %s"
        self.cursor.execute(query, (";" + new_alias, song_name))
        self.connection.commit()

        song["aliases"].append(new_alias.lower())
        return True
