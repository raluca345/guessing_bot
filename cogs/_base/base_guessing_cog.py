import asyncio
import os
from abc import abstractmethod

import discord
from discord.ext import commands

from storage.points_ledger_storage import PointsLedgerStorage
from utility.r2 import connect_to_r2_storage
from utility.session import session_lock
from utility.utility_functions import logger
from views.buttons import Buttons


class BaseGuessingCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.ledger = PointsLedgerStorage()
        self.s3 = connect_to_r2_storage()
        self.BUCKET_NAME = os.getenv("BUCKET_NAME")

    # the args are options passed to the slash command, specific to each guessing game
    async def start_game(self, ctx: discord.ApplicationContext, game_coro, *args, **kwargs):
        await ctx.defer()
        async with session_lock(ctx.channel_id):
            await game_coro(ctx, *args, **kwargs)

    async def _run_game(self, ctx, round_data, leaderboard, replay_args, game_coro, timeout=30):
        while True:
            try:
                guess = await self.bot.wait_for(
                    "message",
                    check=lambda message: (
                        message.author != self.bot
                        and message.channel == ctx.channel
                        and not message.author.bot
                    ),
                    timeout=timeout,
                )
                is_finished = await self._check_guess(
                    ctx,
                    guess,
                    round_data,
                    leaderboard,
                )
                if is_finished:
                    break
            except asyncio.TimeoutError:
                await self._send_answer(
                    ctx,
                    round_data,
                    f"Time's up! The song was **{round_data.song.romaji_name}**!",
                    replay_args,
                    game_coro,
                )
                break

    async def _send_answer(
            self,
            ctx,
            round_data,
            message: str,
            replay_args: list,
            game_coro,
    ):
        """Send answer file with message and replay button."""
        buttons_view = Buttons(ctx, ["Play Again"], game_coro, replay_args)
        round_data.answer_buffer.seek(0)
        sent = await ctx.followup.send(
            message,
            file=discord.File(fp=round_data.answer_buffer, filename="jacket.png"),
            view=buttons_view,
        )
        buttons_view.message = sent
        return sent

    @abstractmethod
    def _build_question(self, *args, **kwargs):
        """Build a question. Signature varies by game type, depending on the passed options to the slash commands."""
        pass


    @abstractmethod
    async def _check_guess(self, ctx, guess, round_data, leaderboard):
        pass

    async def _find_wrong_but_valid(self, guess, round_data):
        pass

    async def _record_correct_guess(
            self,
            user_id: int,
            guild_id: int,
            channel_id: int,
            item_id: int,
            message_id: int | None,
            game_type: str,
            leaderboard,
    ):
        """Record points and update leaderboard."""
        try:
            self.ledger.record_points(
                guild_id,
                channel_id,
                user_id,
                1,
                game_type,
                item_id,
                message_id,
            )
        except Exception:
            logger.exception("Ledger insert failed")

        if leaderboard is not None:
            await leaderboard.on_right_guess(user_id)
