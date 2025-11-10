## An-chan Bot

An-chan is a Discord bot built using the `pycord` python library that implements 3 interactive guessing games based on the *Project SEKAI: Colorful Stage feat. Hatsune Miku* game. It also includes a leaderboard to compete with other players and a feature to pull announcements from the twitter account for the Card Guessing League (CGL) hosted in Sekaicord, an unofficial Project SEKAI Discord server. Optional, but we would love to see you there and play with us!

## Features

**Card guessing:** guess the character the card belongs to based on a crop of the card  
**Lyrics guessing:** guess the song the lyric is from  
**Song jacket guessing:** guess the song based on a crop of its jacket  
**Leaderboard:** each correct guess is worth 1 point, collect points and reach for the top!
**Automated twitter posts fetching:** never miss an announcement  
**Song alias viewing and suggesting:** everyone refers to any song in a specific way so this makes it easier for users to guess  
**Random card fetching:** meant for users or the game hosts to make cropping cards easier, but you can just admire the card art if you want to


## Installation

1. Clone the repository:  
```bash
git clone https://github.com/yourusername/guessing_bot.git
cd guessing_bot
```

2. Install the required packages:  
```bash
pip install -r requirements.txt
```

3. Configure the bot:

- Create a `.env` file in the root directory.
- Add your bot token and other necessarry configurations.

4. Run the bot

```bash
python bot.py
```


## Configuration

The bot uses an `.env` file to configure its dependencies and a `config/config.ini` file for the MySQL database. The card and song jacket images are pulled from a R2 Cloudflare bucket; create one and save your secrets.
If you don't want to fetch twitter posts, exclude the `twthub` cog from the cog loading:

```python
cogs_list = [f.split(".")[0] for f in os.listdir(os.getcwd() + "/cogs") if not f.startswith("__")]
cogs_list = [cog for cog in cogs_list if cog != "twt_hub"]

for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')
```

The `config/config.ini` file follows the following format:  

```ini
[mysqlDB]
host = 127.0.0.1
db = your_databse
user = your_username
pass = your_password
```

The following sections in the `.env` file are required:  

- `TOKEN`: Your Discord bot token
- `BEARER_TOKEN`: Your Twitter project bearer token
- `R2_STORAGE_TOKEN`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`: Cloudflare R2 storage secrets
- `ENDPOINT_URL`: Your Cloudflare R2 storage endpoint URL
- `BUCKET_NAME`: Your Cloudflare R2 storage bucket name
- `S3_API`: The Clouflare S3 API  

## Commands  

### Card Guessing Game Commands

- `/card guess`: Guess from all the cards in the game, excluding 1*s
- `/card {filter}guess`: Guess from all the cards from a filtered pool. The available filters are unit, fourstar, threestar, twostar, notwostar, sanrio, bday  

### Lyrics Guessing Game Commands

- `/lyricsguess {language}`: Guess from all songs from all servers (JP, EN, KR, TW, CN). `{language}` can be en, romaji or jp. Should be be renamed since it includes songs in languages other than Japanese and English now

### Song Jacket Guessing Game Commands

- `/songjacketguess`: Guess from all songs from all servers

### Random Card Commands

- `/random onecard`: Returns one random card. Can be the normal or trained art for a 3* or 4*.
- `/random fivecards`: Returns five random cards

### Song Alias Commands

- `/alias viewsong`: View a song's alias(es)
- `/alias suggestsong`: Suggest an alias for a song
- `/alias viewcharacter`: View a character's alias(es)
- `/alias suggestcharacter`: Suggest an alias for a character

### Other Commands

- `/lb`: View the leaderboard
- `/reload`: Server owner-only command that reloads a specified cog
- `/help`: Sends an embed with all the bot's commands

## Logging

The bot logs its errors to `log/cpy-errors.log`.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any changes or improvements.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/raluca345/guessing_bot?tab=MIT-1-ov-file) file for details.
