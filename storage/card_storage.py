from utility.utility_functions import connect, logger


class CardStorage:

    def __init__(self) -> None:
        self.connection = connect()
        self.cursor = self.connection.cursor(dictionary=True)
        self.card_data = []
        self.get_card_data()

    def _ensure_connection(self):
        try:
            self.connection.ping(reconnect=True, attempts=3, delay=2)
        except Exception:
            logger.warning("Database connection lost, reconnecting...")
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = connect()
        try:
            if hasattr(self, "cursor") and self.cursor is not None:
                try:
                    self.cursor.close()
                except Exception:
                    pass
        except Exception:
            pass
        self.cursor = self.connection.cursor(dictionary=True)

    def close(self):
        try:
            if hasattr(self, 'cursor') and self.cursor is not None:
                try:
                    self.cursor.close()
                except Exception:
                    pass
                self.cursor = None
        except Exception:
            pass
        try:
            if hasattr(self, 'connection') and self.connection is not None:
                try:
                    self.connection.close()
                except Exception:
                    pass
                self.connection = None
        except Exception:
            pass

    def get_card_data(self):
        self._ensure_connection()

        query = "SELECT id, assetbundle_name, card_rarity_type, prefix, en_prefix, release_at, support_unit, character_id FROM cards"

        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        for row in rows:
            if not row or row == {}:
                continue
            self.card_data.append(row)
