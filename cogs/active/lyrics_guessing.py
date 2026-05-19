import asyncio
import random

import discord
from discord.ext import commands, tasks

from data.song_guessing_round import SongGuessingRound
from exception.image_build_error import ImageBuildError
from cogs._base.base_guessing_cog import BaseGuessingCog
from storage.song_storage import SongStorage
from utility.constants import UNITS
from utility.image import prepare_answer_song_jacket
from utility.notifications import notify_owner
from utility.utility_functions import logger, guess_matches, find_wrong_but_valid


class LyricsGuessing(BaseGuessingCog):
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

    lyricsguess = discord.SlashCommandGroup(
        name="lyricsguess",
        description="Guess the name of the song, given a lyric. Use **endguess** to give up",
    )
    

    def _find_wrong_but_valid(self, guessed_raw: str, round_data: SongGuessingRound) -> str | None:
        """Find if guess matches another song in the pool."""
        return find_wrong_but_valid(guessed_raw, round_data.song_pool)


    def _build_question(self, language: str, unit: str) -> SongGuessingRound | None:
        song_pool = self.song_list.songs_with_lyrics(language, unit)
        if not song_pool:
            return None

        song = random.choice(song_pool)
        song_lyrics = song.random_lyrics(language)
        jacket_key = song.jacket_key()

        logger.info([s.romaji_name for s in song_pool])
        logger.info("Song: %s", song.romaji_name)
        logger.info("Lyrics: %s", song_lyrics)
        logger.info("Jacket key: %s", jacket_key)

        try:
            answer_buffer = prepare_answer_song_jacket(self.s3, self.BUCKET_NAME, jacket_key)
        except ImageBuildError:
            return None

        return SongGuessingRound(
            song=song,
            song_pool=song_pool,
            question=song_lyrics,
            answer_buffer=answer_buffer,
            jacket_key=jacket_key,
            language=language,
        )


    async def guessing_lyrics(self, ctx: discord.ApplicationContext, language: str, unit: str):
        leaderboard = self.bot.get_cog("Lb")

        round_data = self._build_question(language, unit)
        if round_data is None:
            await notify_owner(self.bot, "Couldn't fetch songs, please check the database")
            await ctx.followup.send("Could not fetch songs at this time, please try again later!")
            return

        await ctx.followup.send(round_data.question)
        replay_args = [language, round_data.song.unit]
        await self._run_game(ctx, round_data, leaderboard, replay_args, self.guessing_lyrics)


    async def _check_guess(
        self,
        ctx,
        guess,
        round_data: SongGuessingRound,
        leaderboard,
    ):
        # ignore messages starting with "." so people can chat during guessing rounds
        if guess.content.lower().strip().startswith("."):
            return False

        guessed_raw = guess.content.strip()
        song = round_data.song
        replay_args = [round_data.language, song.unit]

        if guess_matches(guessed_raw, song.romaji_name, song.aliases):
            user_id = guess.author.id
            guild_id = ctx.guild.id if ctx.guild else 0
            channel_id = ctx.channel.id if ctx.channel else 0

            message = f"Congrats {guess.author.mention}! You guessed **{song.romaji_name}** correctly!"
            sent = await self._send_answer(
                ctx,
                round_data,
                message,
                replay_args,
                self.guessing_lyrics,
            )

            await self._record_correct_guess(
                user_id,
                guild_id,
                channel_id,
                song.id,
                sent.id if sent else None,
                "lyrics_guess",
                leaderboard,
            )
            return True

        if guessed_raw.lower().strip() == "endguess":
            await self._send_answer(
                ctx,
                round_data,
                f"Giving up? The song was **{song.romaji_name}**!",
                replay_args,
                self.guessing_lyrics,
            )
            return True

        wrong = self._find_wrong_but_valid(guessed_raw, round_data)
        if wrong:
            await ctx.followup.send(f"Nope, it's not **{wrong}**, try again!")
        else:
            await ctx.followup.send("Nope, try again!")
        return False


    @lyricsguess.command(name="romaji", description="Guess the song from a romaji lyric!")
    async def guess_song_romaji(self, ctx, unit: discord.Option(str, choices=UNITS)):  # type: ignore
        await self.start_game(ctx, self.guessing_lyrics, "romaji", unit)

    @lyricsguess.command(name="en", description="Guess the song from an English lyric!")
    async def guess_song_en(self, ctx: discord.ApplicationContext, unit: discord.Option(str, choices=UNITS)):  # type: ignore
        await self.start_game(ctx, self.guessing_lyrics, "en", unit)

    @lyricsguess.command(name="jp", description="Guess the song from a Japanese lyric!")
    async def guess_song_jp(self, ctx: discord.ApplicationContext, unit: discord.Option(str, choices=UNITS)):  # type: ignore
        await self.start_game(ctx, self.guessing_lyrics, "jp", unit)

    @tasks.loop(hours=24)
    async def update_song_list(self):
        self.song_list = SongStorage()
        logger.info("Updated song db")


def setup(bot):
    bot.add_cog(LyricsGuessing(bot))
