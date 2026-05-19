"""Admin utilities cog for owner-only commands."""
from contextlib import closing

import discord
from discord.ext import commands

from utility.utility_functions import logger
from utility.db import temp_connection


class Admin(commands.Cog):
    """Owner-only administrative commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @discord.slash_command(name="db_health", description="Owner: quick DB health check")
    async def db_health(self, ctx: discord.ApplicationContext):
        """Check database connection health and thread count."""
        await ctx.defer()
        try:
            with temp_connection() as conn:
                with closing(conn.cursor()) as cur:
                    cur.execute("SELECT 1")
                    one = cur.fetchone()
                    cur.execute("SHOW STATUS LIKE 'Threads_connected'")
                    threads = cur.fetchall()
            await ctx.followup.send(f"DB OK: {one}, Threads_connected: {threads}")
        except Exception as e:
            logger.exception("DB health check failed")
            await ctx.followup.send(f"DB ERROR: {e}")


def setup(bot):
    bot.add_cog(Admin(bot))

