import asyncio
import os
import random
from io import BytesIO

import aiohttp
import discord
from discord import HTTPException
from discord.ext import commands, tasks

from storage.card_storage import CardStorage
from exception.image_build_error import ImageBuildError
from utility.constants import *
from utility.decorators import retry_async
from utility.image import fetch_card_image_raw
from utility.notifications import notify_owner
from utility.r2 import connect_to_r2_storage
from utility.utility_functions import logger


class RandomCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.card_list = CardStorage()
        self.s3 = connect_to_r2_storage()
        self.BUCKET_NAME = os.getenv("BUCKET_NAME")

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(86400)
        self.update_card_list.start()

    def cog_unload(self) -> None:
        self.update_card_list.cancel()
        self.card_list = None

    randomcard = discord.SlashCommandGroup(name="random", description="Pick 1 or more random cards")

    def _select_card_type(self, card: dict) -> str:
        if card["card_rarity_type"] in ["rarity_2", "rarity_birthday"]:
            return "normal.png"
        return random.choice(["normal.png", "after_training.png"])

    def _get_card_key(self, card: dict, card_type: str) -> str:
        return f"cards/card_{card['id']}_{card_type}"

    @randomcard.command(name="onecard", description="Sends one random card")
    async def pick_one(self, ctx):
        @retry_async(retries=3, delay=2)
        async def defer_with_retry(context):
            await context.defer()
        try:
            await defer_with_retry(ctx)
        except (discord.HTTPException, discord.errors.NotFound, aiohttp.ClientOSError, ConnectionResetError, asyncio.TimeoutError, asyncio.CancelledError) as e:
            logger.warning(f"Defer failed, continuing without defer: {e}")

        card = random.choice(self.card_list.card_data)
        card_type = self._select_card_type(card)
        card_key = self._get_card_key(card, card_type)

        logger.info("Fetching card from R2 - bucket: %s, key: %s", self.BUCKET_NAME, card_key)

        try:
            buffer = fetch_card_image_raw(self.s3, self.BUCKET_NAME, card_key)
            await ctx.followup.send(file=discord.File(buffer, "card.png"))
        except ImageBuildError as e:
            logger.error("Error fetching card from R2: %s", e)
            await notify_owner(self.bot, "Error fetching card from R2")
            await ctx.respond("Could not fetch a card at this time, please try again later!")

    @randomcard.command(name="fivecards", description="Sends 5 random cards")
    async def pick_5(self, ctx):
        await ctx.defer()
        cards_list = []
        cards = random.sample(self.card_list.card_data, k=5)

        for idx, card in enumerate(cards):
            card_type = self._select_card_type(card)
            card_key = self._get_card_key(card, card_type)

            logger.info("Fetching card from R2 - bucket: %s, key: %s", self.BUCKET_NAME, card_key)

            try:
                buffer = fetch_card_image_raw(self.s3, self.BUCKET_NAME, card_key)
                cards_list.append(discord.File(buffer, f"card{idx}.png"))
            except ImageBuildError as e:
                logger.error("Error fetching card from R2: %s", e)
                await notify_owner(self.bot, "Error fetching card from R2")
                await ctx.respond("Could not fetch a card at this time, please try again later!")
                return

        try:
            await ctx.followup.send(files=cards_list)
        except HTTPException:
            await ctx.followup.send("Could not send all cards due to size limitations.")

    @tasks.loop(hours=24)
    async def update_card_list(self):
        self.card_list = CardStorage()
        logger.info("Update card db!")

def setup(bot):
    bot.add_cog(RandomCard(bot))
