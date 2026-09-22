import discord
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo


class Wow(commands.Cog, name="wow"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="wowia", aliases=["wow"])
    async def wowia(self, ctx):
        zi = ZoneInfo("Europe/Helsinki")
        # WoW Forever launch: 5.11.2026 at 02:00 Finnish time
        launch_time = datetime(
            2026, 11, 5, 2, 0, 0,
            tzinfo=zi
        )

        now = datetime.now(zi)

        if now >= launch_time:
            await ctx.send(file=discord.File("images/tauren_hepu.png"))
            await ctx.send(
                "🌿🐂 **A young tauren druid sits beneath the trees, "
                "patiently awaiting his destiny.**"
            )

        else:
            remaining = launch_time - now

            days = remaining.days
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            await ctx.send(file=discord.File("images/tauren_hepu.png"))
            await ctx.send(
                "🌿🐂 **A young tauren druid sits beneath the trees, "
                "patiently awaiting his destiny.**\n"
                f"**SOON:** {days} päivää {hours} tuntia "
                f"{minutes} minuuttia {seconds} sekuntia ennen julkaisua! 🌙"
            )


async def setup(bot):
    await bot.add_cog(Wow(bot))
