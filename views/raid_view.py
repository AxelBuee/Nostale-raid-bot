import discord
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
        await interaction.response.defer()
        for user in self.raid.participants.keys():
            dm_channel = await user.create_dm()
            await dm_channel.send("Raid is about to start")
