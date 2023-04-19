import discord
from discord import app_commands, ui
from discord.ext import commands
from models.raid import Raid
from raid_view import RaidView
from datetime import datetime, date, time
from typing import Tuple
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
# intents = discord.Intents(messages=True, reactions=True, guilds=True, members=True, presences=True, voice_states=True, typing=True, bans=True, emojis=True, integrations=True, webhooks=True, invites=True, voice_states=True, dm_typing=True, guild_typing=True, reactions=True, guild_reactions=True, messages=True, guild_messages=True, dm_messages=True, guild_typing=True, dm_typing=True, presences=True, guild_presences=True)

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)
raids: dict[int, Raid] = {}


class RaidModal(ui.Modal, title="Send us your feedback"):
    raid_name = ui.TextInput(label="raid name")
    # raid_name = ui.Select(placeholder="Select a raid", options=[
    #     discord.SelectOption(label="Erenia"),
    #     discord.SelectOption(label="Zenas")
    # ])

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(os.getenv("GENERAL_CH_ID"))

        embed = discord.Embed(
            title=self.raid_name.value,
            description="New mara raid !",
            color=discord.Color.yellow(),
        )
        embed.set_author(name=interaction.user, icon_url=interaction.user.avatar)

        await channel.send(embed=embed)
        await interaction.response.send_message(
            f"Thank you, {interaction.user.name}", ephemeral=True
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        print(error)


@bot.event
async def on_ready():
    print("Bot is up and ready !")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):

    raid = raids.get(reaction.message.id)
    if raid is None or user.bot:
        return
    message = reaction.message
    if message.author != bot.user:
        return
    if str(reaction.emoji) == "✅":
        print("ADD REACTION")
        raid.add_participant(user)
        embed = raid.to_embed()
        await message.edit(embed=embed)


@bot.event
async def on_reaction_remove(reaction: discord.Reaction, user: discord.User):
    if user.bot:
        return
    raid = raids.get(reaction.message.id)
    if raid is not None:
        print("REMOVED REACTION")
        message = reaction.message
        raid.remove_participant(user)
        await message.edit(content=str(raid))


@bot.tree.command(name="clear")
@app_commands.describe(nb_of_messages_to_delete="Number of messages to delete")
async def clear(interaction: discord.Interaction, nb_of_messages_to_delete: int):
    """Clear a specified number of messages in the channel."""
    if nb_of_messages_to_delete <= 0:
        await interaction.response.send_message(
            "Please enter a positive integer.", ephemeral=True
        )
        return
    try:
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=nb_of_messages_to_delete)
        await interaction.followup.send(
            f"Successfully cleared {len(deleted)} messages.", ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "I don't have permission to delete messages in this channel.",
            ephemeral=True,
        )
    except discord.HTTPException:
        await interaction.followup.send("Failed to delete messages.", ephemeral=True)


@bot.tree.command(name="start_raid")
@app_commands.describe(
    raid_name="Name of the raid",
    start_date="Raid date (YYYY-MM-DD)",
    start_time="Raid start time (HH:MM)",
    max_participants="Max number of participants",
)
async def start_raid(
    interaction: discord.Interaction,
    raid_name: str,
    start_date: str,
    start_time: str,
    max_participants: int,
):
    start_date_obj = datetime.fromisoformat(start_date).date()
    start_time_obj = datetime.strptime(start_time, "%H:%M").time()
    await interaction.response.send_message(
        f"Creating {raid_name} raid", ephemeral=True
    )
    new_raid = Raid(
        interaction.user,
        raid_name,
        datetime.combine(start_date_obj, start_time_obj),
        max_participants,
    )
    message = await interaction.channel.send(embed=new_raid.to_embed())
    new_raid.message = message
    raids[message.id] = new_raid
    bench_emoji = discord.PartialEmoji(name="bench", id=1097864481461260369)
    await message.add_reaction(bench_emoji)


@bot.tree.command(name="view")
async def view(interaction: discord.Interaction):
    await interaction.response.send_message(f"Creating raid", ephemeral=True)
    new_raid = Raid(author=interaction.user)
    view = RaidView(raid=new_raid)
    role = discord.utils.get(interaction.channel.guild.roles, name="Raideur")
    message = await interaction.channel.send(
        content=role.mention, embed=new_raid.to_embed(), view=view
    )
    new_raid.message = message
    raids[message.id] = new_raid
    await message.add_reaction("⚔️")
    await message.add_reaction("🏹")
    await message.add_reaction("🪄")  # Wand emoji
    await message.add_reaction("🤜")


bot.run(os.getenv("BOT_TOKEN"))
