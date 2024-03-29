import discord
from discord import app_commands
from discord.ext import commands

from models.error_embed import ErrorEmbed


class UtilsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clear")
    @app_commands.checks.has_role("Assistant/Gardien")
    @app_commands.describe(
        nb_of_messages_to_delete="Number of messages to delete",
        delete_threads="Delete associated threads ?",
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        nb_of_messages_to_delete: int,
        delete_threads: str | None = None,
    ):
        """Clear a specified number of messages in the channel."""
        if nb_of_messages_to_delete <= 0:
            await interaction.response.send_message(
                "Please enter a positive integer.", ephemeral=True
            )
            return
        try:
            await interaction.response.defer(ephemeral=True)
            deleted_msg = await interaction.channel.purge(
                limit=nb_of_messages_to_delete
            )
            nb_deleted_threads = 0
            if delete_threads:
                for msg in deleted_msg:
                    thread = interaction.channel.get_thread(msg.id)
                    if thread:
                        await thread.delete()
                        nb_deleted_threads += 1
            await interaction.followup.send(
                f"Successfully cleared {len(deleted_msg)} messages and {nb_deleted_threads} threads.",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "I don't have permission to delete messages in this channel.",
                ephemeral=True,
            )
        except discord.HTTPException:
            await interaction.followup.send(
                "Failed to delete messages.", ephemeral=True
            )

    @clear.error
    async def on_clear_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        await interaction.response.send_message(
            embed=ErrorEmbed(description=str(error)), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilsCog(bot))
