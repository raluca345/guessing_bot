from utility.utility_functions import connect

class SongStorage:

    connection = connect()
    cursor = connection.cursor(dictionary=True)

    song_data = []

    def __init__(self) -> None:
        self.song_data = []
        self.get_song_data()

    def get_song_data(self):

        query = ("SELECT id, romaji_name, aliases, unit, english_lyrics, "
                 "kanji_lyrics, romaji_lyrics FROM songs")
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        for row in rows:
            #logger.info(row)
            if not row or row == {}:
                continue
            aliases = row["aliases"].split(";")
            aliases.append(row["romaji_name"])
            aliases = [x.lower() for x in aliases]
            row["aliases"] = aliases
            english_lyrics = row["english_lyrics"].split("\r\n")
            english_lyrics = [x for x in english_lyrics]
            #logger.info(english_lyrics)
            row["english_lyrics"] = english_lyrics
            kanji_lyrics = row["kanji_lyrics"].split("\r\n")
            kanji_lyrics = [x for x in kanji_lyrics]
            row["kanji_lyrics"] = kanji_lyrics
            romaji_lyrics = row["romaji_lyrics"].split("\r\n")
            romaji_lyrics = [x for x in romaji_lyrics]
            row["romaji_lyrics"] = romaji_lyrics
            self.song_data.append(row)

# storage = SongStorage()
# logger.info(storage.song_data)