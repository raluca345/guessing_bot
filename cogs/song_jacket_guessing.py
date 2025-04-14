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


class SongJacketGuessing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_list = SongStorage()
        self.exclusive_english_songs = ['Sweety glitch', 'Hello Builder', 'Unsung Melodies', 'Imaginary love story',
                                        'Ten Thousand Stars', 'Intergalactic Bound', "Can't Make A Song!!",
                                        'MikuFiesta', 'Thousand Little Voices', 'Plaything',
                                        'M@GICAL☆CURE! LOVE ♥ SHOT!', 'Just 1dB Louder', 'NAKAKAPAGPABAGABAG',
                                        'Twilight Melody', 'FAKE HEART']
        self.s3 = connect_to_r2_storage()
        self.BUCKET_NAME = os.getenv("BUCKET_NAME")

    def cog_unload(self) -> None:
        self.update_song_list.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(86400)
        self.update_song_list.start()

    @discord.slash_command(name="songjacketguess", description="Guess the song from a crop of its jacket!")
    async def song_jacket_guess(self, ctx, unit: discord.Option(str, choices=UNITS)):  # type: ignore
        song_list_filtered_by_unit = []
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True

        if not ctx.interaction.response.is_done():
            await ctx.defer()

        leaderboard = self.bot.get_cog("Lb")

        song_list_filtered_by_unit = []
        jacket_key = "songs/song-{}_{}"
        if unit == "None":
            song_list_filtered_by_unit = self.song_list.song_data
        else:
            for song in self.song_list.song_data:
                if song["unit"] == unit:
                    song_list_filtered_by_unit.append(song)
        song_name_list = {x["id"]: x["romaji_name"] for x in song_list_filtered_by_unit}
        if not song_name_list:
            user = await self.bot.fetch_user(OWNER_SERVER_ID)
            await user.send("Couldn't fetch songs, please check the database")
            await ctx.respond("Could not fetch songs at this time, please try again later!")
            return
        song = random.choice(song_list_filtered_by_unit)
        song["aliases"] = [sub(pattern=PATTERN, repl="", string=s.lower()) for s in song["aliases"]]

        song_name = sanitize_file_name(song_name_list[song["id"]]).replace(" ", "-")
        song_id = str(song["id"]).zfill(3)
        jacket_key = jacket_key.format(song_id, song_name)

        logger.info(jacket_key)

        try:
            obj = self.s3.get_object(Bucket=self.BUCKET_NAME, Key=jacket_key)
            buffer = BytesIO(obj['Body'].read())
            img = Image.open(buffer)
        except Exception as e:
            logger.error(f"Error fetching image from R2: {e}")
            user = await self.bot.fetch_user(OWNER_ID)
            await user.send("Error fetching song jacket from R2")
            await ctx.respond("Could not fetch a song jacket at this time, please try again later!")
            active_session[ctx.channel_id] = False
            return
        region = generate_img_crop(img, SONG_JACKET_CROP_SIZE)
        with BytesIO() as image_binary:
            region.save(image_binary, 'PNG', quality=95, optimize=True)
            image_binary.seek(0)
            picture = discord.File(fp=image_binary, filename="jacket.png")
            await ctx.respond(file=picture)

            image_binary.truncate(0)
            image_binary.seek(0)

            img = img.resize(SONG_JACKET_THUMBNAIL_SIZE)
            img.save(image_binary, "PNG", quality=95, optimize=True)
            image_binary.seek(0)
            answer = discord.File(fp=image_binary, filename="answer.png")

        while True:
            try:
                guess = await self.bot.wait_for('message', check=lambda
                    message: message.author != self.bot and message.channel == ctx.channel and not message.author.bot,
                                                timeout=30.0)
                is_finished = await self.check_guess(ctx, guess, song, answer, song_list_filtered_by_unit, leaderboard, unit)
                if is_finished:
                    break
            except asyncio.TimeoutError:
                tmp = song["romaji_name"]
                logger.info(unit)
                await ctx.followup.send(f"Time's up! The song was **{tmp}**!", file=answer,
                                        view=Buttons(ctx, ["Play Again"], self.song_jacket_guess, [unit]))
                active_session[ctx.channel_id] = False
                break

    async def check_guess(self, ctx, guess, song, answer, song_list_filtered_by_unit, leaderboard, unit):
        guessed_song = sub(pattern=PATTERN, string=guess.content.strip().lower(), repl="")
        guessed_song = guessed_song.replace(" ", "")
        guessed_song = guessed_song.strip()  # making sure trailing spaces are really gone
        logger.info("guess - %s", guessed_song)
        if guessed_song in song["aliases"] or guessed_song == song[
            "romaji_name"].lower() or guessed_song == sub(pattern=PATTERN, repl=" ", string=song[
            "romaji_name"]).lower() or guessed_song == sub(pattern=PATTERN, repl="", string=song[
            "romaji_name"]).lower() or guessed_song == sub(pattern=PATTERN, repl="",
                                                           string=song["romaji_name"]).replace(" ", ""):
            logger.info(unit)
            await ctx.followup.send(f"Congrats {guess.author.mention}! You guessed **{song['romaji_name']}** correctly!",
                        file=answer,
                        view=Buttons(ctx, ["Play Again"], self.song_jacket_guess, [unit]))
            user_id = guess.author.id
            if leaderboard is not None:
                await leaderboard.on_right_guess(user_id)
            else:
                await ctx.followup.send("Error updating lb")
                logger.error("Error updating lb")
            active_session[ctx.channel_id] = False
            return True
        elif guessed_song == "endguess":
            await ctx.followup.send(f"Giving up? The song was **{song['romaji_name']}**!", file=answer,
                                    view = Buttons(ctx, ["Play Again"], self.song_jacket_guess, [unit]))
            active_session[ctx.channel_id] = False
            return True
        else:
            # Find a song that matches the incorrect guess
            temp = next((s["romaji_name"] for s in song_list_filtered_by_unit if
                         guessed_song in s["aliases"] or guessed_song == s[
                             "romaji_name"].lower() or guessed_song == sub(pattern=PATTERN, repl=" ", string=s[
                             "romaji_name"]).lower() or guessed_song == sub(pattern=PATTERN, repl="", string=s[
                             "romaji_name"]).lower() or guessed_song == sub(pattern=PATTERN, repl="",
                                                                            string=s["romaji_name"]).replace(" ", "")),
                        None)

            if temp:
                await ctx.followup.send(f"Nope, it's not **{temp}**, try again!")
            else:
                await ctx.followup.send('Nope, try again!')
            return False

    @tasks.loop(hours=24)
    async def update_song_list(self):
        self.song_list.song_data = SongStorage()
        logger.info("Updated song db!")


def setup(bot):
    bot.add_cog(SongJacketGuessing(bot))