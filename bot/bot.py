import discord, configparser, os.path
from discord.ext import commands
from os import path

config = configparser.ConfigParser()

# Try to read the config file from different places depending on where the script was ran from
config.read("../config.ini")
config.read("./config.ini")
try:
    TOKEN = config['BOT']['Token']
except KeyError:
    print("Could not find config.ini")

description = '''Rankaisijabot'''
bot = commands.Bot(command_prefix='!', description=description)

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


@bot.command()
async def hello(ctx):
    """Says world"""
    await ctx.send("world")

bot.run(TOKEN)
