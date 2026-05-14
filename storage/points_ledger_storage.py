from utility.utility_functions import connect, logger


class PointsLedgerStorage:
    def __init__(self):
        self.connection = connect()
        self.cursor = self.connection.cursor()

    def close(self):
        try:
            if hasattr(self, "cursor") and self.cursor is not None:
                try:
                    self.cursor.close()
                except Exception:
                    pass
                self.cursor = None
        except Exception:
            pass

        try:
            if hasattr(self, "connection") and self.connection is not None:
                try:
                    self.connection.close()
                except Exception:
                    pass
                self.connection = None
        except Exception:
            pass
    
    def _ensure_connection(self):
        try:
            self.connection.ping(reconnect=True, attempts=3, delay=2)
        except Exception:
            logger.warning("Ledger DB connection lost, reconnecting...")
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = connect()
        try:
            if self.cursor is not None:
                try:
                    self.cursor.close()
                except Exception:
                    pass
        except Exception:
            pass
        self.cursor = self.connection.cursor()

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
        try:
            self._ensure_connection()

            query = """
                INSERT INTO points_ledger
                (guild_id, channel_id, user_id, points, game_type, card_id, message_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            self.cursor.execute(
                query,
                (guild_id, channel_id, user_id, points, game_type, card_id, message_id),
            )

            self.connection.commit()

        except Exception:
            logger.exception("Failed to insert into points_ledger")