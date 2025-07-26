import asyncio
import random
import os
from io import BytesIO

import discord
from discord import HTTPException
from discord.ext import commands, tasks
from PIL import Image
from dotenv import load_dotenv

from storage.card_storage import CardStorage
from utility.utility_functions import logger
from utility.constants import *
from utility.utility_functions import connect_to_r2_storage

class RandomCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.card_list = CardStorage()
        load_dotenv()
        self.s3 = connect_to_r2_storage()
        self.BUCKET_NAME = os.getenv("BUCKET_NAME")

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(86400)
        self.update_card_list.start()

    def cog_unload(self) -> None:
        self.update_card_list.cancel()

    randomcard = discord.SlashCommandGroup(name="random", description="Pick 1 or more random cards")

    @randomcard.command(name="onecard", description="Sends one random card")
    async def pick_one(self, ctx):
        await ctx.defer()

        card = random.choice(self.card_list.card_data)

        if card["card_rarity_type"] in ["rarity_2", "rarity_birthday"]:
            card_type = "normal.png"
        else:
            card_type = random.choice(["normal.png", "after_training.png"])

        card_key = f"cards/card_{card['id']}_{card_type}"
        logger.info("Fetching card from R2 - bucket: %s, key: %s", self.BUCKET_NAME, card_key)

        try:
            obj = self.s3.get_object(Bucket=self.BUCKET_NAME, Key=card_key)
            buffer = BytesIO(obj['Body'].read())
            await ctx.followup.send(file=discord.File(buffer, "card.png"))
        except Exception as e:
            logger.error("Error fetching card from R2: %s", e)
            user = await self.bot.fetch_user(OWNER_SERVER_ID)
            await user.send("Error fetching card from R2")
            await ctx.respond("Could not fetch a card at this time, please try again later!")

    @randomcard.command(name="fivecards", description="Sends 5 random cards")
    async def pick_5(self, ctx):
        await ctx.defer()
        cards_list = []

        cards = random.sample(self.card_list.card_data, k=5)

        for card in cards:
            if card["card_rarity_type"] in ["rarity_2", "rarity_birthday"]:
                card_type = "normal.png"
            else:
                card_type = random.choice(["normal.png", "after_training.png"])

            card_key = f"cards/card_{card['id']}_{card_type}"
            logger.info("Fetching card from R2 - bucket: %s, key: %s", self.BUCKET_NAME, card_key)

            try:
                obj = self.s3.get_object(Bucket=self.BUCKET_NAME, Key=card_key)
                buffer = BytesIO(obj['Body'].read())
                cards_list.append(discord.File(buffer, f"card{cards.index(card)}.png"))
            except Exception as e:
                logger.error("Error fetching card from R2: %s", e)
                user = await self.bot.fetch_user(OWNER_SERVER_ID)
                await user.send("Error fetching card from R2")
                await ctx.respond("Could not fetch a card at this time, please try again later!")
                return

        try:
            await ctx.followup.send(files=cards_list)
        except HTTPException:
            await ctx.followup.send("Could not send all cards due to size limitations.")

    @tasks.loop(hours=24)
    async def update_card_list(self):
        self.card_list.card_data = CardStorage()
        logger.info("Update card db!")

def setup(bot):
    bot.add_cog(RandomCard(bot))