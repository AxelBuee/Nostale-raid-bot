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
from utils.utils import parse_date, parse_time, update_raid_in_db
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
        emoji_str = str(payload.emoji)
        if emoji_str in "🛡️❤️💀⚔️":
            current_emoji = raid.get_participant_emoji(user)

            if current_emoji == emoji_str:
                return  # déjà inscrit avec ce rôle, rien à faire

            if current_emoji:
                # L'utilisateur change de rôle : vérifie que le nouveau rôle a de la place
                if not raid.has_room_for_role(emoji_str):
                    await message.remove_reaction(payload.emoji, user)
                    await user.send(
                        embed=ErrorEmbed(description="Ce rôle est déjà complet")
                    )
                    return
                raid.participants[user]["reaction_emoji"] = emoji_str
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
                                description="Because you are not a Member, you can only participate 2 hours before the raid starts"
                            )
                        )
                        await message.remove_reaction(payload.emoji, user)
                        return

                added = raid.add_participant(user, emoji_str)
                if not added:
                    await message.remove_reaction(payload.emoji, user)
                    await user.send(
                        embed=ErrorEmbed(description="Ce rôle est déjà complet")
                    )
                    return

                thread = channel.get_thread(message.id)
                await thread.add_user(user)

            embed = raid.to_embed(self.bot.emoji_dict.get(payload.guild_id, []))
            await message.edit(embed=embed)
            update_raid_in_db(raid)
            logger.info(
                f"User {user.name} added {emoji_str} as reaction to raid {message.id}"
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
    )
    @app_commands.choices(
        raid_name=[
            Choice(name="Hardcore A5", value="Hardcore A5"),
            Choice(name="Hardcore A6", value="Hardcore A6"),
            Choice(name="Hardcore A7", value="Hardcore A7"),
            Choice(name="Hardcore A8", value="Hardcore A8"),
            Choice(name="Fernon Hellbound", value="Fernon Hellbound"),
        ]
    )
    async def start_session(
        self,
        interaction: discord.Interaction,
        raid_name: str,
        start_date: str,
        start_time: str,
        duration: int = 1,
    ):
        """Start a new raid session with specified inputs"""
        await interaction.response.send_message(
            f"Creating raid {raid_name}", ephemeral=True
        )
        role = discord.utils.get(
            interaction.channel.guild.roles,
            name="Verified",
        )
        if role is None:
            role = discord.utils.get(interaction.channel.guild.roles, name="Raideur")
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
        role_limits = RAID_TEMPLATES[raid_name]["role_limits"]
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
            role_limits=role_limits,
            participants={},
            guild_emojis=self.bot.emoji_dict.get(interaction.guild_id, []),
        )
        view = RaidView(raid=new_raid, bot=self.bot)

        embed = new_raid.to_embed(self.bot.emoji_dict.get(interaction.guild_id, []))

        await message.edit(content=role.mention, embed=embed, view=view)
        self.bot.raids[message.id] = new_raid

        # bench_emoji = discord.PartialEmoji(name="bench", id=1097864481461260369)
        await message.add_reaction("🛡️")
        await message.add_reaction("❤️")
        await message.add_reaction("💀")
        await message.add_reaction("⚔️")
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
            admin = discord.utils.get(interaction.guild.roles, name="Admin")
            lead = discord.utils.get(interaction.guild.roles, name="LEAD")

            is_author = interaction.user.id == raid.author.id
            is_admin = admin is not None and admin in interaction.user.roles
            is_lead = lead is not None and lead in interaction.user.roles

            if not (is_author or is_admin or is_lead):
                await interaction.followup.send(
                    embed=ErrorEmbed(
                        description="You are not the creator of this raid, or don't have the required Admin or LEAD role"
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
            Choice(name="🛡️ Tank", value="🛡️"),
            Choice(name="❤️ Healer", value="❤️"),
            Choice(name="💀 Debuffer", value="💀"),
            Choice(name="⚔️ DPS", value="⚔️"),
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
            if not raid.has_room_for_role(reaction):
                await interaction.followup.send(
                    embed=ErrorEmbed(description="This role is already full")
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
