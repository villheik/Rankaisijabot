import discord
from discord.ext import commands
from discord.ext.commands import Bot
from bot import constants
from bot import rankaisija

prefix = constants.Bot.prefix
rankaisijaBot = rankaisija.Rankaisija(prefix)

if __name__ == "__main__":
   rankaisijaBot.load_cogs()

rankaisijaBot.run(constants.Bot.token)