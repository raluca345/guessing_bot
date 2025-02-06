import asyncio
import math

import discord
from discord.ext import commands, tasks
from discord.ext.pages import Page
from discord import EmbedAuthor

from leaderboard.leaderboard import Leaderboard
from utility.utility_functions import *


class Lb(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lb_user_list = []
        self.pages = []
        self.leaderboard = Leaderboard()

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(600)
        self.leaderboard_update.start()

    async def on_right_guess(self, user_id):
        # gets all user ids
        user_ids = [x["user_id"] for x in self.lb_user_list]
        if user_id not in user_ids:
            self.lb_user_list.append({"user_id": user_id, "points": 1})
        else:
            # gets the dict that has user_id as key
            temp = next((x for x in self.lb_user_list if x["user_id"] == user_id))
            temp["points"] += 1
        logger.info(self.lb_user_list)


    @discord.command(name="lb", description="View the leaderboard; updates every 10 minutes")
    async def view_lb(self, ctx):
        if self.pages:
            await Leaderboard.lb_pages(ctx, self.pages)
        else:
            await ctx.respond("Please wait for the leaderboard to update!")

    @tasks.loop(minutes=10)
    async def leaderboard_update(self):
        self.pages = await self.create_lb()
        self.lb_user_list = []
        logger.info("Updated db!")

    @leaderboard_update.after_loop
    async def on_leaderboard_update_cancel(self):
        if self.leaderboard_update.is_being_cancelled() and len(self.lb_user_list) != 0:
            await self.create_lb()
            logger.info("Updated db!")

    async def create_lb(self):
        pages = []
        self.leaderboard.add_users(self.lb_user_list)
        self.leaderboard.get_data()
        self.lb_user_list = self.leaderboard.user_lb
        self.lb_user_list = sorted(self.lb_user_list, key=lambda x: x["points"], reverse=True)

        per_page = 10
        total_pages = math.ceil(len(self.lb_user_list) / per_page)

        for page in range(total_pages):
            embed = discord.Embed(title="Guessing Leaderboard", color=discord.Color.teal())
            user_column = "\n\n"
            points_column = "\n\n"

            for idx, user in enumerate(self.lb_user_list[page * per_page:(page + 1) * per_page], start=page * per_page + 1):
                user_id = user["user_id"]
                points = user["points"]

                user_obj = await self.bot.fetch_user(user_id)
                user_name = user_obj.name
                # avoid accidental italics in the leaderboard
                index = user_name.find("_")

                if index !=-1:
                    user_name = user_name[:index] + "\\" + user_name[index:]

                # Replace numbers with emojis for the top 3 on the first page
                if page == 0:
                    if idx == 1:
                        position = "🥇"
                    elif idx == 2:
                        position = "🥈"
                    elif idx == 3:
                        position = "🥉"
                    else:
                        position = f"   **{idx}.**"
                else:
                    position = f"   **{idx}.**"

                user_column += f"{position} {user_name}\n"
                points_column += f"{points}\n"

            embed.add_field(name="user", value=user_column, inline=True)
            embed.add_field(name="points", value=points_column, inline=True)
            embed.set_footer(text="Updates every 10 minutes")

            page = Page(embeds=[embed])
            pages.append(page)

        return pages

def setup(bot):
    bot.add_cog(Lb(bot))