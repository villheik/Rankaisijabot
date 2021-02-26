import discord
from discord.ext import commands

class Misc_games(commands.Cog, name="misc_games"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ror")
    async def ror(self, ctx):
        await ctx.send(file=discord.File("images/ror.png"))

def setup(bot):
    bot.add_cog(Misc_games(bot))