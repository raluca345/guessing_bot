import aiohttp
import discord
from discord.ext import commands, tasks
from storage.character_storage import CharacterStorage

from utility.utility_functions import logger
from utility.constants import *
import os
import tweepy.asynchronous


class TwtHub(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.character_list = CharacterStorage().characters_data
        self.character_names = [character["characterName"] for character in self.character_list]
        self.units = UNITS
        self.client = self.initialize_twitter_client()

    @commands.Cog.listener()
    async def on_ready(self):
        self.broadcast_tweets_to_channel.start()

    @staticmethod
    def initialize_twitter_client():
        client = None
        try:
            bearer_token = os.getenv('BEARER_TOKEN')
            if not bearer_token:
                raise ValueError("BEARER_TOKEN is not set in the environment variables.")
            client = tweepy.asynchronous.AsyncClient(bearer_token=bearer_token, wait_on_rate_limit=True)
            return client
        except Exception as e:
            logger.error(f"Error initializing Twitter client: {e}")

    @tasks.loop(minutes=1)
    async def broadcast_tweets_to_channel(self):
        if self.client:
            logger.info(self.bot.guilds)
            server = self.bot.get_guild(CGL_SERVER_ID)
            try:
                response = await self.client.get_users_tweets(CGL_TWT_TEST_ACC_ID, max_results=5, tweet_fields="created_at")
                if response.data:
                    tweet = response.data[0]
                    channel = None
                    role = None
                    message = ""
                    tweet_url = f"https://x.com/prskcgl/status/{tweet.id}"

                    if "will be held" in tweet.text:
                        channel = self.bot.get_channel(WEEK_ANNOUNCEMENT_CHANNEL)
                        role = discord.utils.get(server.roles, name="Week Announcement Ping")
                        first_line_in_twt = tweet.text.split("\n")[0].split(" ")
                        week_position = first_line_in_twt.index("Week")
                        week_number = first_line_in_twt[week_position + 1]
                        character_name = ""
                        character_two_name = ""
                        first_name_position = 0

                        # check if it's a special week
                        if week_position != 0:
                            type_of_week = first_line_in_twt[week_position - 1]
                            logger.info(f"Type of week: {type_of_week}")
                            if type_of_week == "Unit":
                                unit_word_position = type_of_week.index("Unit")
                                week_number = first_line_in_twt[first_line_in_twt.index("Week", week_position +1) + 1]
                                unit_name = " ".join(first_line_in_twt[:week_position - 1]).strip()
                                logger.info(f"Unit name: {unit_name}")
                                if unit_name in self.units:
                                    character_names = character_name_to_unit[unit_name]
                                    emoji_names = [f"{name}Stamp" for name in character_names]
                                    emoji_list = [discord.utils.get(server.emojis, name=name) for name in emoji_names]
                                    message = f"# {unit_name} Unit Week {week_number} has been announced!\n\nReach deathmatch to earn a {unit_name} stamp! {' '.join(str(emoji) for emoji in emoji_list)}\n\n@prskcgl tweeted {tweet_url}\n{role.mention}"
                            else:
                                last_line = tweet.text.split("\n")[-1].split(" ")
                                for name in self.character_names:
                                    if name in last_line:
                                        character_name = name
                                        break
                                emoji_name = f"{character_name}Stamp"
                                emoji = discord.utils.get(server.emojis, name=emoji_name)

                                message = f"# {type_of_week} Week {week_number} has been announced!\n\nReach deathmatch to earn a {character_name} stamp {emoji}!\n\n@prskcgl tweeted {tweet_url}\n{role.mention}"

                        # normal week
                        else:
                            last_line = tweet.text.split("\n")[-1].split(" ")
                            for name in self.character_names:
                                if name in last_line:
                                    first_name_position = last_line.index(name)
                                    character_name = name
                                    break
                            if (last_line[first_name_position + 1] == "and") and (last_line[first_name_position + 2] in self.character_names):
                                character_two_name = last_line[first_name_position + 2]

                            emoji_name = f"{character_name}Stamp"
                            emoji = discord.utils.get(server.emojis, name=emoji_name)
                            if character_two_name:
                                emoji_two_name = f"{character_two_name}Stamp"
                                emoji_two = discord.utils.get(server.emojis, name=emoji_two_name)
                                message = f"# Week {week_number} has been announced!\n\nReach deathmatch to earn a {character_name} and {character_two_name} stamp! {emoji} {emoji_two}\n\n@prskcgl tweeted {tweet_url}\n{role.mention}"
                            else:
                                message = f"# Week {week_number} has been announced!\n\nReach deathmatch to earn a {character_name} stamp! {emoji}\n\n@prskcgl tweeted {tweet_url}\n{role.mention}"
                    else:
                        channel = self.bot.get_channel(OTHER_ANNOUNCEMENT_CHANNEL)
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
                            logger.error(
                                "Bot does not have permission to send messages in the channel or view the message history.")
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

def setup(bot):
    bot.add_cog(TwtHub(bot))