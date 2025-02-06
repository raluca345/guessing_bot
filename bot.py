import os
from io import BytesIO

import discord
import aiohttp
from PIL import Image, ImageDraw
from discord.ext import commands, tasks
from dotenv import load_dotenv
from utility.utility_functions import logger, active_session, CGL_SERVER_ID, WEEK_ANNOUNCEMENT_CHANNEL, OTHER_ANNOUNCEMENT_CHANNEL, CGL_TWT_ACC_ID
import tweepy.asynchronous

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
    #broadcast_tweets_to_channel.start()

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

try:
    bearer_token = os.getenv('BEARER_TOKEN')
    if not bearer_token:
        raise ValueError("BEARER_TOKEN is not set in the environment variables.")
    client = tweepy.asynchronous.AsyncClient(bearer_token=bearer_token, wait_on_rate_limit=True)
except Exception as e:
    logger.error(f"Error initializing Twitter client: {e}")

async def check_server_permissions(channel_id):
    server = bot.get_guild(CGL_SERVER_ID)
    channel = bot.get_channel(channel_id)
    logger.info("Can the both send messages in this channel? %s", channel.permissions_for(server.me).send_messages)
    logger.info("Can the bot view this channel's history? %s", channel.permissions_for(server.me).read_message_history)

@tasks.loop(hours=24, reconnect=True)
async def broadcast_tweets_to_channel():
    if client:
        logger.info(bot.guilds)
        server = bot.get_guild(CGL_SERVER_ID)
        try:
            response = await client.get_users_tweets(CGL_TWT_ACC_ID, max_results=5, tweet_fields="created_at")
            if response.data:
                tweet = response.data[0]
                channel = None
                role = None
                message = ""
                tweet_url = f"https://x.com/prskcgl/status/{tweet.id}"

                if "Week" in tweet.text:
                    channel = bot.get_channel(WEEK_ANNOUNCEMENT_CHANNEL)
                    role = discord.utils.get(server.roles, name="Week Announcement Ping")
                    week_number = tweet.text.split(" ")[1]
                    character_name = "Emu"
                    emoji_name = f"{character_name}Stamp"
                    emoji = discord.utils.get(server.emojis, name=emoji_name)
                    message = f"# Week {week_number} has been announced!\n\nReach deathmatch to earn a {character_name} stamp! {emoji}\n\n@prskcgl tweeted {tweet_url}\n{role.mention}"
                else:
                    channel = bot.get_channel(OTHER_ANNOUNCEMENT_CHANNEL)
                    role = discord.utils.get(server.roles, name="Announcement Ping")
                    message = f"@prskcgl tweeted {tweet_url}\n{role.mention}"

                if channel:
                    try:
                        async for m in channel.history(limit=1):
                            logger.info(f"Last message in channel: {m.content}")
                            if tweet_url in m.content:
                                logger.info("No new tweets found.")
                                return
                        await channel.send(message)
                        logger.info(f"Sent message to channel {channel.name}")
                    except discord.Forbidden:
                        logger.error("Bot does not have permission to send messages in the channel or view the message history.")
                else:
                    logger.error("Channel not found or bot does not have access to the channel.")
                logger.info(f"Sent new tweet: {tweet.text}")
            else:
                logger.info("No new tweets found.")
        except aiohttp.ClientConnectionError as e:
            logger.error(f"Connection error fetching tweets: {e}")
            logger.error("Could not fetch tweets.")
        except tweepy.TweepyException as e:
            # Log the headers in case of a TweepyException
            if e.response:
                logger.error(f"Tweepy error: {e}")
                logger.error(f"Response Headers: {e.response.headers}")
            else:
                logger.error(f"Tweepy error: {e}")
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
    else:
        logger.error("Client is not initialized.")


bot.run(os.getenv("TOKEN"))