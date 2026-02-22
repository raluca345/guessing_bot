import discord
from discord import Embed
from discord.ext.pages import Page, Paginator
from utility.utility_functions import connect, logger

class Leaderboard:

    def __init__(self) -> None:
        self.connection = connect()
        self.cursor = self.connection.cursor(dictionary=True)
        self.user_lb = []
        self.get_data()

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
        self.cursor = self.connection.cursor(dictionary=True)

    def get_data(self):
        self._ensure_connection()
        self.user_lb.clear()

        query = "SELECT user_id, points FROM leaderboard"
        self.cursor.execute(query)

        rows = self.cursor.fetchall()

        for row in rows:
            if row == {} or not row:
                continue
            usr = {"user_id": row["user_id"], "points": row["points"]}
            self.user_lb.append(usr)

    def add_users(self, user_list):
        self._ensure_connection()
        query = "INSERT INTO leaderboard (user_id, points) VALUES (%(user_id)s, %(points)s) ON DUPLICATE KEY UPDATE points = points + VALUES(points)"
        self.cursor.executemany(query, user_list)
        self.connection.commit()

    def delete_user(self, user_id):
        try:
            self._ensure_connection()
            query = "DELETE FROM leaderboard WHERE user_id = %s"
            self.cursor.execute(query, (user_id,))
            self.connection.commit()
        except Exception:
            pass

    @staticmethod
    async def lb_pages(ctx: discord.ApplicationContext, pages: list[Embed]):
        paginator = Paginator(pages=pages)

        await paginator.respond(ctx.interaction)
