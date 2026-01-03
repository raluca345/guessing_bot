import asyncio
import math

import discord
from discord.ext import commands, tasks
from discord.ext.pages import Page

from leaderboard.leaderboard import Leaderboard
from utility.utility_functions import *


class Lb(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lb_user_list = []
        self.pages = []
        self.leaderboard = Leaderboard()
        self._update_lock = asyncio.Lock()

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(600)
        if not self.leaderboard_update.is_running():
            self.leaderboard_update.start()

    async def on_right_guess(self, user_id):
        user_ids = [x["user_id"] for x in self.lb_user_list]
        if user_id not in user_ids:
            self.lb_user_list.append({"user_id": user_id, "points": 1})
        else:
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
        async with self._update_lock:
            self.pages = []
            self.pages = await self.create_lb()
            self.lb_user_list = []
            logger.info("Updated db!")

    @leaderboard_update.after_loop
    async def on_leaderboard_update_cancel(self):
        if self.leaderboard_update.is_being_cancelled() and len(self.lb_user_list) != 0:
            async with self._update_lock:
                await self.create_lb()
                self.lb_user_list = []
                logger.info("Updated db!")

    async def create_lb(self):
        pages = []
        deltas = [{"user_id": u["user_id"], "points": u["points"]} for u in self.lb_user_list]
        if deltas:
            self.leaderboard.add_users(deltas)

        self.leaderboard.get_data()
        db_users = sorted(list(self.leaderboard.user_lb), key=lambda x: x["points"], reverse=True)

        filtered_users = []
        for u in db_users:
            user_id = u["user_id"]
            points = u["points"]
            try:
                user_obj = self.bot.get_user(user_id)
                if user_obj is None:
                    try:
                        user_obj = await self.bot.fetch_user(user_id)
                    except discord.NotFound:
                        logger.warning(f"[create_lb] User not found or not visible to bot: {user_id}")
                        user_name = f"UnknownUser_{user_id}"
                    else:
                        user_name = user_obj.name
                else:
                    user_name = user_obj.name

            except Exception as e:
                logger.exception(f"[create_lb] Failed fetching user {user_id}: {e}")
                user_name = f"UnknownUser_{user_id}"

            filtered_users.append({"user_id": user_id, "points": points, "display_name": user_name})

        per_page = 10
        total_pages = math.ceil(len(filtered_users) / per_page) if filtered_users else 1

        for page_idx in range(total_pages):
            embed = discord.Embed(title="Guessing Leaderboard", color=discord.Color.teal())
            leaderboard_content = ""

            for idx, user in enumerate(filtered_users[page_idx * per_page:(page_idx + 1) * per_page],
                                    start=page_idx * per_page + 1):
                user_id = user["user_id"]
                points = user["points"]
                user_name = user["display_name"]

                if page_idx == 0:
                    if idx == 1:
                        position = "🥇"
                    elif idx == 2:
                        position = "🥈"
                    elif idx == 3:
                        position = "🥉"
                    else:
                        position = f"**{idx}.**"
                else:
                    position = f"**{idx}.**"

                leaderboard_content += f"{position} {user_name} - {points} points\n"

            if not leaderboard_content:
                leaderboard_content = "No entries"

            embed.add_field(name="Leaderboard", value=leaderboard_content, inline=False)
            embed.set_footer(text="Updates every 10 minutes")

            page = Page(embeds=[embed])
            pages.append(page)

        return pages

def setup(bot):
    bot.add_cog(Lb(bot))