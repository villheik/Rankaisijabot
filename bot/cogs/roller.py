import discord
from discord.ext import commands
import random

class Roller(commands.Cog, name="roll"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="roll")
    async def roller(self, ctx):
        roll = random.randint(1,20)
        await ctx.send(f'Rollasit {roll}!')

def setup(bot):
    bot.add_cog(Roller(bot))
