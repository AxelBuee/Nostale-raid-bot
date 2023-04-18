import discord
from discord.ext import commands
from models.raid import Raid
import datetime

class RaidForm(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=30.0)
        self.interaction = interaction
        self.author = interaction.user
        self.raid_name = None
        self.date = None
        self.time = None
        self.max_participants = 0

        self.text_input = discord.ui.TextInput(
            label="input",
            placeholder='Enter the name of the raid...',
            max_length=100,
        )
        self.add_item(self.text_input)

    @discord.ui.select(placeholder="Select raid", options=[
        discord.SelectOption(label="Erenia", value="Erenia"),
        discord.SelectOption(label="Zenas", value="Zenas"),
        discord.SelectOption(label="Kiro", value="Kiro"),
    ])
    async def raid_select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        self.raid_name = select.values[0]
        await interaction.response.edit_message(view=self)

    # @discord.ui.TextInput(label="date", placeholder="Raid date start (YYYY-MM-DD)")
    # async def raid_date_callback(self, input: discord.ui.TextInput, interaction: discord.Interaction):
    #     self.date = datetime.datetime.fromisoformat(input.value)
    #     await interaction.response.edit_message(view=self)

    # @discord.ui.TextInput(label="time", placeholder="Raid date start time (HH:MM)")
    # async def raid_date_callback(self, input: discord.ui.TextInput, interaction: discord.Interaction):
    #     self.time = datetime.datetime.strptime(input.value, "%H:%M")
    #     await interaction.response.edit_message(view=self)
    
    # @discord.ui.TextInput(label="max_participants", placeholder="Max participants")
    # async def raid_max_callback(self, input: discord.ui.TextInput, interaction: discord.Interaction):
    #     self.max_participants = int(input.value)
    #     await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Submit")
    async def submit_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.raid_name and self.date:
            await interaction.response.edit_message(view=None)
            await interaction.followup.send("Raid created!", ephemeral=True)
            raid = Raid(raid_name=self.raid_name, start_datetime=datetime.datetime.combine(self.date, self.time), max_participants=self.max_participants)
            self.stop()
            # do something with the raid object
        else:
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("Please fill out all fields.", ephemeral=True)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.author

    async def on_timeout(self):
        await self.interaction.edit_original_response(view=None)
        await self.interaction.response.send_message(content="Timed out")

    async def start(self):
        embed = discord.Embed(title="New Raid Creation Form", description="Please fill out the form below.")
        embed.add_field(name="Difficulty", value="Please select the difficulty of the raid.")
