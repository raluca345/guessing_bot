import discord
from discord import Embed
from discord.ext.pages import Page, Paginator
from utility.utility_functions import connect

class Leaderboard:

    user_lb = []

    connection = connect()
    cursor = connection.cursor(dictionary=True)

    def __init__(self) -> None:
        self.get_data()

    def get_data(self):
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

        query = "INSERT INTO leaderboard (user_id, points) VALUES (%(user_id)s, %(points)s) ON DUPLICATE KEY UPDATE points = points + VALUES(points)"
        self.cursor.executemany(query, user_list)
        self.connection.commit()

    @staticmethod
    async def lb_pages(ctx: discord.ApplicationContext, pages: list[Embed]):
        paginator = Paginator(pages=pages)

        await paginator.respond(ctx.interaction)
