import discord
from discord import app_commands
from discord.ext import commands
from models.raid import Raid
from logger import logger
import os


class NostaleRaidHelperBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

        self.cog_list = ["cogs.raid_cog"]  # "cogs.utils_cog"
        self.raids: dict[int, Raid] = {}

    async def setup_hook(self):
        for cog in self.cog_list:
            await self.load_extension(cog)

    async def on_ready(self):
        from utils.utils import load_raids_from_db, generate_raids_dict

        logger.info("Bot is up and ready !")
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.critical(e)
        raids_list = await load_raids_from_db(bot=self)
        self.raids = generate_raids_dict(raids_list)


# intents = discord.Intents(messages=True, reactions=True, guilds=True, members=True, presences=True, voice_states=True, typing=True, bans=True, emojis=True, integrations=True, webhooks=True, invites=True, voice_states=True, dm_typing=True, guild_typing=True, reactions=True, guild_reactions=True, messages=True, guild_messages=True, dm_messages=True, guild_typing=True, dm_typing=True, presences=True, guild_presences=True)
# intents.message_content = True
# bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)
# raids: dict[int, Raid] = {}
