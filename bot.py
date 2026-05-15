import os
import asyncio
import signal

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utility.utility_functions import logger, active_session
from utility.constants import *

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.dm_messages = True
intents.guilds = True
intents.members = True


bot = discord.Bot(intents=intents, activity=discord.Game(name="Guessing cards and songs"))

# Load all cogs EXCEPT twt_hub (which is DEPRECATED and disabled by default).
# The Twitter API free tier has been discontinued so this functionality can't be supported anymore
cogs_list = [f.split(".")[0] for f in os.listdir(os.getcwd() + "/cogs") if not f.startswith("__") and f.split(".")[0] not in ["twt_hub", "base_guessing_cog"]]
logger.info(f"Loading cogs: {cogs_list}")

for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')


SKIP_CHANNEL_IDS: set[int] = {1074836993575501826}
SKIP_CHANNEL_NAMES = {"cgl-lounge"}


async def send_error_message(ctx: discord.ApplicationContext, message: str) -> bool:
    """Try to send error message. Returns True if sent."""
    try:
        # Try followup first (works if ctx was deferred)
        await ctx.followup.send(message, ephemeral=True)
        return True
    except (discord.NotFound, discord.HTTPException, AttributeError):
        pass
    try:
        # Fallback to channel send
        await ctx.channel.send(message)
        return True
    except (discord.Forbidden, discord.HTTPException):
        pass
    return False


@bot.event
async def on_ready():
    logger.info(f"{bot.user} is online!")
    logger.info(f"Connected guilds: {bot.guilds}")
    await check_server_permissions(WEEK_ANNOUNCEMENT_CHANNEL)
    await check_server_permissions(OTHER_ANNOUNCEMENT_CHANNEL)

@bot.event
async def on_command_error(ctx: discord.ApplicationContext, error):
    """Handle command errors and reset session state."""
    if ctx.channel_id:
        active_session[ctx.channel_id] = False
    
    # Log the error with context
    logger.error(f"Error in channel {ctx.channel_id}: {type(error).__name__}: {error}")
    
    # Determine user-facing message based on error type
    if isinstance(error, discord.NotFound):
        user_message = "The interaction timed out. Please try the command again."

    elif isinstance(error, discord.Forbidden):
        logger.error(f"Missing permissions in channel {ctx.channel_id}")
        return  # Can't send messages if forbidden
    
    elif isinstance(error, (asyncio.TimeoutError, asyncio.CancelledError)):
        user_message = "Network timeout occurred. Please try again!"

    elif isinstance(error, discord.HTTPException):
        user_message = "A network error occurred. Please try again!"
        
    else:
        user_message = "Something went wrong. Please try again!"
    
    # Try to send error message to user
    if not await send_error_message(ctx, user_message):
        logger.error(f"Failed to send error message to channel {ctx.channel_id}")


@bot.command(name="reload", guild_ids=[1076494695204659220],
            default_member_permissions=discord.Permissions(administrator=True))
@commands.is_owner()
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


def shutdown_handler(signum, frame):
    """Handle SIGTERM and gracefully close the bot"""
    logger.info("Received shutdown signal, closing bot gracefully...")
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(bot.close())
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

bot.run(os.getenv("TOKEN"))