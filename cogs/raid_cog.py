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
                raid.add_participant(user, str(payload.emoji))
            embed = raid.to_embed()
            await message.edit(embed=embed)
            update_raid_in_db(raid)
            logger.info(
                f"User {user.name} added {payload.emoji} as reaction to raid {message.id}"
            )

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
            logger.info(
                f"User {user.name} removed {payload.emoji} as reaction to raid {message.id}"
            )

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
        await message.add_reaction("🧙")  # Wand emoji
        await message.add_reaction("🤜")
        await interaction.edit_original_response(content="Raid fully created")

    @app_commands.command(name="view")
    @app_commands.describe(
        raid_name="Name of the raid",
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
    async def view(self, interaction: discord.Interaction, raid_name: str):
        await interaction.response.send_message(f"Creating raid", ephemeral=True)
        role = discord.utils.get(interaction.channel.guild.roles, name="Raideur")
        message = await interaction.channel.send(
            content=role.mention + f"Nouvelle session {raid_name} en création"
        )
        new_raid = Raid(
            raid_name=raid_name,
            author=interaction.user,
            message=message,
            participants={},
            max_participants=1,
        )
        logger.info(f"{interaction.user} created a new raid")
        view = RaidView(raid=new_raid)

        embed = new_raid.to_embed()
        emoji_list = await interaction.guild.fetch_emojis()
        thumbnail = next(
            (emoji for emoji in emoji_list if raid_name.lower() in emoji.name), None
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail.url)

        await message.edit(content=role.mention, embed=embed, view=view)
        self.bot.raids[message.id] = new_raid
        await message.add_reaction("⚔️")
        await message.add_reaction("🏹")
        await message.add_reaction("🧙")
        await message.add_reaction("🤜")
        await message.create_thread(
            name=f"Session {new_raid.raid_name} - {new_raid.start_datetime.isoformat()}"
        )  # TODO: Change time format ?
        update_raid_in_db(new_raid)

    @app_commands.command(name="remove_from_raid")
    @app_commands.describe(user_to_rm="Name of the user to remove")
    async def remove_from_raid(self, interaction: discord.Interaction, user_to_rm: str):
        if isinstance(interaction.channel, discord.Thread):
            await interaction.response.defer(ephemeral=True, thinking=True)
            original_message_id = interaction.channel.id
            raid = self.bot.raids.get(original_message_id)
            admin = discord.utils.get(interaction.guild.roles, name="Assitant/Gardien")
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
                if user_to_rm.lower() in user.name.lower():
                    await raid.message.remove_reaction(
                        raid.get_participant_emoji(user), user
                    )
                    raid.remove_participant(user)
                    await interaction.edit_original_response(
                        content=f"{user.name} removed from raid"
                    )
                    update_raid_in_db(raid)
                    await raid.message.edit(embed=raid.to_embed())
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
    @app_commands.describe(user_to_add="Mention the user to add", reaction="User class")
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

                update_raid_in_db(raid)
                await interaction.followup.send(
                    content=f"Player {user_to_add} was added to the raid."
                )
                await raid.message.edit(embed=raid.to_embed())
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
                await raid.message.edit(embed=raid.to_embed())
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
