import discord
from discord.ext import commands

from storage.character_storage import CharacterStorage
from storage.song_storage import SongStorage
from utility.utility_functions import logger


class Alias(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_list = SongStorage()
        self.song_name_options = [s["romaji_name"] for s in self.song_list.song_data]
        self.character_list = CharacterStorage()
        self.chara_name_list = [c["characterName"] for c in self.character_list.characters_data]

    alias = discord.SlashCommandGroup(name="alias", description="Song or charcter aliases related commands")

    async def song_name_autocomplete(self, ctx: discord.AutocompleteContext):
        return [song for song in self.song_name_options if song.lower().startswith(ctx.value.lower())]

    async def chara_name_autocomplete(self, ctx: discord.AutocompleteContext):
        return [char for char in self.chara_name_list if char.lower().startswith(ctx.value.lower())]

    @alias.command(name="viewsong", description="View a song's aliases")
    async def alias_view_song(self, ctx: discord.ApplicationContext, song: discord.Option(str, autocomplete=song_name_autocomplete)): #type: ignore
        e = discord.Embed(title=f"{song} Aliases", color=discord.Color.fuchsia())
        val = next((s["aliases"] for s in self.song_list.song_data if s["romaji_name"] == song))
        e.add_field(name="", value=f"```{val}```")
        await ctx.respond(embed=e)


    @alias.command(name="suggestsong", description="Suggest a song alias!")
    async def alias_suggest_song(self, ctx, song: discord.Option(str, autocomplete=song_name_autocomplete), a: str):
        me = await self.bot.fetch_user(599999906039726090)
        user = await self.bot.fetch_user(ctx.author.id)
        await me.send(f"User `{user.name}` sent an alias suggestion for the song **{song}**: **{a}**")
        await ctx.respond("Your suggestion has been sent!")

    @alias.command(name="viewcharacter", description="View a character's aliases")
    async def alias_view_chara(self, ctx, character: discord.Option(str, autocomplete=chara_name_autocomplete)):
        e = discord.Embed(title=f"{character} Aliases", color=discord.Color.fuchsia())
        val = next((c["aliases"] for c in self.character_list.characters_data if c["characterName"] == character))
        e.add_field(name="", value=f"```{val}```")
        await ctx.respond(embed=e)

    @alias.command(name="suggestcharacter", description="Suggest a character alias!")
    async def alias_suggest_character(self, ctx, character: discord.Option(str, autocomplete=chara_name_autocomplete), a: str):
        me = await self.bot.fetch_user(599999906039726090)
        user = await self.bot.fetch_user(ctx.author.id)
        await me.send(f"User `{user.name}` sent an alias suggestion for the character **{character}**: **{a}**")
        await ctx.respond("Your suggestion has been sent!")

def setup(bot):
    bot.add_cog(Alias(bot))