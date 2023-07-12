import discord
from discord.ext import commands

class Misc(commands.Cog, name="misc"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="rakyta")
    async def rakyta(self, ctx):
        await ctx.send(file=discord.File("images/rakyta.jpg"))


async def setup(bot):
    await bot.add_cog(Misc(bot))