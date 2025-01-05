import discord
from discord.ext import commands


class Dota(commands.Cog, name="dota"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dotaukkoja", aliases=["ukkoja"])
    async def ukkoja(self, ctx):
        await ctx.send(file=discord.File("images/dota_ukkoja.png"))

    @commands.command(name="ei")
    async def ei(self, ctx):
        await ctx.send(file=discord.File("images/ei.png"))


async def setup(bot):
    await bot.add_cog(Dota(bot))
