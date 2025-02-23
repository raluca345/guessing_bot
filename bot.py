import os

import aiohttp
import discord
import tweepy.asynchronous
from discord.ext import tasks
from dotenv import load_dotenv

from utility.utility_functions import logger, active_session
from utility.constants import *

# Set up intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# Initialize the bot
bot = discord.Bot(intents=intents, activity=discord.Game(name="Guessing cards and songs"))

# List of cogs to be loaded
cogs_list = [f.split(".")[0] for f in os.listdir(os.getcwd() + "/cogs") if not f.startswith("__")]
logger.info(cogs_list)

# Load each cog
for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')

@bot.event
async def on_ready():
    logger.info(f"{bot.user} is online!")
    logger.info(f"Connected guilds: {bot.guilds}")
    await check_server_permissions(WEEK_ANNOUNCEMENT_CHANNEL)
    await check_server_permissions(OTHER_ANNOUNCEMENT_CHANNEL)

@bot.event
async def on_command_error(ctx: discord.ApplicationContext, error):
    active_session[ctx.channel_id] = False
    await ctx.followup.send("Something went wrong, please try again!", ephemeral=True)
    logger.error(error)

@bot.command(name="reload", guild_ids=[1076494695204659220], default_member_permissions=discord.Permissions(administrator=True))
async def reload(ctx, cog_name: discord.Option(choices=cogs_list)): #type: ignore
    if cog_name in cogs_list:
        bot.reload_extension(f"cogs.{cog_name}")
        await ctx.respond(f"Reloaded the {cog_name} cog", ephemeral=True)
    else:
        await ctx.respond("Couldn't find a cog with that name!", ephemeral=True)

load_dotenv()

async def check_server_permissions(channel_id):
    server = bot.get_guild(CGL_SERVER_ID)
    channel = bot.get_channel(channel_id)
    logger.info("Can the both send messages in this channel? %s", channel.permissions_for(server.me).send_messages)
    logger.info("Can the bot view this channel's history? %s", channel.permissions_for(server.me).read_message_history)


bot.run(os.getenv("TOKEN"))

# TODO: create a README.md file