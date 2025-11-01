import asyncio
import random
from io import BytesIO
from urllib.parse import urljoin

import discord
from aiohttp import ClientSession
from discord.ext import commands, tasks
from dotenv import load_dotenv
from views.buttons import Buttons

from storage.card_storage import CardStorage
from storage.character_storage import CharacterStorage
from utility.utility_functions import *
from utility.constants import *

# ty kana5 mafuyu for joining the gang
VERTICAL_CARDS = ["res013_no033", "res014_no034", "res015_no033", "res016_no033", "res018_no044"]

class CardsGuessing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.card_list = CardStorage()
        self.character_list = CharacterStorage()
        self.four_stars_list = four_star_filter(self.card_list.card_data)
        self.three_stars_list = three_star_filter(self.card_list.card_data)
        self.two_stars_list = two_star_filter(self.card_list.card_data)
        self.sanrio_list = sanrio_filter(self.card_list.card_data)
        self.birthday_list = birthday_filter(self.card_list.card_data)
        self.birthday1_list = birthday1_filter(self.card_list.card_data)
        self.birthday2_list = birthday2_filter(self.card_list.card_data)
        self.birthday3_list = birthday3_filter(self.card_list.card_data)
        self.birthday4_list = birthday4_filter(self.card_list.card_data)
        self.no_two_stars_list = no_two_star_filter(self.card_list.card_data)
        self.VERTICAL_CARDS = ["res013_no033", "res014_no034", "res015_no033", "res016_no033", "res018_no044"]
        load_dotenv()
        self.s3 = connect_to_r2_storage()
        self.BUCKET_NAME = os.getenv("BUCKET_NAME")

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(86400)
        self.update_card_list.start()

    def cog_unload(self) -> None:
        self.update_card_list.cancel()

    cards = discord.SlashCommandGroup("card",
                                      description="Given a card crop, guess the character it belongs to. Use **endguess** to give up")

    @cards.command(name="guess",
                   description="Guess from all cards! (1*s excluded)")
    async def guess_card(self, ctx):
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True

        await ctx.defer()
        try:
            await self.card_guess_helper(ctx, self.card_list.card_data)
        finally:
            active_session[ctx.channel_id] = False

    async def card_guess_helper(self, ctx: discord.ApplicationContext, filtered_cards_list):
        leaderboard = self.bot.get_cog("Lb")

        card = random.choice(filtered_cards_list)
        logger.info(card)
        character = next(
            (c for c in self.character_list.characters_data if c.get("characterId") == card["character_id"]))
        logger.info(character)
        all_character_aliases_but_the_right_one = [a for c in self.character_list.characters_data for a in c["aliases"]
                                                   if c["characterName"] != character["characterName"]]
        all_character_names_but_the_right_one = [c["characterName"].lower() for c in self.character_list.characters_data
                                                 if c["characterName"] != character["characterName"]]
        logger.info(all_character_aliases_but_the_right_one)
        logger.info(all_character_names_but_the_right_one)

        if card["card_rarity_type"] in ["rarity_2", "rarity_birthday"]:
            card_type = "normal.png"
        else:
            card_type = random.choice(["normal.png", "after_training.png"])

        if card["en_prefix"] != "":
            card_name = card["en_prefix"]
        else:
            card_name = card["prefix"]

        card_key = f"cards/card_{card['id']}_{card_type}"

        logger.info("url - %s", card_key)
        try:
            logger.info(f"Fetching card from R2 - bucket: {self.BUCKET_NAME}, key: {card_key}")
            obj = self.s3.get_object(Bucket=self.BUCKET_NAME, Key=card_key)
            buffer = BytesIO(obj['Body'].read())
            img = Image.open(buffer)
            og_img = img.copy()
        except Exception as e:
            logger.error(f"Error fetching image from R2: {e}")
            user = await self.bot.fetch_user(OWNER_ID)
            await user.send("Error fetching card from R2")
            await ctx.respond("Could not fetch a card at this time, please try again later!")
            active_session[ctx.channel_id] = False
            return

        if card["assetbundle_name"] in self.VERTICAL_CARDS and card_type == "card_after_training.png":
            img = img.rotate(270, expand=True)
            og_img.resize(img.size)
            og_img = img.copy()

        if card["card_rarity_type"].strip() == "rarity_2":
            w, h = img.size
            box = (w // 6, 0, w - w // 6, h)
            img = img.crop(box)

        region = generate_img_crop(img, CARD_CROP_SIZE)
        with BytesIO() as image_binary:
            region.save(image_binary, 'PNG', quality=95, optimize=True)
            image_binary.seek(0)
            picture = discord.File(fp=image_binary, filename="card.png")
            try:
                await ctx.respond(file=picture)
            except discord.errors.NotFound:
                await ctx.send("Something went wrong, try again!")
                active_session[ctx.channel_id] = False
                return

            image_binary.truncate(0)
            image_binary.seek(0)
            s = og_img.size
            s = s[0] // 4, s[1] // 4
            og_img = og_img.resize(s)
            og_img.save(image_binary, 'PNG', quality=95, optimize=True)
            image_binary.seek(0)
            answer = discord.File(fp=image_binary, filename="answer.png")
        while True:
            try:
                guess = await self.bot.wait_for('message', check=lambda
                    message: message.author != self.bot and message.channel == ctx.channel and not message.author.bot,
                                                timeout=30.0)
                is_finished = await self.check_guess(ctx, guess, character, card_name, answer, leaderboard, filtered_cards_list)
                if is_finished:
                    break
            except asyncio.TimeoutError:
                await ctx.followup.send(
                    f"Time's up! It was **{character['characterLastName']}  {character['characterName']}** - **{card_name}**!",
                    file=answer, view=Buttons(ctx, ["Play Again"], self.card_guess_helper, [filtered_cards_list]))
                break

    async def check_guess(self, ctx, guess, character, card_name, answer, leaderboard, filtered_cards_list):
        all_character_aliases_but_the_right_one = [a for c in self.character_list.characters_data for a 
                                                   in c["aliases"]
                                                   if c["characterName"] != character["characterName"]]
        all_character_names_but_the_right_one = [c["characterName"].lower() for c
                                                in self.character_list.characters_data 
                                                if c["characterName"] != character["characterName"]]
        if guess.content.lower().strip() == character[
            "characterName"].lower() or guess.content.lower().strip() in \
                character["aliases"] or guess.content.lower().strip("-").strip() in character[
            "aliases"] or guess.content.lower().strip("-").strip() == character["characterName"].lower():
            await ctx.followup.send(
                f'Congrats {guess.author.mention}! You guessed **{character["characterLastName"] + " " + character["characterName"]}** - **{card_name}** correctly!',
                file=answer, view=Buttons(ctx, ["Play Again"], self.card_guess_helper, [filtered_cards_list]))
            user_id = guess.author.id
            if leaderboard is not None:
                await leaderboard.on_right_guess(user_id)
            else:
                await ctx.followup.send("Error updating lb")
                logger.error("Error updating lb")
            return True
        elif guess.content.lower().strip() == "endguess":
            await ctx.followup.send(
                f'Giving up? It was **{character["characterLastName"] + " " + character["characterName"]}** - **{card_name}**!',
                file=answer, view=Buttons(ctx, ["Play Again"], self.card_guess_helper, [filtered_cards_list]))
            return True
        else:
            if guess.content.lower().strip() in all_character_aliases_but_the_right_one or guess.content.lower().strip() in all_character_names_but_the_right_one or guess.content.lower().strip(
                    "-").strip() in all_character_names_but_the_right_one or guess.content.lower().strip(
                "-").strip() in all_character_aliases_but_the_right_one:
                wrong_chara_last_name = next(
                    (c["characterLastName"] for c in self.character_list.characters_data if
                     guess.content.lower().strip() in c["aliases"] or guess.content.lower().strip(
                         "-").strip() in c[
                         "aliases"] or guess.content.lower().strip() == c[
                         "characterName"].lower() or guess.content.lower().strip("-").strip() == c[
                         "characterName"].lower()), "")
                wrong_chara_name = next((c["characterName"] for c in self.character_list.characters_data if
                                         guess.content.lower().strip() in c[
                                             "aliases"] or guess.content.lower().strip() == c[
                                             "characterName"].lower() or guess.content.lower().strip(
                                             "-").strip() in c["aliases"] or guess.content.lower().strip(
                                             "-").strip() == c["characterName"].lower()))
                await ctx.followup.send(
                    f"Nope, it's not **{wrong_chara_last_name} {wrong_chara_name}**")
                return False
            else:
                await ctx.send('Nope, try again!')
                return False

    @cards.command(name="fourstarguess", description="Guess from all 4* cards!")
    async def guess_four_star(self, ctx):
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True
        await ctx.defer()
        await self.card_guess_helper(ctx, self.four_stars_list)
        active_session[ctx.channel_id] = False

    @cards.command(name="threestarguess", description="Guess from all 3* cards!")
    async def guess_three_star(self, ctx):
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True
        await ctx.defer()
        await self.card_guess_helper(ctx, self.three_stars_list)
        active_session[ctx.channel_id] = False

    @cards.command(name="notwostarguess", description="Guess from all cards that aren't 2*!")
    async def guess_no_two_star(self, ctx):
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True
        await ctx.defer()
        await self.card_guess_helper(ctx, self.no_two_stars_list)
        active_session[ctx.channel_id] = False

    @cards.command(name="twostarguess", description="Guess from all 2* cards!")
    async def guess_two_star(self, ctx):
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True
        await ctx.defer()
        await self.card_guess_helper(ctx, self.two_stars_list)
        active_session[ctx.channel_id] = False

    @cards.command(name="bdayguess", description="Guess from all birthday rarity cards!")
    async def guess_birthday(self, ctx, rotation: discord.Option(discord.SlashCommandOptionType.integer, required=False, description="The rotation from which you want to guess, based on the Japanese server")):  #type: ignore
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True
        await ctx.defer()
        if rotation == 1:
            await self.card_guess_helper(ctx, self.birthday1_list)
        elif rotation == 2:
            await self.card_guess_helper(ctx, self.birthday2_list)
        elif rotation == 3:
            await self.card_guess_helper(ctx, self.birthday3_list)
        elif rotation == 4:
            await self.card_guess_helper(ctx, self.birthday4_list)
        else:
            await self.card_guess_helper(ctx, self.birthday_list)
        active_session[ctx.channel_id] = False

    @cards.command(name="sanrioguess", description="Guess from all sanrio cards!")
    async def guess_sanrio(self, ctx):
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True
        await ctx.defer()
        await self.card_guess_helper(ctx, self.sanrio_list)
        active_session[ctx.channel_id] = False

    @cards.command(name="unitguess", description="Guess from all cards from the unit of your choice!")
    async def guess_unit(self, ctx, unit: discord.Option(str, choices=UNITS)):  #type: ignore
        if active_session[ctx.channel_id]:
            await ctx.respond('Guessing has already started!')
            return
        active_session[ctx.channel_id] = True
        cards_filtered_by_unit_list = unit_filter(self.card_list.card_data, unit)
        if not cards_filtered_by_unit_list:
            cards_filtered_by_unit_list = self.card_list.card_data
            await ctx.defer()
        await self.card_guess_helper(ctx, cards_filtered_by_unit_list)
        active_session[ctx.channel_id] = False

    @tasks.loop(hours=24)
    async def update_card_list(self):
        self.card_list.card_data = CardStorage()
        logger.info("Update card db!")

def setup(bot):
    bot.add_cog(CardsGuessing(bot))