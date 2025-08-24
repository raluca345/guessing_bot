import datetime
import aiohttp
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from storage.character_storage import CharacterStorage

from utility.utility_functions import logger
from utility.constants import *
import os
import tweepy.asynchronous

load_dotenv()


class TwtHub(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.character_list = CharacterStorage().characters_data
        self.character_names = [character["characterName"] for character in self.character_list]
        self.units = UNITS
        self.unit_to_character_names = unit_to_character_names
        self.client = self.initialize_twitter_client()

    @commands.Cog.listener()
    async def on_ready(self):
        self.broadcast_tweets_to_channel.start()

    @staticmethod
    def initialize_twitter_client():
        client = None
        try:
            bearer_token = os.getenv('BEARER_TOKEN_2')
            if not bearer_token:
                raise ValueError("BEARER_TOKEN_2 is not set in the environment variables.")
            client = tweepy.asynchronous.AsyncClient(bearer_token=bearer_token, wait_on_rate_limit=True)
            return client
        except Exception as e:
            logger.error(f"Error initializing Twitter client: {e}")

    def handle_normal_week(self, character_names_line, server, week_number, tweet_url, role):
        character_name = ""
        for name in self.character_names:
            if name in character_names_line:
                character_name = name
                break

        emoji_name = f"{character_name}Stamp"
        emoji = discord.utils.get(server.emojis, name=emoji_name)
        message = (f"# Week {week_number} has been announced!"
                   f"\n\nReach deathmatch to earn a {character_name} stamp {emoji}!"
                   f"\n\n@prskcgl tweeted {tweet_url}\n{role.mention}")
        return message

    def handle_kizuna_week(self, character_names_line, server, week_number, tweet_url, role):
        character_names = [name for name in self.character_names if name in character_names_line]
        logger.info("Character names: %s", character_names)
        emoji_names = [f"{name}Stamp" for name in character_names]
        emojis = [discord.utils.get(server.emojis, name=name) for name in emoji_names]
        logger.info("Emojis: %s", emojis)
        message = (f"# Week {week_number} has been announced!"
                   f"\n\nReach deathmatch to earn a {character_names[0]} stamp {emojis[0]}"
                   f" and a {character_names[1]} stamp {emojis[1]}!\n\n@prskcgl tweeted {tweet_url}\n{role.mention}")
        return message

    def handle_shuffle_unit_week(self, character_names_line, server, week_number, tweet_url, role):
        character_names = [name for name in self.character_names if name in character_names_line]
        logger.info("Character names: %s", character_names)
        emoji_names = [f"{name}Stamp" for name in character_names]

        for name in character_names:
            if name == "MEIKO":
                emoji_names.append("MeikoStamp")
                emoji_names.remove("MEIKOStamp")
            if name == "KAITO":
                emoji_names.append("KaitoStamp")
                emoji_names.remove("KAITOStamp")

        emojis = [discord.utils.get(server.emojis, name=name) for name in emoji_names]
        message = (f"# Shuffle Unit Week {week_number} has been announced!"
                   f"\n\nReach deathmatch to earn a shuffle unit stamp {' '.join(str(emoji) for emoji in emojis)}!"
                   f"\n\n@prskcgl tweeted {tweet_url}\n{role.mention}")
        return message

    def handle_unit_week(self, first_line, server, week_number, tweet_url, role):
        unit_word_position = first_line.index("Unit")
        unit_name = ' '.join(first_line[:unit_word_position])
        logger.info(f"Unit name: {unit_name}")
        if unit_name in self.units:
            character_names = self.unit_to_character_names[unit_name]
            emoji_names = [f"{name}Stamp" for name in character_names]
            logger.info(f"Emoji names: {emoji_names}")
            emojis = [discord.utils.get(server.emojis, name=name) for name in emoji_names]
            message = (f"# {unit_name} Unit Week {week_number} has been announced!"
                       f"\n\nReach deathmatch to earn a {unit_name} stamp {' '.join(str(emoji) for emoji in emojis)}!"
                       f"\n\n@prskcgl tweeted {tweet_url}\n{role.mention}")
            return message
        else:
            logger.error(f"Unit {unit_name} not found in units list.")
            return None

    @staticmethod
    def handle_everyone_week(week_number, tweet_url, role):
        message = (f"# Week {week_number} has been announced!"
                   f"\n\nReach deathmatch to earn a stamp of your choice!"
                   f"\n\n@prskcgl tweeted {tweet_url}\n{role.mention}")
        return message

    @tasks.loop(time=datetime.time(hour=13, minute=5))
    async def broadcast_tweets_to_channel(self):
        if self.client:
            logger.info(self.bot.guilds)
            server = self.bot.get_guild(CGL_SERVER_ID)
            try:
                response = await self.client.get_users_tweets(CGL_TWT_ACC_ID, max_results=5,
                                                              tweet_fields="created_at")
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
                        logger.info("First line in tweet: %s", first_line_in_twt)
                        character_names_line = tweet.text.split("\n")[-1].split("!")[0].strip()
                        logger.info("Character names line: %s", character_names_line)
                        week_position = first_line_in_twt.index("Week")
                        week_number = first_line_in_twt[week_position + 1]

                        if "Anniversary" in first_line_in_twt:
                            message = self.handle_everyone_week(week_number, tweet_url, role)

                        elif "Shuffle" in first_line_in_twt:
                            # 2 "weeks" so look for the second one, the number is after that one
                            # looks crappy so might change later
                            week_position = first_line_in_twt.index("Week", week_position + 1)
                            week_number = first_line_in_twt[week_position + 1]
                            message = self.handle_shuffle_unit_week(character_names_line, server,
                                                                    week_number, tweet_url, role)

                        elif "Unit" in first_line_in_twt:
                            # same thing as above
                            week_position = first_line_in_twt.index("Week", week_position + 1)
                            week_number = first_line_in_twt[week_position + 1]
                            message = self.handle_unit_week(first_line_in_twt, server,
                                                            week_number, tweet_url, role)

                        elif "and" in character_names_line:
                            message = self.handle_kizuna_week(character_names_line, server,
                                                              week_number, tweet_url, role)

                        else:
                            message = self.handle_normal_week(character_names_line, server,
                                                              week_number, tweet_url, role)

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
