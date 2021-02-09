import discord
from discord.ext import commands
from discord.ext.commands import Bot
from bot import constants

class Rankaisija(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def load_cogs(self):
        for cog in constants.Cog.cogs:
            try:
                self.load_extension("bot.cogs." + cog)
                print(f"Loaded extension '{cog}'")
            except Exception as e:
                print(f"Failed to load extension {cog}")
