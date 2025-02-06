SONG_JACKET_THUMBNAIL_SIZE = (200, 200)
CARD_CROP_SIZE = 250
SONG_JACKET_CROP_SIZE = 150
COMMANDS_PER_PAGE = 6
PATTERN = r'\W+'  # removes all characters that aren't letters or digits; should keep japanese or other languages charas
WEEK_ANNOUNCEMENT_CHANNEL = 1081669989989359736
OTHER_ANNOUNCEMENT_CHANNEL = 1335994039434215557
CGL_TWT_ACC_ID = 1596219475019583488
CGL_SERVER_ID = 1076494695204659220
OWNER_ID = 599999906039726090
OWNER_SERVER_ID = 1076494695204659220

UNITS = ["None", "VIRTUAL SINGER", "Leo/need", "MORE MORE JUMP!", "Wonderlands × Showtime", "Vivid BAD SQUAD",
         "25-ji, Nightcord de.", "Other"]
character_id_to_unit = {
    "Leo/need": [1, 2, 3, 4],
    "MORE MORE JUMP!": [5, 6, 7, 8],
    "Vivid BAD SQUAD": [9, 10, 11, 12],
    "Wonderlands × Showtime": [13, 14, 15, 16],
    "25-ji, Nightcord de.": [17, 18, 19, 20],
    "VIRTUAL SINGER": [21, 22, 23, 24, 25, 26]
}
unit_aliases = [
    {
        "unit": UNITS[1],
        "aliases": ["virtual_singer", "vs", "virtual_singers", "vocaloid", "vocaloids", "cryptonloids"]
    },
    {
        "unit": UNITS[2],
        "aliases": ["leo/need", "ln", "l/n", "leoni", "leoneed", "leo_need", "band", "light_sound"]
    },
    {
        "unit": UNITS[3],
        "aliases": ["more_more_jump", "mmj", "moremorejump", "momojan", "idol"]
    },
    {
        "unit": UNITS[4],
        "aliases": ["wonderlands×showtime", "wxs", "wonderlandsxshowtime", "wonderlandxshowtime",
                    "wonderlandsshowtime", "wonderlandshowtime", "wandasho", "wonderlands",
                    "wonderland", "clowns", "theme_park"]
    },
    {
        "unit": UNITS[5],
        "aliases": ["vivid_bad_squad", "vbs", "bibibus", "bibibas", "vivid_squad",
                    "vivid_bad", "vividbadsquad", "street_music_group", "street"]
    },
    {
        "unit": UNITS[6],
        "aliases": ["25-ji,_nightcord_de.", "nightcord", "niigo", "25ji",
                    "nightcord_at_25jii", "nightcord_at_25", "music_circle", "school_refusal"]
    },
    {
        "unit": UNITS[7],
        "aliases": ["other", "others", "misc", "miscellaneous"]
    }
]
unit_aliases_list = [alias for unit_dict in unit_aliases for alias in
                     unit_dict["aliases"]]  # gets all aliases and also flattens the lists

FIRST_ANNI = 1632949200
SECOND_ANNI = 1664485200
THIRD_ANNI = 1696021200
FOURTH_ANNI = 1727643600
FIFTH_ANNI = 1759179600