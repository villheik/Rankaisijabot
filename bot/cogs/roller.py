import discord
from discord.ext import commands
import random

class Roller(commands.Cog, name="roll"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="roll")
    async def roller(self, ctx, *, roll_string:str):
        try:
            dice, modifier = (roll_string.split('+') + ['0'])[:2]
            dice_count, dice_faces = map(int, dice.split('d'))
            modifier = int(modifier)
            if dice_count <= 0 or dice_faces <= 0 or dice_faces > 100 or dice_count > 100 or modifier > 100 or modifier < -100:
                await ctx.send("Heittomäärän ja silmälukujen on oltava suurempia kuin nolla, ja pienempiä kuin 100")
            else:
                rolls = [random.randint(1, dice_faces) for _ in range (dice_count)]
                result = sum(rolls) + modifier
                rolls_str = ','.join(str(roll) for roll in rolls)
                await ctx.send(f'Rollasit {rolls_str}. Loppusumma {result}')
        except ValueError:
            await ctx.send("Syötä komento muodossa NdN+N tai NdN (eli vaikka 1d20+3 tai 5d100)")

    @commands.command(name="coinflip")
    async def coinflip(self, ctx):
        await ctx.send(f'Coinflip: {random.choice(["Kruunu", "Klaava"])}')
def setup(bot):                                                                 
    bot.add_cog(Roller(bot))    
