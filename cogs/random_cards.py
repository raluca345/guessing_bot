import asyncio
from io import BytesIO
import random
from urllib.parse import urljoin

import discord
from PIL import Image
from aiohttp import ClientSession
from discord import HTTPException, Embed
from discord.ext import commands, tasks
from discord.ext.pages import PageGroup, Page, Paginator

from storage.card_storage import CardStorage
from utility.utility_functions import logger


class RandomCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.card_list = CardStorage()

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
        card_url = "https://storage.sekai.best/sekai-jp-assets/character/member/"

        card = random.choice(self.card_list.card_data)

        if card["card_rarity_type"] in ["rarity_2", "rarity_birthday"]:
            card_type = "card_normal.png"
        else:
            card_type = random.choice(["card_normal.png", "card_after_training.png"])

        temp = card["assetbundle_name"] + "_rip/" + card_type
        card_url = urljoin(card_url, temp)
        logger.info("url - %s", card_url)

        async with ClientSession() as session:
            async with session.get(url=card_url) as res:
                if res.status != 200:
                    user = await self.bot.fetch_user(OWNER_SERVER_ID)
                    await user.send("Error fetching card")
                    logger.error(res)
                    await ctx.respond("Could not fetch a card at this time, please try again later!")
                    return
                random_card = BytesIO(await res.read())
                await ctx.followup.send(file=discord.File(random_card, "card.png"))

    @tasks.loop(hours=24)
    async def update_card_list(self):
        self.card_list.card_data = CardStorage()
        logger.info("Update card db!")

    @randomcard.command(name="fivecards", description="Sends 5 random cards")
    async def pick_5(self, ctx):
        await ctx.defer()
        card_url = "https://storage.sekai.best/sekai-jp-assets/character/member/"
        card_urls = []
        cards_list = [] #file list

        cards = random.sample(self.card_list.card_data, k=5)

        for card in cards:
            card_url = "https://storage.sekai.best/sekai-jp-assets/character/member/"
            if card["card_rarity_type"] in ["rarity_2", "rarity_birthday"]:
                card_type = "card_normal.png"
            else:
                card_type = random.choice(["card_normal.png", "card_after_training.png"])
            temp = card["assetbundle_name"] + "_rip/" + card_type
            card_url = urljoin(card_url, temp)
            logger.info("url - %s", card_url)
            card_urls.append(card_url)

            async with ClientSession() as session:
                async with session.get(url=card_url) as res:
                    if res.status != 200:
                        user = await self.bot.fetch_user(OWNER_SERVER_ID)
                        await user.send("Error fetching card")
                        logger.error(res)
                        await ctx.respond("Could not fetch a card at this time, please try again later!")
                        return
                    random_card = BytesIO(await res.read())
                    cards_list.append(discord.File(random_card, f"card{cards.index(card)}.png"))

        try:
            await ctx.followup.send(files=cards_list)
        except HTTPException:
            await ctx.followup.send("\n".join(card_urls))

def setup(bot):
    bot.add_cog(RandomCard(bot))