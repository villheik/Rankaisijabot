import discord
from discord.ext import commands


class General(commands.Cog, name="general"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="info", aliases=["botinfo"])
    async def info(self, ctx):
        thumbnail = discord.File("images/rankaisija.jpg", filename="rankaisija.jpg")
        embed = discord.Embed(description="Rankaisijabot", color=0x00FFFF)
        embed.set_thumbnail(url="attachment://rankaisija.jpg")
        embed.add_field(
            name="Github link", value="https://github.com/villheik/Rankaisijabot"
        )
        await ctx.send(file=thumbnail, embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))
