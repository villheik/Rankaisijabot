import discord
from discord.ext import commands
from datetime import *

class Ghost(commands.Cog, name="ghostTimer"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ghost")
    async def ghost(self, ctx):
        await ctx.send(file=discord.File("images/ghost_tampere.jpg"))
        ghost_gig_date = date(2022, 4, 27)
        today_date = date.today()
        if ghost_gig_date == date.today():
            await ctx.send("Ghostin keikka tänään!!!")
        elif today_date > ghost_gig_date:
            await ctx.send("Ghostin keikka meni jo :(")
        else:
            await ctx.send("Ghostin tampereen keikkaan aikaa: " + str(abs(ghost_gig_date - today_date).days) + " päivää!")




def setup(bot):
    bot.add_cog(Ghost(bot))