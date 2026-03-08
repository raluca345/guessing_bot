import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from storage.character_storage import CharacterStorage

from utility.utility_functions import logger
from utility.constants import *
import os
import tweepy
import tweepy.asynchronous

load_dotenv()


class _CglFilteredStream(tweepy.asynchronous.AsyncStreamingClient):
    def __init__(self, bearer_token: str, hub: "TwtHub"):
        super().__init__(bearer_token=bearer_token, wait_on_rate_limit=True)
        self._hub = hub

    async def on_tweet(self, tweet: tweepy.Tweet):
        await self._hub.handle_incoming_tweet(tweet)

    async def on_request_error(self, status_code):
        logger.error("Twitter stream request error: %s", status_code)

    async def on_connection_error(self):
        logger.error("Twitter stream connection error")

    async def on_exception(self, exception):
        logger.error("Twitter stream exception: %s", exception)

    async def on_disconnect(self):
        logger.warning("Twitter stream disconnected")


class TwtHub(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.character_list = CharacterStorage().characters_data
        self.character_names = [character["characterName"] for character in self.character_list]

        self.units = UNITS
        self.unit_to_character_names = unit_to_character_names

        self.stream: _CglFilteredStream | None = None
        self.stream_task: asyncio.Task | None = None

        self._last_sent_tweet_id: str | int | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self.stream_task is None:
            self.stream_task = asyncio.create_task(self.stream_worker())

    def cog_unload(self):
        if self.stream:
            try:
                self.stream.disconnect()
            except Exception:
                pass

        if self.stream_task:
            self.stream_task.cancel()

    async def stream_worker(self):
        bearer_token = os.getenv("BEARER_TOKEN")

        if not bearer_token:
            logger.error("BEARER_TOKEN is not set; Twitter stream disabled.")
            return

        while True:
            try:
                logger.info("Starting Twitter filtered stream")

                self.stream = _CglFilteredStream(bearer_token, self)

                await self._ensure_stream_rule()

                await self.stream.filter(
                    tweet_fields=["created_at", "author_id"],
                )

            except asyncio.CancelledError:
                logger.info("Twitter stream worker cancelled")
                if self.stream:
                    self.stream.disconnect()
                raise

            except Exception as e:
                logger.error("Twitter stream crashed: %s", e)

            logger.info("Restarting Twitter stream in 30 seconds")
            await asyncio.sleep(30)

    async def _ensure_stream_rule(self):
        if self.stream is None:
            return

        desired_value = f"from:{CGL_TWT_ACC_ID} -is:retweet -is:reply"
        desired_tag = "cgl-week-announcement"

        try:
            existing = await self.stream.get_rules()
            rules = list(getattr(existing, "data", None) or [])

            for rule in rules:
                if getattr(rule, "tag", None) == desired_tag:
                    if getattr(rule, "value", None) != desired_value:
                        await self.stream.delete_rules(rule.id)
                        await self.stream.add_rules(tweepy.StreamRule(desired_value, tag=desired_tag))
                    return

            await self.stream.add_rules(tweepy.StreamRule(desired_value, tag=desired_tag))
        except Exception as e:
            logger.error("Error ensuring Twitter stream rules: %s", e)

    def handle_normal_week(self, character_names_line, server, week_number, tweet_url, role):
        character_name = ""
        for name in self.character_names:
            if name in character_names_line:
                character_name = name
                break

        if character_name == "MEIKO":
            character_name = "Meiko"

        if character_name == "KAITO":
            character_name = "Kaito"

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

        for name in character_names:
            if name == "MEIKO":
                emoji_names.append("MeikoStamp")
                emoji_names.remove("MEIKOStamp")
            if name == "KAITO":
                emoji_names.append("KaitoStamp")
                emoji_names.remove("KAITOStamp")

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

            for name in character_names:
                if name == "MEIKO":
                    emoji_names.append("MeikoStamp")
                    emoji_names.remove("MEIKOStamp")
                if name == "KAITO":
                    emoji_names.append("KaitoStamp")
                    emoji_names.remove("KAITOStamp")

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

    def _build_week_announcement_message(self, tweet_text: str, server, tweet_url: str, role):
        first_line_in_twt = tweet_text.split("\n")[0].split()
        logger.info("First line in tweet: %s", first_line_in_twt)

        character_names_line = tweet_text.split("\n")[-1].split("!")[0].strip()
        logger.info("Character names line: %s", character_names_line)

        try:
            week_position = first_line_in_twt.index("Week")
            week_number = first_line_in_twt[week_position + 1]
        except (ValueError, IndexError):
            logger.error("Could not parse week number from tweet: %s", first_line_in_twt)
            return None

        if "Anniversary" in first_line_in_twt:
            return self.handle_everyone_week(week_number, tweet_url, role)

        if "Shuffle" in first_line_in_twt:
            try:
                week_position = first_line_in_twt.index("Week", week_position + 1)
                week_number = first_line_in_twt[week_position + 1]
            except (ValueError, IndexError):
                logger.error("Could not parse Shuffle Unit week number from tweet: %s", first_line_in_twt)
                return None
            return self.handle_shuffle_unit_week(character_names_line, server, week_number, tweet_url, role)

        if "Unit" in first_line_in_twt:
            try:
                week_position = first_line_in_twt.index("Week", week_position + 1)
                week_number = first_line_in_twt[week_position + 1]
            except (ValueError, IndexError):
                logger.error("Could not parse Unit week number from tweet: %s", first_line_in_twt)
                return None
            return self.handle_unit_week(first_line_in_twt, server, week_number, tweet_url, role)

        if "and" in character_names_line:
            return self.handle_kizuna_week(character_names_line, server, week_number, tweet_url, role)

        return self.handle_normal_week(character_names_line, server, week_number, tweet_url, role)

    async def handle_incoming_tweet(self, tweet: tweepy.Tweet):
        if tweet is None or not getattr(tweet, "text", None):
            return

        author_id = getattr(tweet, "author_id", None)
        if author_id is not None and str(author_id) != str(CGL_TWT_ACC_ID):
            return

        tweet_url = f"https://x.com/prskcgl/status/{tweet.id}"

        if self._last_sent_tweet_id == tweet.id:
            return

        if "will be held" not in tweet.text:
            return

        server = self.bot.get_guild(CGL_SERVER_ID)
        if server is None:
            logger.error("Server not found; cannot broadcast tweet")
            return

        channel = self.bot.get_channel(WEEK_ANNOUNCEMENT_CHANNEL)
        if channel is None:
            logger.error("Week announcement channel not found")
            return

        role = discord.utils.get(server.roles, name="Week Announcement Ping")
        if role is None:
            logger.error("Week Announcement Ping role not found")
            return

        message = self._build_week_announcement_message(tweet.text, server, tweet_url, role)
        if not message:
            return

        try:
            async for m in channel.history(limit=1):
                if tweet_url in getattr(m, "content", ""):
                    logger.info("Tweet already posted; skipping")
                    self._last_sent_tweet_id = tweet.id
                    return
            await channel.send(message)
            self._last_sent_tweet_id = tweet.id
            logger.info("Sent tweet announcement to channel %s", getattr(channel, "name", "<unknown>"))
        except discord.Forbidden:
            logger.error("Missing permission to send messages or read history in the channel")
        except Exception as e:
            logger.error("Error sending tweet announcement: %s", e)


def setup(bot):
    bot.add_cog(TwtHub(bot))
