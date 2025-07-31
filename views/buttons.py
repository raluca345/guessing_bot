import discord
import logging

logger = logging.getLogger(__name__)

class Buttons(discord.ui.View):
    def __init__(self, ctx, buttons: list[str], callback, callback_args=None, timeout=None):
        super().__init__()
        self.ctx = ctx
        self.buttons = buttons
        self.callback = callback
        self.callback_args = callback_args if callback_args is not None else []

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.primary)
    async def play_again(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer()
        button.disabled = True
        button.label = "New Session Starting..."
        original_message = await interaction.original_response()
        new_content = original_message.content + "\nRestarting..."
        await interaction.edit_original_response(content=new_content, view=self)
        await self.callback(self.ctx, *self.callback_args)