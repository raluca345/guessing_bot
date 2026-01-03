import discord
import logging
from utility.utility_functions import active_session

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

        # Start new session using a safe active_session toggle; if the callback fails, ensure flag is cleared.
        ch_id = getattr(interaction_to_use, "channel_id", None) or (interaction_to_use.channel.id if getattr(interaction_to_use, "channel", None) else None)
        pass
        try:
            if ch_id is not None:
                active_session[ch_id] = True
            await self.callback(interaction_to_use, *self.callback_args)
        except Exception:
            logger.exception("Error while starting new session from Play Again button")
            try:
                if ch_id is not None:
                    active_session[ch_id] = False
            except Exception:
                logger.exception("Failed to clear active_session after failed restart")