import discord
from discord.ext import commands

class Rankaisumetodit(commands.Cog, name="rankaisumetodit"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="rankaise")
    async def rankaise(self, ctx, rankaisukohde=None):
        if (rankaisukohde == None):
            await ctx.send(f"{ctx.author.name} alensi itsensä pojaksi ja käytti rankaisumetodeja itseensä")
        elif (len(rankaisukohde) > 20):
            await ctx.send(f"{ctx.author.name} ei ottanut rankaisumetodeja vakavasti ja joutui poikien mukana kamarille")
        else:
            await ctx.send(f'{ctx.author.name} käytti rankaisumetodeja poikaan: {rankaisukohde}')


def setup(bot):
    bot.add_cog(Rankaisumetodit(bot))