from contextlib import closing

from utility.db import temp_connection
from utility.utility_functions import logger


class PointsLedgerStorage:
    def record_points(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        points: int,
        game_type: str,
        card_id: int | None = None,
        message_id: int | None = None,
    ):
        query = """
            INSERT INTO points_ledger
            (guild_id, channel_id, user_id, points, game_type, card_id, message_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with temp_connection() as connection:
                with closing(connection.cursor()) as cursor:
                    cursor.execute(
                        query,
                        (guild_id, channel_id, user_id, points, game_type, card_id, message_id),
                    )
                    connection.commit()
        except Exception:
            logger.exception("Failed to record points")
