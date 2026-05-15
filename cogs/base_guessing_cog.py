from abc import ABC, abstractmethod
import discord
from discord.ext import commands


class BaseGuessingCog(commands.Cog, metaclass=ABC):

    @abstractmethod
    async def build_question(self, item):
        pass


    @abstractmethod
    async def fetch_answer_image(self, item):
        pass


    @abstractmethod
    async def check_guess(self, guess: str, item, item_type):
    # item is a dictionary with all needed data, like song name, id, aliases etc.
        pass


    async def fetch_from_bucket(self, key):
        pass


    async def send_error_for_wrong_guess(self, guess, data):
        pass


    # core loop, not an abstract method, to be implemented
    async def run_game(self, ctx, pool):
        pass