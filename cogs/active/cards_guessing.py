import asyncio
import os
import random
from io import BytesIO

import discord
from discord.ext import commands, tasks

from cogs._base.base_guessing_cog import BaseGuessingCog
from data.card import Card
from data.card_guessing_round import CardGuessingRound
from data.character import Character
from exception.image_build_error import ImageBuildError
from storage.card_storage import CardStorage
from storage.character_storage import CharacterStorage
from utility.constants import UNITS
from utility.filters import get_card_filter
from utility.image import prepare_card_question_and_answer
from utility.notifications import notify_owner
from utility.utility_functions import logger


class CardsGuessing(BaseGuessingCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.card_storage = CardStorage()
        self.character_storage = CharacterStorage()



    def cog_unload(self) -> None:
        self.update_card_list.cancel()
        self.card_storage = None
        self.ledger = None

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(86400)
        self.update_card_list.start()


    cards = discord.SlashCommandGroup(
        "card",
        description="Given a card crop, guess the character it belongs to. Use endguess to give up",
    )

    @cards.command(name="guess", description="Guess from all cards! (1*s excluded)")
    async def guess_card(self, ctx: discord.ApplicationContext):
        await self.start_game(ctx, self.card_guess_game, self.card_storage.card_data)

    @cards.command(name="fourstarguess", description="Guess from all 4* cards!")
    async def guess_four_star(self, ctx):
        await self.start_game(ctx, self.card_guess_game, get_card_filter("four_star", self.card_storage.card_data))

    @cards.command(name="threestarguess", description="Guess from all 3* cards!")
    async def guess_three_star(self, ctx):
        await self.start_game(ctx, self.card_guess_game, get_card_filter("three_star", self.card_storage.card_data))

    @cards.command(name="notwostarguess", description="Guess from all cards that aren't 2*!")
    async def guess_no_two_star(self, ctx):
        await self.start_game(ctx, self.card_guess_game, get_card_filter("no_two_star", self.card_storage.card_data))

    @cards.command(name="twostarguess", description="Guess from all 2* cards!")
    async def guess_two_star(self, ctx):
        await self.start_game(ctx, self.card_guess_game, get_card_filter("two_star", self.card_storage.card_data))

    @cards.command(name="bdayguess", description="Guess from all birthday rarity cards!")
    async def guess_birthday(
        self,
        ctx,
        rotation: discord.Option(
            discord.SlashCommandOptionType.integer,
            required=False,
            description="Birthday rotation",
        ) = None, #type: ignore
    ):
        cards_filtered = get_card_filter("birthday", self.card_storage.card_data)
        if rotation:
            cards_filtered = get_card_filter(f"birthday{rotation}", self.card_storage.card_data)
        await self.start_game(ctx, self.card_guess_game, cards_filtered)

    @cards.command(name="collabguess", description="Guess from collaboration cards!")
    async def guess_collab(self, ctx):
        await self.start_game(ctx, self.card_guess_game, get_card_filter("collab", self.card_storage.card_data))

    @cards.command(name="tamagotchiguess", description="Guess from tamagotchi cards!")
    async def guess_tamagotchi(self, ctx):
        await self.start_game(ctx, self.card_guess_game, get_card_filter("tamagotchi", self.card_storage.card_data))

    @cards.command(name="sanrioguess", description="Guess from sanrio cards!")
    async def guess_sanrio(self, ctx):
        await self.start_game(ctx, self.card_guess_game, get_card_filter("sanrio", self.card_storage.card_data))

    @cards.command(name="movieguess", description="Guess from movie cards!")
    async def guess_movie(self, ctx):
        await self.start_game(ctx, self.card_guess_game, get_card_filter("movie", self.card_storage.card_data))

    @cards.command(name="unitguess", description="Guess from cards from a specific unit!")
    async def guess_unit(self, ctx, unit: discord.Option(str, choices=UNITS)):  # type: ignore
        cards_filtered = get_card_filter(f"unit:{unit}", self.card_storage.card_data) or self.card_storage.card_data
        await self.start_game(ctx, self.card_guess_game, cards_filtered)


    def _build_question(self, filtered_cards_list: list) -> CardGuessingRound | None:
        """Build a card guessing round."""
        if not filtered_cards_list:
            return None

        card_dict = random.choice(filtered_cards_list)
        card = Card.from_db_row(card_dict)

        # Find character
        character = self.character_storage.get_by_id(card.character_id)
        if not character:
            return None

        # Choose card type
        if card.card_rarity_type in ["rarity_2", "rarity_birthday"]:
            card_type = "normal.png"
        else:
            card_type = random.choice(["normal.png", "after_training.png"])

        card_key = card.card_key(card_type)
        use_mask = card.card_rarity_type.strip() == "rarity_2"

        logger.info(f"Card: {card.id}, Character: {character.character_name}, Type: {card_type}")

        try:
            question_bytes, answer_buffer = prepare_card_question_and_answer(
                self.s3, self.BUCKET_NAME, card_key, card.id, use_mask
            )
        except ImageBuildError as e:
            logger.error("Error preparing card images: %s", e)
            return None

        return CardGuessingRound(
            card=card,
            character=character,
            question=question_bytes,
            answer_buffer=answer_buffer,
            card_pool=filtered_cards_list,
            card_type=card_type,
        )

    def _find_wrong_character(self, guessed_raw: str) -> Character | None:
        """Find if a guess matches a character other than the target."""
        for char_dict in self.character_storage.characters_data:
            char = Character.from_db_row(char_dict)
            if char.matches(guessed_raw):
                return char

        return None


    async def card_guess_game(self, ctx: discord.ApplicationContext, filtered_cards_list):
        """Main game flow for card guessing."""
        leaderboard = self.bot.get_cog("Lb")

        round_data = self._build_question(filtered_cards_list)
        if round_data is None:
            await notify_owner(self.bot, "Couldn't fetch cards, please check the database")
            await ctx.followup.send("Could not fetch cards at this time, please try again later!")
            return

        # send the card crop
        question_file = discord.File(fp=BytesIO(round_data.question), filename="card.png")
        await ctx.followup.send(file=question_file)

        replay_args = [filtered_cards_list]
        await self._run_game(ctx, round_data, leaderboard, replay_args, self.card_guess_game)

    async def _run_game(self, ctx, round_data, leaderboard, replay_args, game_coro, timeout=30.0):
        """Override to provide card-specific timeout message."""
        while True:
            try:
                guess = await self.bot.wait_for(
                    "message",
                    check=lambda m: (
                        m.author != self.bot
                        and m.channel == ctx.channel
                        and not m.author.bot
                    ),
                    timeout=timeout,
                )

                finished = await self._check_guess(ctx, guess, round_data, leaderboard)
                if finished:
                    break

            except asyncio.TimeoutError:
                await self._send_answer(
                    ctx,
                    round_data,
                    f"Time's up! It was **{round_data.character.display_name()}** - **{round_data.card.display_name()}**!",
                    replay_args,
                    game_coro,
                )
                break


    async def _check_guess(self, ctx, guess, round_data: CardGuessingRound, leaderboard):
        """Check if the guess is correct."""
        if guess.content.lower().strip().startswith("."):
            return False

        content = guess.content.lower().strip()

        # Correct guess
        if round_data.character.matches(content):
            message = f'Congrats {guess.author.mention}! You guessed **{round_data.character.display_name()}** - **{round_data.card.display_name()}** correctly!'
            sent = await self._send_answer(
                ctx,
                round_data,
                message,
                [round_data.card_pool],
                self.card_guess_game,
            )

            user_id = guess.author.id
            guild_id = ctx.guild.id if ctx.guild else 0
            channel_id = ctx.channel.id if ctx.channel else 0

            await self._record_correct_guess(
                user_id,
                guild_id,
                channel_id,
                round_data.card.id,
                sent.id if sent else None,
                "card_guess",
                leaderboard,
            )
            return True

        # Give up
        if content == "endguess":
            await self._send_answer(
                ctx,
                round_data,
                f"Giving up? It was **{round_data.character.display_name()}** - **{round_data.card.display_name()}**!",
                [round_data.card_pool],
                self.card_guess_game,
            )
            return True

        # Provide hint if guess matches another character
        wrong_char = self._find_wrong_character(content)
        if wrong_char:
            await ctx.followup.send(
                f"Nope, it's not **{wrong_char.display_name()}**, try again!"
            )
            return False

        # Generic wrong answer
        await ctx.followup.send("Nope, try again!")
        return False


    @tasks.loop(hours=24)
    async def update_card_list(self):
        self.card_storage = CardStorage()
        logger.info("Updated card DB")


def setup(bot):
    bot.add_cog(CardsGuessing(bot))
