from datetime import datetime, timedelta

import discord
import pytz

from logger import logger
from models.raid import Raid


class RaidView(discord.ui.View):
    def __init__(self, raid):
        super().__init__(timeout=None)
        self.raid: Raid = raid

    @discord.ui.button(label="Notify", style=discord.ButtonStyle.blurple)
    async def notify_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.raid.author:
            await interaction.response.send_message(
                "Only the author can do this", ephemeral=True
            )
            return
        now = datetime.now(pytz.timezone("Europe/Paris"))
        time_difference = self.raid.start_datetime - now
        if time_difference <= timedelta(minutes=30):
            await interaction.response.defer()
            for user in self.raid.participants.keys():
                dm_channel = await user.create_dm()
                await dm_channel.send(
                    "Raid is about to start", embed=self.raid.to_embed([])
                )
                logger.info(f"Send DM to {user.name} for raid {self.raid.message.id}")
        else:
            await interaction.response.send_message(
                "You can only notify between start_raid_time + 30min and start_raid_time",
                ephemeral=True,
            )
            return
