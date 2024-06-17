from datetime import datetime, timedelta

import discord
import pytz
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from logger import logger
from models.error_embed import ErrorEmbed
from models.raid import Raid
from nostale_bot import NostaleRaidHelperBot
from templates.templates import RAID_TEMPLATES
from utils.utils import update_raid_in_db, parse_date, parse_time
from views.raid_view import RaidView


class RaidCog(commands.Cog):
    def __init__(self, bot: NostaleRaidHelperBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        raid = self.bot.raids.get(payload.message_id)
        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id)
        if raid is None or user.bot:
            return
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if message.author != self.bot.user:
            return
        if str(payload.emoji) in "⚔️🏹🧙🤜":
            if (
                len(raid.participants) >= raid.max_participants
                and user not in raid.participants
            ):
                return
            current_emoji = raid.get_participant_emoji(user)
            if current_emoji:
                raid.participants[user]["reaction_emoji"] = str(payload.emoji)
                await message.remove_reaction(current_emoji, user)
            else:
                member = discord.utils.get(guild.roles, name="Membre")
                friend = discord.utils.get(guild.roles, name="Ami.e")
                if member in raid.author.roles and friend in user.roles:
                    now = datetime.now(pytz.timezone("Europe/Paris"))
                    time_difference = raid.start_datetime - now
                    if time_difference >= timedelta(hours=2):
                        logger.info(
                            f"User {user.display_name} tried to react to raid {message.id} 2h before start"
                        )
                        await user.send(
                            embed=ErrorEmbed(
                                description=f"Because you are not a Member, you can only participate 2 hours before the raid starts"
                            )
                        )
                        await message.remove_reaction(payload.emoji, user)
                        return
                raid.add_participant(user, str(payload.emoji))
                thread = channel.get_thread(message.id)
                await thread.add_user(user)
            embed = raid.to_embed(self.bot.emoji_dict.get(payload.guild_id, []))
            await message.edit(embed=embed)
            update_raid_in_db(raid)
            logger.info(
                f"User {user.name} added {payload.emoji} as reaction to raid {message.id}"
            )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id)
        raid = self.bot.raids.get(payload.message_id)
        if (
            not raid
            or user.bot
            or raid.get_participant_emoji(user) != str(payload.emoji)
        ):
            return
        if raid is not None:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            raid.remove_participant(user)
            thread = channel.get_thread(message.id)
            await thread.remove_user(user)
            await message.edit(
                embed=raid.to_embed(self.bot.emoji_dict.get(payload.guild_id, []))
            )
            update_raid_in_db(raid)
            logger.info(
                f"User {user.name} removed {payload.emoji} as reaction to raid {message.id}"
            )

    @app_commands.command(name="start_session")
    @app_commands.describe(
        raid_name="Name of the raid",
        start_date="Raid date (YYYY-MM-DD)",
        start_time="Raid start time (HH:MM)",
        duration="Raid duration in hour (default: 1)",
        max_participants="Max number of participants (if you want to override default max)",
    )
    @app_commands.choices(
        raid_name=[
            Choice(name="Alzanor", value="Alzanor"),
            Choice(name="Arma", value="Arma"),
            Choice(name="Belial", value="Belial"),
            Choice(name="Carno", value="Carno"),
            Choice(name="Draco+Glacerus", value="DraGla"),
            Choice(name="Erenia", value="Erenia"),
            Choice(name="Fernon", value="Fernon"),
            Choice(name="Glacerus", value="Glacerus"),
            Choice(name="Kirollas", value="Kirollas"),
            Choice(name="Laurena", value="Laurena"),
            Choice(name="Paimon", value="Paimon"),
            Choice(name="Pollutus", value="Pollutus"),
            Choice(name="Valehir", value="Valehir"),
            Choice(name="Zenas", value="Zenas"),
        ]
    )
    async def start_session(
        self,
        interaction: discord.Interaction,
        raid_name: str,
        start_date: str,
        start_time: str,
        duration: int = 1,
        max_participants: int | None = None,
    ):
        """Start a new raid session with specified inputs"""
        await interaction.response.send_message(f"Creating raid", ephemeral=True)
        role = discord.utils.get(
            interaction.channel.guild.roles,
            name=f"Raideur {interaction.channel.category}",
        )
        start_date_obj = parse_date(start_date)
        start_time_obj = parse_time(start_time)
        if start_date_obj is None or start_time_obj is None:
            await interaction.edit_original_response(
                embed=ErrorEmbed(
                    description="Date or time format was wrong. Please try again"
                )
            )
            return
        tz = pytz.timezone("Europe/Paris")
        message = await interaction.channel.send(
            content=role.mention + f"Nouvelle session {raid_name} en création"
        )
        if not max_participants:
            max_participants = RAID_TEMPLATES[raid_name]["max_participants"]
        logger.info(f"{interaction.user} created a new raid")
        new_raid = Raid(
            message=message,
            raid_name=raid_name,
            author=interaction.user,
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            start_datetime=tz.localize(
                datetime.combine(start_date_obj, start_time_obj)
            ),
            duration=duration,
            max_participants=max_participants,
            participants={},
        )
        view = RaidView(raid=new_raid, bot=self.bot)

        embed = new_raid.to_embed(self.bot.emoji_dict.get(interaction.guild_id, []))

        await message.edit(content=role.mention, embed=embed, view=view)
        self.bot.raids[message.id] = new_raid

        # bench_emoji = discord.PartialEmoji(name="bench", id=1097864481461260369)
        await message.add_reaction("⚔️")
        await message.add_reaction("🏹")
        await message.add_reaction("🧙")
        await message.add_reaction("🤜")
        thread = await message.create_thread(
            name=f"Session {new_raid.raid_name} - {new_raid.start_datetime.strftime('%Y-%m-%d %H:%M')}"
        )
        if RAID_TEMPLATES[raid_name].get("opt_images"):
            for img in RAID_TEMPLATES[raid_name]["opt_images"]:
                with open(img, "rb") as f:
                    image = discord.File(f)
                    await thread.send(file=image)
        update_raid_in_db(new_raid)
        await interaction.edit_original_response(content="Raid fully created")

    @app_commands.command(name="remove_from_raid")
    @app_commands.describe(user_to_rm="Name of the user to remove")
    async def remove_from_raid(self, interaction: discord.Interaction, user_to_rm: str):
        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.defer(ephemeral=True, thinking=True)
            original_message_id = interaction.channel.id
            raid = self.bot.raids.get(original_message_id)
            admin = discord.utils.get(interaction.guild.roles, name="Assistant/Gardien")
            if (
                interaction.user.id != raid.author.id
                and admin not in interaction.user.roles
            ):
                await interaction.followup.send(
                    embed=ErrorEmbed(
                        description=f"You are not the creator of this raid or have {admin.mention} role"
                    )
                )
                return
            for user in raid.participants.keys():
                if user_to_rm.lower() in user.name.lower() or (
                    user.nick and user_to_rm.lower() in user.nick.lower()
                ):
                    await raid.message.remove_reaction(
                        raid.get_participant_emoji(user), user
                    )
                    raid.remove_participant(user)
                    await interaction.channel.remove_user(user)
                    await interaction.edit_original_response(
                        content=f"{user.name} removed from raid"
                    )
                    update_raid_in_db(raid)
                    await raid.message.edit(
                        embed=raid.to_embed(
                            self.bot.emoji_dict.get(interaction.guild_id, [])
                        )
                    )
                    return
            await interaction.followup.send(
                content=f"Couldn't find a match for: {user_to_rm}"
            )
            return
        else:
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    description="This command can only be used inside a raid thread created by this bot",
                ),
                ephemeral=True,
            )
            return

    @app_commands.command(name="add_to_raid")
    @app_commands.describe(
        user_to_add="@Mention the user to add", reaction="User class"
    )
    @app_commands.choices(
        reaction=[
            Choice(name="⚔️ Escri", value="⚔️"),
            Choice(name="🏹 Archer", value="🏹"),
            Choice(name="🧙 Mage", value="🧙"),
            Choice(name="🤜 Artiste Martial", value="🤜"),
        ]
    )
    async def add_to_raid(
        self,
        interaction: discord.Interaction,
        user_to_add: discord.Member,
        reaction: str,
    ):
        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.defer(ephemeral=True, thinking=True)
            original_message_id = interaction.channel.id
            raid = self.bot.raids.get(original_message_id)
            if len(raid.participants) >= raid.max_participants:
                await interaction.followup.send(
                    embed=ErrorEmbed(description=f"Raid is full")
                )
                return
            if user_to_add in raid.participants:
                await interaction.followup.send(
                    embed=ErrorEmbed(
                        description=f"Player {user_to_add} is already in raid."
                    )
                )
                return
            else:
                raid.add_participant(user=user_to_add, reaction_emoji=reaction)
                await interaction.channel.add_user(user_to_add)
                update_raid_in_db(raid)
                await interaction.followup.send(
                    content=f"Player {user_to_add} was added to the raid."
                )
                await raid.message.edit(
                    embed=raid.to_embed(
                        self.bot.emoji_dict.get(interaction.guild_id, [])
                    )
                )
                return
        else:
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    description="This command can only be used inside a raid thread created by this bot",
                ),
                ephemeral=True,
            )
            return

    @app_commands.command(name="result")
    @app_commands.describe(number_of_raids="Number of raids done in total")
    async def result(self, interaction: discord.Interaction, number_of_raids: int):
        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.defer(ephemeral=True, thinking=True)
            original_message_id = interaction.channel.id
            raid = self.bot.raids.get(original_message_id)
            if number_of_raids <= 0:
                await interaction.followup.send(
                    embed=ErrorEmbed(description=f"Number of raids should be > 0.")
                )
                return
            else:
                raid.nb_of_raids = number_of_raids
                update_raid_in_db(raid)
                await interaction.followup.send(content=f"Raid result updated")
                await raid.message.edit(
                    embed=raid.to_embed(
                        self.bot.emoji_dict.get(interaction.guild_id, [])
                    )
                )
                return
        else:
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    description="This command can only be used inside a raid thread created by this bot",
                ),
                ephemeral=True,
            )
            return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RaidCog(bot))
