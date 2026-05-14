import asyncio
import os
from dotenv import load_dotenv
import random
from io import BytesIO

import aiohttp
import discord
from PIL import Image
from discord.ext import commands, tasks

from storage.card_storage import CardStorage
from storage.character_storage import CharacterStorage
from storage.points_ledger_storage import PointsLedgerStorage
from utility.decorators import retry_async
from utility.utility_functions import logger, active_session
from utility.filters import build_card_filter_cache, get_cached_card_filter
from utility.r2 import connect_to_r2_storage, get_mask_from_r2, get_object_with_retry
from utility.image import generate_img_crop, generate_foreground_crop_from_mask
from utility.constants import UNITS, CARD_CROP_SIZE
from views.buttons import Buttons


class CardsGuessing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.card_list = CardStorage()
        self.character_list = CharacterStorage()
        self.ledger = PointsLedgerStorage()

        self.VERTICAL_CARDS = [
            "res013_no033",
            "res014_no034",
            "res015_no033",
            "res016_no033",
            "res018_no044",
        ]

        load_dotenv()
        self.s3 = connect_to_r2_storage()
        self.BUCKET_NAME = os.getenv("BUCKET_NAME")

        try:
            build_card_filter_cache(self.card_list.card_data)
        except Exception:
            logger.exception("Failed to build card filter cache at startup")

    def cog_unload(self) -> None:
        try:
            if hasattr(self, "update_card_list") and self.update_card_list.is_running():
                self.update_card_list.cancel()
        except Exception:
            pass

        try:
            if hasattr(self, "card_list") and self.card_list is not None:
                try:
                    self.card_list.close()
                except Exception:
                    pass
                self.card_list = None
        except Exception:
            pass

        try:
            if hasattr(self, "ledger") and self.ledger is not None:
                try:
                    self.ledger.close()
                except Exception:
                    pass
                self.ledger = None
        except Exception:
            pass

    # -------------------------
    # SLASH COMMAND GROUP
    # -------------------------

    cards = discord.SlashCommandGroup(
        "card",
        description="Given a card crop, guess the character it belongs to. Use endguess to give up",
    )

    async def start_game(self, ctx, filtered_cards):
        if active_session[ctx.channel_id]:
            await ctx.respond("Guessing has already started!")
            return

        active_session[ctx.channel_id] = True

        try:
            @retry_async(retries=3, delay=2)
            async def defer_with_retry(context):
                await context.defer()
            try:
                await defer_with_retry(ctx)
            except (discord.HTTPException, discord.errors.NotFound, aiohttp.ClientOSError, ConnectionResetError, asyncio.TimeoutError, asyncio.CancelledError) as e:
                logger.warning(f"Defer failed, continuing without defer: {e}")

            await self.card_guess_helper(ctx, filtered_cards)

        except (asyncio.TimeoutError, asyncio.CancelledError) as e:
            logger.error(f"start_game network error: {e}")
            await ctx.respond("Network error occurred. Please try again later.")
        except Exception:
            logger.exception("start_game failed")

        finally:
            active_session[ctx.channel_id] = False

    @cards.command(name="guess", description="Guess from all cards! (1*s excluded)")
    async def guess_card(self, ctx: discord.ApplicationContext):
        await self.start_game(ctx, self.card_list.card_data)

    @cards.command(name="fourstarguess", description="Guess from all 4* cards!")
    async def guess_four_star(self, ctx):
        await self.start_game(ctx, get_cached_card_filter("four_star", self.card_list.card_data))

    @cards.command(name="threestarguess", description="Guess from all 3* cards!")
    async def guess_three_star(self, ctx):
        await self.start_game(ctx, get_cached_card_filter("three_star", self.card_list.card_data))

    @cards.command(name="notwostarguess", description="Guess from all cards that aren't 2*!")
    async def guess_no_two_star(self, ctx):
        await self.start_game(ctx, get_cached_card_filter("no_two_star", self.card_list.card_data))

    @cards.command(name="twostarguess", description="Guess from all 2* cards!")
    async def guess_two_star(self, ctx):
        await self.start_game(ctx, get_cached_card_filter("two_star", self.card_list.card_data))

    @cards.command(name="bdayguess", description="Guess from all birthday rarity cards!")
    async def guess_birthday(
        self,
        ctx,
        rotation: discord.Option(
            discord.SlashCommandOptionType.integer,
            required=False,
            description="Birthday rotation",
        ) = None, #type: ignore
    ):
        if rotation:
            await self.start_game(ctx, get_cached_card_filter(f"birthday{rotation}", self.card_list.card_data))
        else:
            await self.start_game(ctx, get_cached_card_filter("birthday", self.card_list.card_data))

    @cards.command(name="collabguess", description="Guess from collaboration cards!")
    async def guess_collab(self, ctx):
        await self.start_game(ctx, get_cached_card_filter("collab", self.card_list.card_data))

    @cards.command(name="tamagotchiguess", description="Guess from tamagotchi cards!")
    async def guess_tamagotchi(self, ctx):
        await self.start_game(ctx, get_cached_card_filter("tamagotchi", self.card_list.card_data))

    @cards.command(name="sanrioguess", description="Guess from sanrio cards!")
    async def guess_sanrio(self, ctx):
        await self.start_game(ctx, get_cached_card_filter("sanrio", self.card_list.card_data))

    @cards.command(name="movieguess", description="Guess from movie cards!")
    async def guess_movie(self, ctx):
        await self.start_game(ctx, get_cached_card_filter("movie", self.card_list.card_data))

    @cards.command(name="unitguess", description="Guess from cards from a specific unit!")
    async def guess_unit(self, ctx, unit: discord.Option(str, choices=UNITS)):  # type: ignore
        cards_filtered = get_cached_card_filter(f"unit:{unit}", self.card_list.card_data) or self.card_list.card_data
        await self.start_game(ctx, cards_filtered)

    # -------------------------
    # GAME CORE
    # -------------------------

    async def card_guess_helper(self, ctx: discord.ApplicationContext, filtered_cards_list):
        leaderboard = self.bot.get_cog("Lb")
        ch_id = getattr(ctx, "channel_id", None) or (
            ctx.channel.id if getattr(ctx, "channel", None) else None
        )

        try:
            card = random.choice(filtered_cards_list)

            character = next(
                (c for c in self.character_list.characters_data
                if c.get("characterId") == card["character_id"])
            )

            # -------------------------
            # ORIGINAL CARD TYPE LOGIC
            # -------------------------
            if card["card_rarity_type"] in ["rarity_2", "rarity_birthday"]:
                card_type = "normal.png"
            else:
                card_type = random.choice(["normal.png", "after_training.png"])

            card_name = card["en_prefix"] if card["en_prefix"] else card["prefix"]
            card_key = f"cards/card_{card['id']}_{card_type}"

            # -------------------------
            # FETCH IMAGE
            # -------------------------
            obj = get_object_with_retry(self.s3, self.BUCKET_NAME, card_key)
            buffer = BytesIO(obj["Body"].read())
            img = Image.open(buffer)
            og_img = img.copy()

            # -------------------------
            # VERTICAL CARD ROTATION
            # -------------------------
            if (
                card["assetbundle_name"] in self.VERTICAL_CARDS
                and card_type == "after_training.png"
            ):
                img = img.rotate(270, expand=True)
                og_img = img.copy()

            # -------------------------
            # 2★ MASK LOGIC
            # -------------------------
            if card["card_rarity_type"].strip() == "rarity_2":
                mask_key = f"masks/card_{card['id']}_normal.npz"
                alpha = get_mask_from_r2(self.s3, self.BUCKET_NAME, mask_key)
                region = generate_foreground_crop_from_mask(img, alpha, CARD_CROP_SIZE)
            else:
                region = generate_img_crop(img, CARD_CROP_SIZE)

            with BytesIO() as image_binary:
                # Send cropped image
                region.save(image_binary, "PNG", quality=95, optimize=True)
                image_binary.seek(0)
                picture = discord.File(fp=image_binary, filename="card.png")
                await ctx.followup.send(file=picture)

                # answer
                image_binary.truncate(0)
                image_binary.seek(0)

                s = og_img.size
                s = s[0] // 4, s[1] // 4
                og_img = og_img.resize(s)

                og_img.save(image_binary, "PNG", quality=95, optimize=True)
                image_binary.seek(0)
                answer = discord.File(fp=image_binary, filename="answer.png")

                # -------------------------
                # GUESS LOOP
                # -------------------------
                while True:
                    try:
                        guess = await self.bot.wait_for(
                            "message",
                            check=lambda m: (
                                m.author != self.bot
                                and m.channel == ctx.channel
                                and not m.author.bot
                            ),
                            timeout=30.0,
                        )

                        finished = await self.check_guess(
                            ctx,
                            guess,
                            character,
                            card_name,
                            answer,
                            leaderboard,
                            filtered_cards_list,
                            card,  # needed for ledger
                        )

                        if finished:
                            break

                    except asyncio.TimeoutError:
                        buttons_view = Buttons(
                            ctx,
                            ["Play Again"],
                            self.card_guess_helper,
                            [filtered_cards_list],
                        )
                        sent = await ctx.followup.send(
                            f"Time's up! It was **{character['characterLastName']} "
                            f"{character['characterName']}** - **{card_name}**!",
                            file=answer,
                            view=buttons_view,
                        )
                        buttons_view.message = sent
                        break

        finally:
            if ch_id is not None:
                active_session[ch_id] = False
    # -------------------------
    # CHECK GUESS
    # -------------------------

    async def check_guess(
    self,
    ctx,
    guess,
    character,
    card_name,
    answer,
    leaderboard,
    filtered_cards_list,
    card,
):
        try:
            content = guess.content.lower().strip()

            if content.startswith("."):
                return False

            # wrong-character pools
            all_character_aliases_but_the_right_one = [
                a for c in self.character_list.characters_data
                for a in c["aliases"]
                if c["characterName"] != character["characterName"]
            ]

            all_character_names_but_the_right_one = [
                c["characterName"].lower()
                for c in self.character_list.characters_data
                if c["characterName"] != character["characterName"]
            ]

            # -------------------------
            # CORRECT GUESS
            # -------------------------
            correct = (
                content == character["characterName"].lower()
                or content in character["aliases"]
                or content.strip("-") in character["aliases"]
                or content.strip("-") == character["characterName"].lower()
            )

            if correct:
                buttons_view = Buttons(
                    ctx,
                    ["Play Again"],
                    self.card_guess_helper,
                    [filtered_cards_list],
                )
                sent = await ctx.followup.send(
                    f'Congrats {guess.author.mention}! You guessed '
                    f'**{character["characterLastName"]} {character["characterName"]}** '
                    f'- **{card_name}** correctly!',
                    file=answer,
                    view=buttons_view,
                )
                buttons_view.message = sent

                guild_id = ctx.guild.id if ctx.guild else 0
                channel_id = ctx.channel.id if ctx.channel else 0
                user_id = guess.author.id

                # Ledger write (non-blocking)
                try:
                    await asyncio.to_thread(
                        self.ledger.record_points,
                        guild_id,
                        channel_id,
                        user_id,
                        1,
                        "card_guess",
                        card.get("id"),
                        sent.id,
                    )
                except Exception:
                    logger.exception("Ledger insert failed")

                if leaderboard:
                    await leaderboard.on_right_guess(user_id)

                return True

            # -------------------------
            # END GUESS
            # -------------------------
            if content == "endguess":
                buttons_view = Buttons(
                    ctx,
                    ["Play Again"],
                    self.card_guess_helper,
                    [filtered_cards_list],
                )
                sent = await ctx.followup.send(
                    f'Giving up? It was **{character["characterLastName"]} '
                    f'{character["characterName"]}** - **{card_name}**!',
                    file=answer,
                    view=buttons_view,
                )
                buttons_view.message = sent
                return True

            # -------------------------
            # WRONG BUT VALID CHARACTER
            # -------------------------
            if (
                content in all_character_aliases_but_the_right_one
                or content in all_character_names_but_the_right_one
                or content.strip("-") in all_character_names_but_the_right_one
                or content.strip("-") in all_character_aliases_but_the_right_one
            ):
                wrong_chara_last_name = next(
                    (
                        c["characterLastName"]
                        for c in self.character_list.characters_data
                        if content in c["aliases"]
                        or content.strip("-") in c["aliases"]
                        or content == c["characterName"].lower()
                        or content.strip("-") == c["characterName"].lower()
                    ),
                    "",
                )

                wrong_chara_name = next(
                    (
                        c["characterName"]
                        for c in self.character_list.characters_data
                        if content in c["aliases"]
                        or content.strip("-") in c["aliases"]
                        or content == c["characterName"].lower()
                        or content.strip("-") == c["characterName"].lower()
                    ),
                    "",
                )

                await ctx.followup.send(
                    f"Nope, it's not **{wrong_chara_last_name} {wrong_chara_name}**, try again!"
                )
                return False

            # -------------------------
            # COMPLETELY WRONG INPUT
            # -------------------------
            await ctx.channel.send("Nope, try again!")
            return False

        except Exception:
            logger.exception("check_guess error")
            return False

    # -------------------------
    # UPDATE LOOP
    # -------------------------

    @tasks.loop(hours=24)
    async def update_card_list(self):
        try:
            if hasattr(self, "card_list") and self.card_list is not None:
                try:
                    self.card_list.close()
                except Exception:
                    pass
        except Exception:
            pass

        self.card_list = CardStorage()
        build_card_filter_cache(self.card_list.card_data)
        logger.info("Updated card DB")


def setup(bot):
    bot.add_cog(CardsGuessing(bot))
