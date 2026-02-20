import re

from utility.utility_functions import connect

class SongStorage:

    connection = connect()
    cursor = connection.cursor(dictionary=True)

    song_data = []

    def __init__(self) -> None:
        self.song_data = []
        self.song_by_name = {}
        self.get_song_data()

    def get_song_data(self):

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

        query = "UPDATE songs SET aliases = CONCAT(aliases, %s) WHERE romaji_name = %s"
        self.cursor.execute(query, (";" + new_alias, song_name))
        self.connection.commit()

        song["aliases"].append(new_alias.lower())
        return True
