import asyncio
import random
from io import BytesIO
from re import sub

import discord
from aiohttp import ClientSession
from discord.ext import commands, tasks

from storage.song_storage import SongStorage
from utility.utility_functions import *
from views.buttons import Buttons


class LyricsGuessing(commands.Cog):
    def __init__(self, bot):
        self.song_list = SongStorage()
        self.bot = bot
        self.exclusive_en_songs = ['Sweety glitch', 'Hello Builder', 'Unsung Melodies', 'Imaginary love story', 'Ten Thousand Stars', 'Intergalactic Bound', "Can't Make A Song!!", 'MikuFiesta', 'Thousand Little Voices', 'Plaything', 'M@GICAL☆CURE! LOVE ♥ SHOT!', 'Just 1dB Louder', 'NAKAKAPAGPABAGABAG', 'Twilight Melody', 'FAKE HEART']
    def cog_unload(self) -> None:
        self.update_song_list.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(86400)
        self.update_song_list.start()

    lyricsguess = discord.SlashCommandGroup(name="lyricsguess", description="Guess the name of the song, given a lyric. Use **endguess** to give up")

    async def guess_the_song(self, ctx: discord.ApplicationContext, language, unit):
        leaderboard = self.bot.get_cog("Lb")

        song_list_filtered_by_unit = []
        jacket_url = "https://storage.sekai.best/sekai-jp-assets/music/jacket/jacket_s_(song_id)_rip/jacket_s_(song_id).png"
        if unit == "None":
            song_list_filtered_by_unit = self.song_list.song_data
        else:
            for song in self.song_list.song_data:
                if song["unit"] == unit:
                    song_list_filtered_by_unit.append(song)

        lyrics = {}
        song_name_list = []
        if language == "en":
            lyrics = {x["romaji_name"]: x["english_lyrics"] for x in song_list_filtered_by_unit}
            song_name_list = [x["romaji_name"] for x in song_list_filtered_by_unit if x["english_lyrics"]]
        if language == "jp":
            lyrics = {x["romaji_name"]: x["kanji_lyrics"] for x in song_list_filtered_by_unit}
            song_name_list = [x["romaji_name"] for x in song_list_filtered_by_unit if x["kanji_lyrics"]]
        if language == "romaji":
            lyrics = {x["romaji_name"]: x["romaji_lyrics"] for x in song_list_filtered_by_unit}
            song_name_list = [x["romaji_name"] for x in song_list_filtered_by_unit if x["romaji_lyrics"]]

        if not song_name_list:
            user = await self.bot.fetch_user(OWNER_SERVER_ID)
            await user.send("Couldn't fetch songs, please check the database")
            await ctx.respond("Could not fetch songs at this time, please try again later!")
            return

        song = random.choice(song_list_filtered_by_unit)
        logger.info(f"Song: {song['romaji_name']}")
        song_lyric = random.choice(lyrics[song["romaji_name"]])
        song["aliases"] = [sub(pattern=PATTERN, repl="", string=s.lower()) for s in song["aliases"]]

        if song["romaji_name"] in ["Jangsanbeom", "Alone"]:
            jacket_url = "https://storage.sekai.best/sekai-kr-assets/music/jacket/jacket_s_(song_id)_rip/jacket_s_(song_id).png"
        if song["romaji_name"] in self.exclusive_en_songs:
            jacket_url = "https://storage.sekai.best/sekai-en-assets/music/jacket/jacket_s_(song_id)_rip/jacket_s_(song_id).png"
        if song["romaji_name"] not in ["Jangsanbeom", "Alone"]:
            jacket_url = jacket_url.replace("(song_id)", str(song["id"]).rjust(3, '0'))
        else:
            jacket_url = jacket_url.replace("(song_id)", str(song["id"]))

        await ctx.respond(song_lyric)
        async with ClientSession() as session:
            async with session.get(url=jacket_url) as res:
                if res.status != 200:
                    user = await self.bot.fetch_user(OWNER_SERVER_ID)
                    await user.send(
                        "There's been an error fetching the requested URL, please check the logs for details.")
                    await ctx.respond("Could not fetch the song jacket at this time, please try again later.")
                    return
                buffer = BytesIO(await res.read())
                song_jacket = Image.open(buffer)
                song_jacket = song_jacket.resize(SONG_JACKET_THUMBNAIL_SIZE)
                buffer.seek(0)
                buffer.truncate(0)
                song_jacket.save(buffer, format='PNG', quality=95, optimize=True)
                buffer.seek(0)

        while True:
            try:
                guess = await self.bot.wait_for('message', check=lambda
                message: message.author != self.bot and message.channel == ctx.channel and not message.author.bot, timeout=30)
                is_finished = await self.check_guess(ctx, guess, song, buffer, song_list_filtered_by_unit, leaderboard)
                if is_finished:
                    break
            except asyncio.TimeoutError:
                await ctx.followup.send(f"Time's up! The song was **{song['romaji_name']}**!",
                                        file=discord.File(fp=buffer, filename="jacket.png"),
                                        view=Buttons(ctx, ["Play Again"], self.guess_the_song,
                                                     ["romaji", song["unit"]]))
                break

    async def check_guess(self, ctx, guess, song, buffer, song_list_filtered_by_unit, leaderboard):
        guessed_song = sub(pattern=PATTERN, string=guess.content.strip().lower(), repl="")
        guessed_song = guessed_song.replace(" ", "")
        guessed_song = guessed_song.strip()

        if guessed_song in song["aliases"] or guessed_song == song["romaji_name"].lower():
            await ctx.followup.send(f"Congrats {ctx.author.mention}! You guessed **{song['romaji_name']}** correctly!",
                                    file=discord.File(fp=buffer, filename="jacket.png"),
                                    view=Buttons(ctx, ["Play Again"], self.guess_the_song,
                                                 ["romaji", song["unit"]]))
            user_id = guess.author.id
            if leaderboard is not None:
                await leaderboard.on_right_guess(user_id)
            else:
                await ctx.followup.send("Error updating lb")
            return True
        elif guessed_song == "endguess":
            await ctx.followup.send(f"Giving up? The song was **{song['romaji_name']}**!",
                                    file=discord.File(fp=buffer, filename="jacket.png"),
                                    view=Buttons(ctx, ["Play Again"], self.guess_the_song,
                                                 ["romaji", song["unit"]]))
            return True
        else:
            temp = next((s["romaji_name"] for s in song_list_filtered_by_unit if
                         guessed_song in s["aliases"] or guessed_song == s["romaji_name"].lower()), None)

            if temp:
                await ctx.followup.send(f"Nope, it's not **{temp}**, try again!")
            else:
                await ctx.followup.send('Nope, try again!')
            return False

    @lyricsguess.command(name="romaji",
                         description="Guess the song from a romaji lyric!")
    async def guess_song_romaji(self, ctx,
                                unit: discord.Option(str, choices=UNITS)):  # type: ignore
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True
        await ctx.defer()
        await self.guess_the_song(ctx, "romaji", unit)
        active_session[ctx.channel_id] = False

    @lyricsguess.command(name="en",
                         description="Guess the song from an English lyric!")
    async def guess_song_en(self, ctx: discord.ApplicationContext, unit: discord.Option(str, choices=UNITS)):  # type: ignore
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True
        await ctx.defer()
        await self.guess_the_song(ctx, "en", unit)
        active_session[ctx.channel_id] = False

    @lyricsguess.command(name="jp",
                         description="Guess the song from a Japanese lyric!")
    async def guess_song_jp(self, ctx: discord.ApplicationContext, unit: discord.Option(str, choices=UNITS)):  # type: ignore
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True
        await ctx.defer()
        await self.guess_the_song(ctx, "jp", unit)
        active_session[ctx.channel_id] = False

    @tasks.loop(hours=24)
    async def update_song_list(self):
        self.song_list.song_data = SongStorage()
        logger.info("Updated song db!")

def setup(bot):
    bot.add_cog(LyricsGuessing(bot))