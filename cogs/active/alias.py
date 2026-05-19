import discord
from discord.ext import commands

from storage.character_storage import CharacterStorage
from storage.song_storage import SongStorage
from utility.notifications import notify_owner


class Alias(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_list = SongStorage()
        self.song_name_options = [s.romaji_name for s in self.song_list.song_data]
        self.character_list = CharacterStorage()
        self.chara_name_list = [c["characterName"] for c in self.character_list.characters_data]

    alias = discord.SlashCommandGroup(name="alias", description="Song or character aliases related commands")

    def _autocomplete_filter(self, ctx: discord.AutocompleteContext, options: list[str]) -> list[str]:
        """Generic autocomplete filter for matching options."""
        return [opt for opt in options if opt.lower().startswith(ctx.value.lower())]

    async def song_name_autocomplete(self, ctx: discord.AutocompleteContext):
        return self._autocomplete_filter(ctx, self.song_name_options)

    async def chara_name_autocomplete(self, ctx: discord.AutocompleteContext):
        return self._autocomplete_filter(ctx, self.chara_name_list)

    def _build_alias_embed(self, title: str, aliases: str) -> discord.Embed:
        """Build an embed for displaying aliases."""
        embed = discord.Embed(title=f"{title} Aliases", color=discord.Color.fuchsia())
        embed.add_field(name="", value=f"```{aliases}```")
        return embed

    @alias.command(name="viewsong", description="View a song's aliases")
    async def alias_view_song(self, ctx: discord.ApplicationContext, song: discord.Option(str, autocomplete=song_name_autocomplete)):  # type: ignore
        aliases = next((s.aliases for s in self.song_list.song_data if s.romaji_name == song), None)
        if not aliases:
            await ctx.respond(f"Song **{song}** not found!", ephemeral=True)
            return

        embed = self._build_alias_embed(song, aliases)
        await ctx.respond(embed=embed)

    @alias.command(name="suggestsong", description="Suggest a song alias!")
    async def alias_suggest_song(self, ctx, song: discord.Option(str, autocomplete=song_name_autocomplete), alias: str):  # type: ignore
        await notify_owner(
            self.bot,
            f"User `{ctx.author.name}` sent an alias suggestion for the song **{song}**: **{alias}**",
        )
        await ctx.respond("Your suggestion has been sent!")

    @alias.command(name="viewcharacter", description="View a character's aliases")
    async def alias_view_chara(self, ctx, character: discord.Option(str, autocomplete=chara_name_autocomplete)):  # type: ignore
        aliases = next((c["aliases"] for c in self.character_list.characters_data if c["characterName"] == character), None)
        if not aliases:
            await ctx.respond(f"Character **{character}** not found!", ephemeral=True)
            return

        embed = self._build_alias_embed(character, aliases)
        await ctx.respond(embed=embed)

    @alias.command(name="addsong", description="Add an alias for a song")
    @commands.is_owner()
    async def alias_add_song(self, ctx: discord.ApplicationContext, song: discord.Option(str, autocomplete=song_name_autocomplete), alias: str):  # type: ignore
        if not self.song_list.add_song_alias(song, alias):
            await ctx.respond(f"Alias **{alias}** already exists for **{song}**!", ephemeral=True)
            return
        await ctx.respond(f"Alias **{alias}** added for **{song}**!", ephemeral=True)

    @alias.command(name="suggestcharacter", description="Suggest a character alias!")
    async def alias_suggest_character(self, ctx, character: discord.Option(str, autocomplete=chara_name_autocomplete), alias: str):  # type: ignore
        await notify_owner(
            self.bot,
            f"User `{ctx.author.name}` sent an alias suggestion for the character **{character}**: **{alias}**",
        )
        await ctx.respond("Your suggestion has been sent!")


def setup(bot):
    bot.add_cog(Alias(bot))


