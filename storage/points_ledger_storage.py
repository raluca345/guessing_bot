from storage.base_storage import BaseStorage


class PointsLedgerStorage(BaseStorage):
    def __init__(self):
        super().__init__(use_dictionary=False)

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
        self.execute_insert(
            query,
            (guild_id, channel_id, user_id, points, game_type, card_id, message_id),
        )