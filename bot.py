import discord
from discord.ext import commands
import asyncio
import datetime
from models.raid import Raid
from typing import List

bot = commands.Bot(command_prefix='!')
client = discord.Client()

raids: dict[int, Raid] = {}

# Check if it's past the start time plus 30 minutes


@client.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    raid = raids.get(reaction.message.id)
    if raid is None or user.bot:
        return
    message = reaction.message
    if message.author != client.user:
        return
    if str(reaction.emoji) == "✅":
        # Add user to participants list
        raid.add_participant(user)
        await message.edit(content=f"Raid participants ({len(raid.participants)}/15):\n{raid.participants}")

@client.event
async def on_reaction_remove(reaction: discord.Reaction, user: discord.User):
    if user.bot:
        return
    raid = raids.get(reaction.message.id)
    if raid is not None:
        await raid.remove_participant(user)

@bot.command()
async def clear(ctx, num_messages: int):
    """Clear a specified number of messages in the channel."""
    if num_messages <= 0:
        await ctx.send("Please enter a positive integer.")
        return
    try:
        await ctx.channel.purge(limit=num_messages)
        await ctx.send(f"Successfully cleared {num_messages} messages.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to delete messages in this channel.")
    except discord.HTTPException:
        await ctx.send("Failed to delete messages.")

@bot.command()
async def start_raid(ctx):
    # Your code to start a new raid event goes here
    pass

client.run('your_bot_token')
bot.run("your_bot_token_here")