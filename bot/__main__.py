import discord
import asyncio
import platform
import os
from bot import constants
from bot import rankaisija
from bot import log
from discord.ext.commands import Context

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

prefix = constants.Bot.prefix
rankaisijaBot = rankaisija.Rankaisija(prefix, intents=intents)

rankaisijaBot.logger = log.setup()


@rankaisijaBot.event
async def on_ready() -> None:
    """
    The code in this event is executed when the bot is ready.
    """
    rankaisijaBot.logger.info(f"Logged in as {rankaisijaBot.user.name}")
    rankaisijaBot.logger.info(f"discord.py API version: {discord.__version__}")
    rankaisijaBot.logger.info(f"Python version: {platform.python_version()}")
    rankaisijaBot.logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
    rankaisijaBot.logger.info("-------------------")

@rankaisijaBot.event
async def on_message(message: discord.Message):
   if message.author == rankaisijaBot.user:
      return
   await rankaisijaBot.process_commands(message)

@rankaisijaBot.event
async def on_command_completion(context: Context) -> None:
    full_command_name = context.command.qualified_name
    split = full_command_name.split(" ")
    executed_command = str(split[0])
    if context.guild is not None:
        rankaisijaBot.logger.info(
            f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
        )
    else:
        rankaisijaBot.logger.info(
            f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
        )

async def load_cogs() -> None:
   await rankaisijaBot.load_cogs()

asyncio.run(load_cogs())
rankaisijaBot.run(constants.Bot.token)