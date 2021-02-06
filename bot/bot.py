import discord, configparser, os.path
from discord.ext import commands
from os import path

config = configparser.ConfigParser()
if not (path.exists('../config.ini')):
    print("Could not find config file.")
config.read_file(open("../config.ini", "r"))
TOKEN = config['BOT']['Token']

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
