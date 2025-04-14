from discord.ext import commands
from discord.ext.pages import Page, Paginator

from utility.utility_functions import *
import discord

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def collect_commands(self):
        #Collect all commands and subcommands, and return a lst of pages for the paginator.
        all_commands = []

        # Collect all commands and subcommands into a lst of dictionaries
        for command in self.bot.application_commands:
            all_commands.extend(self.collect_command_info(command))

        # Create a lst of embeds for each page
        help_embeds = []
        total_pages = (len(all_commands) - 1) // COMMANDS_PER_PAGE + 1

        for page in range(total_pages):
            embed = discord.Embed(color=discord.Color.blue())
            start_idx = page * COMMANDS_PER_PAGE
            end_idx = start_idx + COMMANDS_PER_PAGE

            for command in all_commands[start_idx:end_idx]:
                if command["name"] == "reload":
                    continue
                embed.add_field(name=f"/{command['name']}", value=command['description'], inline=False)

            help_embeds.append(Page(embeds=[embed]))

        return help_embeds

    def collect_command_info(self, command, parent_name=""):
        #Helper function to collect command information.
        full_name = f"{parent_name} {command.name}".strip()
        app_commands = []

        if isinstance(command, discord.SlashCommandGroup):
            for subcommand in command.subcommands:
                app_commands.extend(self.collect_command_info(subcommand, full_name))
        else:
            app_commands.append({'name': full_name, 'description': command.description})

        return app_commands

    @discord.command(name="help", description="Shows information about all commands")
    async def help_command(self, ctx: discord.ApplicationContext):

        help_embeds = self.collect_commands()

        paginator = Paginator(pages=help_embeds)

        await paginator.respond(ctx.interaction)

def setup(bot):
    bot.add_cog(Help(bot))