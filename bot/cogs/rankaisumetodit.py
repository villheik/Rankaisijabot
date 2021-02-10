import discord
from discord.ext import commands

class Rankaisumetodit(commands.Cog, name="rankaisumetodit"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="rankaise")
    async def rankaise(self, ctx, rankaisukohde=None):
        if (rankaisukohde == None):
            await ctx.send("Rankaisen itseäni")
        else:
            await ctx.send(f'{ctx.author.name} käytti rankaisumetodeja poikaan: {rankaisukohde}')


def setup(bot):
    bot.add_cog(Rankaisumetodit(bot))