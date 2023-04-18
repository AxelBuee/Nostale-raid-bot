import discord
from models.raid import Raid


class RaidView(discord.ui.View):
    def __init__(self, raid):
        super().__init__(timeout=None)
        self.raid: Raid = raid

    @discord.ui.button(label="Join", style=discord.ButtonStyle.green)
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        role = discord.utils.get(interaction.channel.guild.roles, name="Raideur")
        if not role in interaction.user.roles:
            embed = discord.Embed(
                title="You don't have the required role!",
                description=f"You need the {role.mention} role to do that.",
                colour=discord.Colour.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        joined = self.raid.add_participant(interaction.user)
        if joined:
            embed = self.raid.to_embed()
            await interaction.message.edit(embed=embed)
            await interaction.response.send_message(
                "You joined the raid !", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "You have already joined", ephemeral=True
            )
        # await interaction.response.defer()
        # dm_channel = await interaction.user.create_dm()
        # await dm_channel.send("You joined the raid !")

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.red)
    async def leave_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        left = self.raid.remove_participant(interaction.user)
        if left:
            await interaction.response.send_message("You left the raid", ephemeral=True)
        else:
            await interaction.response.send_message(
                "You were not part of the raid", ephemeral=True
            )
