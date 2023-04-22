import discord


class ErrorEmbed(discord.Embed):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, colour=discord.Colour.red())
