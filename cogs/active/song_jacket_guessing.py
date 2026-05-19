import asyncio
import random
from io import BytesIO

import discord
from discord.ext import commands, tasks

from cogs._base.base_guessing_cog import BaseGuessingCog
from data.song_guessing_round import SongGuessingRound
from exception.image_build_error import ImageBuildError
from storage.song_storage import SongStorage
from utility.constants import UNITS, SONG_JACKET_CROP_SIZE
from utility.image import prepare_cropped_jacket_question_and_answer
from utility.notifications import notify_owner
from utility.utility_functions import logger, guess_matches, find_wrong_but_valid


class SongJacketGuessing(BaseGuessingCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.song_list = SongStorage()


    def cog_unload(self) -> None:
        self.update_song_list.cancel()
        self.song_list = None
        self.ledger = None

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(86400)
        self.update_song_list.start()

    def _build_question(self, unit: str) -> SongGuessingRound | None:
        song_list_filtered_by_unit = self.song_list.songs_for_unit(unit)
        if not song_list_filtered_by_unit:
            return None

        song = random.choice(song_list_filtered_by_unit)
        jacket_key = song.jacket_key()

        logger.info(jacket_key)

        try:
            question_bytes, answer_buffer = prepare_cropped_jacket_question_and_answer(
                self.s3, self.BUCKET_NAME, jacket_key, SONG_JACKET_CROP_SIZE
            )
        except ImageBuildError as e:
            logger.error("Error preparing jacket images: %s", e)
            return None


        return SongGuessingRound(
            song=song,
            song_pool=song_list_filtered_by_unit,
            question=question_bytes,
            answer_buffer=answer_buffer,
            jacket_key=jacket_key,
            language=unit,
        )

    @discord.slash_command(name="songjacketguess", description="Guess the song from a crop of its jacket!")
    async def song_jacket_guess(self, ctx: discord.ApplicationContext, unit: discord.Option(str, choices=UNITS)):  # type: ignore
        await self.start_game(ctx, self.guessing_song, unit)

    async def guessing_song(self, ctx: discord.ApplicationContext, unit: str):
        leaderboard = self.bot.get_cog("Lb")

        round_data = self._build_question(unit)
        if round_data is None:
            await notify_owner(self.bot, "Couldn't fetch songs, please check the database")
            await ctx.followup.send("Could not fetch songs at this time, please try again later!")
            return

        # Send the cropped jacket image as the question
        question_file = discord.File(fp=BytesIO(round_data.question), filename="jacket.png")
        await ctx.followup.send(file=question_file)

        replay_args = [unit]
        await self._run_game(ctx, round_data, leaderboard, replay_args, self.guessing_song)

    def _find_wrong_but_valid(self, guessed_raw: str, round_data: SongGuessingRound) -> str | None:
        """Find if guess matches another song in the pool."""
        return find_wrong_but_valid(guessed_raw, round_data.song_pool)

    async def _check_guess(self, ctx, guess, round_data, leaderboard):
        if guess.content.lower().strip().startswith("."):
            return False

        guessed_raw = guess.content.strip()
        song = round_data.song
        replay_args = [round_data.language]

        if guess_matches(guessed_raw, song.romaji_name, song.aliases):
            message = f"Congrats {guess.author.mention}! You guessed **{song.romaji_name}** correctly!"
            sent = await self._send_answer(
                ctx,
                round_data,
                message,
                replay_args,
                self.guessing_song,
            )

            user_id = guess.author.id
            guild_id = ctx.guild.id if ctx.guild else 0
            channel_id = ctx.channel.id if ctx.channel else 0

            await self._record_correct_guess(
                user_id,
                guild_id,
                channel_id,
                song.id,
                sent.id if sent else None,
                "song_jacket_guess",
                leaderboard,
            )
            return True

        if guessed_raw.lower().strip() == "endguess":
            await self._send_answer(
                ctx,
                round_data,
                f"Giving up? The song was **{song.romaji_name}**!",
                replay_args,
                self.guessing_song,
            )
            return True

        wrong = self._find_wrong_but_valid(guessed_raw, round_data)

        if wrong:
            await ctx.followup.send(f"Nope, it's not **{wrong}**, try again!")
        else:
            await ctx.followup.send('Nope, try again!')
        return False

    @tasks.loop(hours=24)
    async def update_song_list(self):
        self.song_list = SongStorage()
        logger.info("Updated song db")


def setup(bot):
    bot.add_cog(SongJacketGuessing(bot))
