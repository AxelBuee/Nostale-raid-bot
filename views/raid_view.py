from datetime import datetime, timedelta

import discord
import pytz

from logger import logger
from models.raid import Raid
from nostale_bot import NostaleRaidHelperBot
from utils.utils import delete_raid_from_db


class RaidView(discord.ui.View):
    def __init__(self, raid: Raid, bot: NostaleRaidHelperBot):
        super().__init__(timeout=None)
        self.raid = raid
        self.bot = bot

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

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.raid.author:
            await interaction.response.send_message(
                "Only the author can do this", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        deleted = delete_raid_from_db(self.raid)
        if deleted:
            await interaction.followup.send("Raid canceled", ephemeral=True)
            del self.bot.raids[self.raid.message.id]
            thread = interaction.channel.get_thread(self.raid.message.id)
            await thread.send(
                f"Session annulée !\n{self.raid.get_participant_list_pprint()}"
            )
            message = self.raid.message
            await message.edit(
                embed=self.raid.to_cancel_embed(
                    self.bot.emoji_dict.get(self.raid.guild_id, [])
                )
            )
            self.stop()
            return
        await interaction.followup.send(
            "Couldn't cancel raid, please contact @AxelB", ephemeral=True
        )
