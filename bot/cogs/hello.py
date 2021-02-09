import discord
from discord.ext import commands

class Hello(commands.Cog, name="hello"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="hello")
    async def hello(self, ctx):
        await ctx.send("hello")

def setup(bot):
    bot.add_cog(Hello(bot))