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
        button.disabled = True
        button.label = "New Session Starting..."
        interaction_to_use = interaction
        pass
        try:
            await interaction.response.defer()
            try:
                original_message = await interaction.original_response()
                new_content = original_message.content + "\nRestarting..."
                await interaction.edit_original_response(content=new_content, view=self)
            except Exception:
                logger.exception("Failed to edit original response before restarting session")
        except discord.errors.NotFound:
            # Interaction is unknown/expired; fall back to the original context stored on the view
            logger.warning("Interaction expired when pressing Play Again; falling back to stored ctx")
            interaction_to_use = self.ctx

        # Start new session
        try:
            await self.callback(interaction_to_use, *self.callback_args)
        except Exception:
            logger.exception("Error while starting new session from Play Again button")