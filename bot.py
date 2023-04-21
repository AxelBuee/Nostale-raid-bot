import discord
from discord import app_commands
from discord.ext import commands
from models.raid import Raid
from views.raid_view import RaidView
from datetime import datetime
import os
from dotenv import load_dotenv
from db import get_session, RaidSQL
import asyncio
from typing import List

load_dotenv()
# intents = discord.Intents(messages=True, reactions=True, guilds=True, members=True, presences=True, voice_states=True, typing=True, bans=True, emojis=True, integrations=True, webhooks=True, invites=True, voice_states=True, dm_typing=True, guild_typing=True, reactions=True, guild_reactions=True, messages=True, guild_messages=True, dm_messages=True, guild_typing=True, dm_typing=True, presences=True, guild_presences=True)

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)
raids: dict[int, Raid] = {}


@bot.event
async def on_ready():
    print("Bot is up and ready !")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    session = get_session()
    session.close()


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    raid = raids.get(payload.message_id)
    user = await bot.fetch_user(payload.user_id)
    if raid is None or user.bot:
        return
    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    if message.author != bot.user:
        return
    if str(payload.emoji) in "⚔️🏹🪄🤜":
        current_emoji = raid.get_participant_emoji(user)
        if current_emoji:
            raid.participants[user]["reaction_emoji"] = str(payload.emoji)
            await message.remove_reaction(current_emoji, user)
        else:
            raid.add_participant(user, str(payload.emoji))
        embed = raid.to_embed()
        await message.edit(embed=embed)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    user = await bot.fetch_user(payload.user_id)
    raid = raids.get(payload.message_id)
    if not raid or user.bot or raid.get_participant_emoji(user) != str(payload.emoji):
        return
    if raid is not None:
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        raid.remove_participant(user)
        await message.edit(embed=raid.to_embed())


@bot.tree.command(name="clear")
@app_commands.describe(nb_of_messages_to_delete="Number of messages to delete")
async def clear(interaction: discord.Interaction, nb_of_messages_to_delete: int):
    """Clear a specified number of messages in the channel."""
    # TODO: Add user role check
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
    max_participants: int | None = None,
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
    await message.add_reaction("⚔️")
    await message.add_reaction("🏹")
    await message.add_reaction("🪄")  # Wand emoji
    await message.add_reaction("🤜")
    await interaction.edit_original_response(content="Raid fully created")


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


@bot.tree.command(name="store")
async def store(interaction: discord.Interaction):
    await interaction.response.send_message(f"Storing raids", ephemeral=True)
    session = get_session()
    for message_id, raid in raids.items():
        raid_sql = raid.to_raid_sql()
        session.merge(raid_sql)
        session.commit()
    session.close()
    await interaction.edit_original_response(content="Raids stored")


@bot.tree.command(name="load")
async def load(interaction: discord.Interaction):
    await interaction.response.send_message(f"Loading raids", ephemeral=True)
    session = get_session()
    today_end = datetime.combine(datetime.today(), datetime.max.time())
    raids_sql = session.query(RaidSQL).filter(RaidSQL.start_datetime <= today_end).all()
    to_raid_tasks = [raid_sql.to_raid(bot=bot) for raid_sql in raids_sql]
    raids_list: List[Raid] = await asyncio.gather(*to_raid_tasks)
    for raid in raids_list:
        if raids.get(raid.message.id) is None:
            raids[raid.message.id] = raid
        else:
            print(f"Raid {raid.message.id} already loaded")
    await interaction.edit_original_response(content=f"{len(raids_list)} raids loaded")
    session.close()


bot.run(os.getenv("BOT_TOKEN"))
