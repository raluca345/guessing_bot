import os

import discord
from discord.ext import tasks
from dotenv import load_dotenv

from utility.utility_functions import logger, active_session
from utility.constants import *

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.dm_messages = True
intents.guilds = True

bot = discord.Bot(intents=intents, activity=discord.Game(name="Guessing cards and songs"))

cogs_list = [f.split(".")[0] for f in os.listdir(os.getcwd() + "/cogs") if not f.startswith("__")]
logger.info(cogs_list)

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
    
    if isinstance(error, discord.NotFound):
        logger.error(f"Interaction not found in channel {ctx.channel_id}: {error}")
        try:
            await ctx.channel.send("The interaction timed out. Please try the command again.", ephemeral=True)
        except discord.Forbidden:
            logger.error(f"Cannot send messages to channel {ctx.channel_id}")
        except Exception as e:
            logger.error(f"Failed to send error message to channel {ctx.channel_id}: {e}")
    elif isinstance(error, discord.Forbidden):
        logger.error(f"Missing permissions in channel {ctx.channel_id}: {error}")
    elif isinstance(error, discord.HTTPException):
        logger.error(f"HTTP error in channel {ctx.channel_id}: {error}")
        try:
            await ctx.followup.send("A network error occurred. Please try again!", ephemeral=True)
        except:
            try:
                await ctx.channel.send("A network error occurred. Please try again!", ephemeral=True)
            except:
                logger.error(f"Cannot send any messages to channel {ctx.channel_id}")
    else:
        try:
            await ctx.followup.send("Something went wrong, please try again!", ephemeral=True)
        except:
            try:
                await ctx.channel.send("Something went wrong, please try again!", ephemeral=True)
            except:
                logger.error(f"Cannot send any messages to channel {ctx.channel_id}")
    
    logger.error(f"Error in channel {ctx.channel_id}: {error}")

@bot.command(name="reload", guild_ids=[1076494695204659220],
            default_member_permissions=discord.Permissions(administrator=True))
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
    logger.info("Can the both send messages in this channel? %s",
                channel.permissions_for(server.me).send_messages)
    logger.info("Can the bot view this channel's history? %s",
                channel.permissions_for(server.me).read_message_history)


bot.run(os.getenv("TOKEN"))
