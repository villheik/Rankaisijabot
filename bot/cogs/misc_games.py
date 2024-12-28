import discord
from discord.ext import commands

class Misc_games(commands.Cog, name="misc_games"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ror")
    async def ror(self, ctx):
        await ctx.send(file=discord.File("images/ror.png"))

    @commands.command(name="hon")
    async def hon(self, ctx):
        await ctx.send(file=discord.File("images/hon.png"))

    @commands.command(name="eft", aliases=["tarkov"])
    async def eft(self, ctx):
        await ctx.send(file=discord.File("images/eft.png"))

    @commands.command(name="darktide")
    async def darktide(self, ctx):
        await ctx.send(file=discord.File("images/darktide.png"))

async def setup(bot):
    await bot.add_cog(Misc_games(bot))