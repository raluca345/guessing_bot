"""
DEPRECATED: Twitter/X integration cog.

This cog is no longer actively maintained and has been disabled by default.
The implementation called called the Twitter API, but its free tier has been discontinued.

WARNING: Do not manually load this cog in production. It will be removed
in a future version.
"""

import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from storage.character_storage import CharacterStorage

from utility.utility_functions import logger
from utility.decorators import retry_async
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
    """DEPRECATED: Twitter/X integration cog. Do not use in production."""

    def __init__(self, bot):
        self.bot = bot
        self.character_list = CharacterStorage().characters_data
        self.character_names = [c["characterName"] for c in self.character_list]

        self.units = UNITS
        self.unit_to_character_names = unit_to_character_names

        self.stream: _CglFilteredStream | None = None
        self.stream_task: asyncio.Task | None = None

        self._last_sent_tweet_id: str | int | None = None
        self._shutting_down: bool = False
        self._rules_set: bool = False  # avoid repeated get_rules calls

    @commands.Cog.listener()
    async def on_ready(self):
        if self.stream_task is None:
            self.stream_task = asyncio.create_task(self._stream_worker())

    def cog_unload(self):
        self._shutting_down = True
        if self.stream_task:
            self.stream_task.cancel()
        if self.stream:
            try:
                self.stream.disconnect()
            except Exception:
                pass

    async def _stream_worker(self):
        bearer_token = os.getenv("BEARER_TOKEN_2")
        if not bearer_token:
            logger.error("BEARER_TOKEN_2 not set; Twitter stream disabled.")
            return

        reconnect_delay = 1  # exponential backoff in seconds

        while not self._shutting_down:
            try:
                logger.info("Starting Twitter filtered stream")

                self.stream = _CglFilteredStream(bearer_token, self)

                if not self._rules_set:
                    await self._ensure_stream_rule()
                    self._rules_set = True

                # Run stream; backfill last 5 minutes
                await self.stream.filter(
                    tweet_fields=["created_at", "author_id"],
                    backfill_minutes=40
                )

                reconnect_delay = 1  # reset on success

            except asyncio.CancelledError:
                logger.info("Twitter stream worker cancelled")
                if self.stream:
                    self.stream.disconnect()
                break

            except Exception as e:
                logger.error("Twitter stream crashed: %s", e)
                if self.stream:
                    self.stream.disconnect()

                # Exponential backoff for reconnects to save credits
                logger.info("Reconnecting in %s seconds", reconnect_delay)
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 300)  # max 5 min

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

            # Add rule if it didn't exist
            await self.stream.add_rules(tweepy.StreamRule(desired_value, tag=desired_tag))

        except Exception as e:
            logger.error("Error ensuring Twitter stream rules: %s", e)

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
            # Dedup within channel history
            async for m in channel.history(limit=1):
                if tweet_url in getattr(m, "content", ""):
                    self._last_sent_tweet_id = tweet.id
                    return

            @retry_async(retries=3, delay=2)
            async def send_with_retry(chan, msg):
                await chan.send(msg)
            await send_with_retry(channel, message)

            self._last_sent_tweet_id = tweet.id
            logger.info("Sent tweet announcement to channel %s", getattr(channel, "name", "<unknown>"))

        except discord.Forbidden:
            logger.error("Missing permission to send messages or read history in the channel")
        except (asyncio.TimeoutError, asyncio.CancelledError) as e:
            logger.error(f"Error sending tweet announcement (network): {e}")
        except Exception as e:
            logger.error(f"Error sending tweet announcement: {e}")


def setup(bot):
    """Setup function for TwtHub cog. DEPRECATED — do not load."""
    logger.warning(
        "=" * 80
        + "\n"
        + "DEPRECATION WARNING: TwtHub cog setup() called.\n"
        + "This cog is no longer maintained and is disabled by default.\n"
        + "If loaded manually, it will consume significant API quota.\n"
        + "Please remove any manual loading of this cog from your configuration.\n"
        + "=" * 80
    )
    bot.add_cog(TwtHub(bot))