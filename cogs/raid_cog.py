from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
from models.error_embed import ErrorEmbed
from models.raid import Raid

from utils.utils import update_raid_in_db
from nostale_bot import NostaleRaidHelperBot
from views.raid_view import RaidView
from logger import logger


class RaidCog(commands.Cog):
    def __init__(self, bot: NostaleRaidHelperBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):

        raid = self.bot.raids.get(payload.message_id)
        user = await self.bot.fetch_user(payload.user_id)
        if raid is None or user.bot:
            return
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if message.author != self.bot.user:
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
            update_raid_in_db(raid)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        user = await self.bot.fetch_user(payload.user_id)
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
            await message.edit(embed=raid.to_embed())
            update_raid_in_db(raid)

    @app_commands.command(name="start_raid")
    @app_commands.describe(
        raid_name="Name of the raid",
        start_date="Raid date (YYYY-MM-DD)",
        start_time="Raid start time (HH:MM)",
        max_participants="Max number of participants",
    )
    @app_commands.choices(
        raid_name=[
            Choice(name="Kiro", value="Kirollas"),
            Choice(name="Carno", value="Carno"),
            Choice(name="Erenia", value="Erenia"),
            Choice(name="Zenas", value="Zenas"),
            Choice(name="Fernon", value="Fernon"),
            Choice(name="Laurena", value="Laurena"),
            Choice(name="Belial", value="Belial"),
            Choice(name="Paimon", value="Paimon"),
        ]
    )
    async def start_raid(
        self,
        interaction: discord.Interaction,
        raid_name: str,
        start_date: str,
        start_time: str,
        max_participants: int | None = None,
    ):
        """Start a new raid with specified inputs"""
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
        self.bot.raids[message.id] = new_raid
        # bench_emoji = discord.PartialEmoji(name="bench", id=1097864481461260369)
        await message.add_reaction("⚔️")
        await message.add_reaction("🏹")
        await message.add_reaction("🪄")  # Wand emoji
        await message.add_reaction("🤜")
        await interaction.edit_original_response(content="Raid fully created")

    @app_commands.command(name="view")
    @app_commands.checks.has_role("Raideur")
    async def view(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Creating raid", ephemeral=True)
        new_raid = Raid(author=interaction.user, participants={}, max_participants=1)
        logger.info(f"{interaction.user} created a new raid")
        view = RaidView(raid=new_raid)
        role = discord.utils.get(interaction.channel.guild.roles, name="Raideur")
        message = await interaction.channel.send(
            content=role.mention, embed=new_raid.to_embed(), view=view
        )
        new_raid.message = message
        self.bot.raids[message.id] = new_raid
        update_raid_in_db(new_raid)
        await message.add_reaction("⚔️")
        await message.add_reaction("🏹")
        await message.add_reaction("🪄")  # Wand emoji
        await message.add_reaction("🤜")
        await message.create_thread(
            name=f"Raid {new_raid.raid_name} - {new_raid.start_datetime.isoformat()}"
        )

    @app_commands.command(name="eject")
    @app_commands.checks.has_role("Raideur")
    @app_commands.describe(user_name="Name of the user to remove")
    async def eject(self, interaction: discord.Interaction, user_name: str):
        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.defer(ephemeral=True, thinking=True)
            original_message_id = interaction.channel.id
            raid = self.bot.raids.get(original_message_id)
            if interaction.user.id != raid.author.id:
                await interaction.followup.send(
                    embed=ErrorEmbed(description="You are not the creator of this raid")
                )
                return
            for user in raid.participants.keys():
                if user_name in user.name:
                    if raid.message:
                        await raid.message.remove_reaction(
                            raid.get_participant_emoji(user), user
                        )
                        raid.remove_participant(user)
                        await interaction.edit_original_response(
                            content=f"{user.name} removed from raid"
                        )
                        update_raid_in_db(raid)
                        return
            await interaction.followup.send(
                content=f"Couldn't find a match for: {user_name}"
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
