import discord
import logging

logger = logging.getLogger(__name__)

class Buttons(discord.ui.View):
    def __init__(self, ctx, buttons, callback, callback_args=None, timeout=None):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.callback = callback
        self.callback_args = callback_args if callback_args is not None else []
        self._starting = False  # guard flag

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.primary)
    async def play_again(self, button, interaction):
        # Guard against race conditions from multiple clicks
        if self._starting:
            await interaction.response.defer()
            return
        self._starting = True

        button.disabled = True
        button.label = "New Session Starting..."

        # Disable the button on Discord's side FIRST, before starting the session
        try:
            await interaction.response.edit_message(view=self)
        except discord.errors.NotFound:
            pass  # interaction expired, that's okay

        await self.callback(interaction, *self.callback_args)
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