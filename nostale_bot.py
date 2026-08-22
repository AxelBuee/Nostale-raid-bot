from datetime import datetime, timedelta
from typing import List

import discord
import pytz
from discord.ext import commands, tasks

from logger import logger
from models.raid import Raid


class NostaleRaidHelperBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

        self.cog_list = ["cogs.raid_cog", "cogs.utils_cog"]
        self.raids: dict[int, Raid] = {}
        self.emoji_dict: dict[int, List[discord.Emoji]] = {}

    async def setup_hook(self):
        for cog in self.cog_list:
            await self.load_extension(cog)
        from views.raid_view import RaidView

        self.add_view(RaidView(bot=self))
        self.cleanup_expired_raids.start()

    @tasks.loop(minutes=10)
    async def cleanup_expired_raids(self):
        now = datetime.now(pytz.timezone("Europe/Paris"))
        logger.info(
            f"[cleanup_expired_raids] Running check at {now.strftime('%Y-%m-%d %H:%M:%S')} "
            f"— {len(self.raids)} raid(s) in memory"
        )
        processed = set()

        for raid in list(self.raids.values()):
            if raid.message.id in processed:
                continue

            end_time = raid.start_datetime + timedelta(hours=raid.duration)
            deletion_time = end_time + timedelta(hours=1)
            logger.info(
                f"[cleanup_expired_raids] Raid '{raid.raid_name}' (message {raid.message.id}): "
                f"end={end_time.strftime('%Y-%m-%d %H:%M')}, "
                f"deletion_time={deletion_time.strftime('%Y-%m-%d %H:%M')}, "
                f"expired={now >= deletion_time}"
            )
            if now < deletion_time:
                continue

            processed.add(raid.message.id)

            if raid.thread_id:
                thread = self.get_channel(raid.thread_id)
                if thread is None:
                    try:
                        thread = await self.fetch_channel(raid.thread_id)
                    except (discord.NotFound, discord.Forbidden):
                        thread = None
                if thread:
                    try:
                        await thread.delete()
                    except (discord.NotFound, discord.Forbidden) as e:
                        logger.warning(f"Could not delete thread {raid.thread_id}: {e}")

            try:
                await raid.message.delete()
            except (discord.NotFound, discord.Forbidden) as e:
                logger.warning(f"Could not delete raid message {raid.message.id}: {e}")

            self.raids.pop(raid.message.id, None)
            if raid.thread_id:
                self.raids.pop(raid.thread_id, None)

            logger.info(
                f"Cleaned up expired raid '{raid.raid_name}' (message {raid.message.id})"
            )

    @cleanup_expired_raids.before_loop
    async def before_cleanup_expired_raids(self):
        await self.wait_until_ready()

    async def on_ready(self):
        from utils.utils import generate_raids_dict, load_raids_from_db

        synced = await self.tree.sync(guild=discord.Object(id=688757693850452007))
        logger.info("Bot is up and ready !")
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.critical(e)
        for guild in self.guilds:
            emojis = await guild.fetch_emojis()
            self.emoji_dict[guild.id] = emojis
        raids_list = await load_raids_from_db(bot=self)
        self.raids = generate_raids_dict(raids_list, self.emoji_dict)


# intents = discord.Intents(messages=True, reactions=True, guilds=True, members=True, presences=True, voice_states=True, typing=True, bans=True, emojis=True, integrations=True, webhooks=True, invites=True, voice_states=True, dm_typing=True, guild_typing=True, reactions=True, guild_reactions=True, messages=True, guild_messages=True, dm_messages=True, guild_typing=True, dm_typing=True, presences=True, guild_presences=True)
# intents.message_content = True
# bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)
# raids: dict[int, Raid] = {}
