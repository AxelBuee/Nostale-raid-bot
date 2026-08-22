from datetime import datetime, timedelta

import discord
import pytz

from logger import logger
from models.error_embed import ErrorEmbed
from models.raid import Raid
from nostale_bot import NostaleRaidHelperBot
from utils.utils import delete_raid_from_db


class RaidView(discord.ui.View):
    def __init__(self, bot: NostaleRaidHelperBot):
        super().__init__(timeout=None)
        self.bot = bot

    def get_raid(self, interaction: discord.Interaction) -> Raid | None:
        return self.bot.raids.get(interaction.message.id)

    @discord.ui.button(
        label="Notify",
        style=discord.ButtonStyle.blurple,
        custom_id="raid_notify_button",
    )
    async def notify_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        raid = self.get_raid(interaction)
        if raid is None:
            await interaction.response.send_message(
                embed=ErrorEmbed(description="This raid could not be found."),
                ephemeral=True,
            )
            return

        if interaction.user != raid.author:
            await interaction.response.send_message(
                "Only the author can do this", ephemeral=True
            )
            return

        now = datetime.now(pytz.timezone("Europe/Paris"))
        time_difference = raid.start_datetime - now
        if time_difference <= timedelta(minutes=30):
            await interaction.response.defer()
            for user in raid.participants:
                dm_channel = await user.create_dm()
                await dm_channel.send("Raid is about to start", embed=raid.to_embed([]))
                logger.info(f"Send DM to {user.name} for raid {raid.message.id}")
        else:
            await interaction.response.send_message(
                "You can only notify between start_raid_time + 30min and start_raid_time",
                ephemeral=True,
            )
            return

    @discord.ui.button(
        label="Cancel", style=discord.ButtonStyle.red, custom_id="raid_cancel_button"
    )
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        raid = self.get_raid(interaction)
        if raid is None:
            await interaction.response.send_message(
                embed=ErrorEmbed(description="This raid could not be found."),
                ephemeral=True,
            )
            return

        if interaction.user != raid.author:
            await interaction.response.send_message(
                "Only the author can do this", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        deleted = delete_raid_from_db(raid)
        if deleted:
            await interaction.followup.send("Raid canceled", ephemeral=True)
            self.bot.raids.pop(raid.message.id, None)
            if raid.thread_id:
                self.bot.raids.pop(raid.thread_id, None)

            thread = interaction.channel.get_thread(raid.message.id)
            if thread:
                await thread.send(
                    f"Session annulée !\n{raid.get_participant_list_pprint()}"
                )

            await raid.message.edit(
                embed=raid.to_cancel_embed(self.bot.emoji_dict.get(raid.guild_id, []))
            )
            return
        await interaction.followup.send(
            "Couldn't cancel raid, please contact @AxelB", ephemeral=True
        )
