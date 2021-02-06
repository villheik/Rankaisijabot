import discord, configparser
from discord.ext import commands

config = configparser.ConfigParser()
config.read('../config.ini')
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
