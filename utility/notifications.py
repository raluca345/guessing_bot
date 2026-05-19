from utility.constants import OWNER_ID
from utility.utility_functions import logger


async def notify_owner(bot, message: str):
    try:
        owner = bot.get_user(OWNER_ID)
        await owner.send(message)
    except Exception:
        logger.exception("Failed to notify owner")
