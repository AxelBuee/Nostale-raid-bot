from datetime import datetime, timedelta
from typing import Any, List

from babel.dates import format_date, format_time
from discord import Colour, Embed, Emoji, Member, Message

from db import RaidSQL
from templates.templates import RAID_TEMPLATES


class Raid:
    def __init__(
        self,
        message: Message,
        raid_name: str,
        author: Member,
        guild_id: int,
        channel_id: int,
        start_datetime: datetime,
        duration=1,
        max_participants=2,
        participants=None,
        nb_of_raids=0,
    ):
        self.author: Member = author
        self.raid_name: str = raid_name
        self.start_datetime: datetime = start_datetime
        self.duration: int = duration
        self.message = message
        self.max_participants: int = max_participants
        self.participants: dict[Member, dict[str, Any]] = participants
        self.nb_of_raids: int = nb_of_raids
        self.guild_id: int = guild_id
        self.channel_id: int = channel_id

    def __str__(self):
        str_raid = f"Session {self.raid_name}! \n Starting at : {self.start_datetime} \n Participants ({len(self.participants)}/{self.max_participants}):"
        str_raid += f"\n{self.get_participant_list_pprint()}"
        return str_raid

    def add_participant(self, user: Member, reaction_emoji: str):
        if (
            len(self.participants) < self.max_participants
            and user not in self.participants
        ):
            self.participants[user] = {"reaction_emoji": reaction_emoji}
            return True
        return False

    def remove_participant(self, user: Member):
        if user in self.participants:
            del self.participants[user]
            return True
        return False

    def get_participant_emoji(self, user: Member):
        return self.participants.get(user, {}).get("reaction_emoji")

    def to_embed(self, guild_emojis: List[Emoji]) -> Embed:
        embed = Embed(
            title=f"Session {self.raid_name}",
            colour=Colour.from_rgb(*RAID_TEMPLATES[self.raid_name]["colour"]),
        )
        embed.set_author(name=f"{self.author.name} - {self.message.id}")
        thumbnail = next(
            (emoji for emoji in guild_emojis if self.raid_name.lower() in emoji.name),
            None,
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail.url)
        embed.add_field(
            name="Date",
            value="`"
            + format_date(
                self.start_datetime.date(), format="full", locale="fr_FR"
            ).capitalize()
            + "`",
        )
        embed.add_field(
            name="Heure",
            value=(
                f"`{format_time(self.start_datetime.time(), format='short', locale='fr_FR')}` - "
                f"`{format_time((self.start_datetime + timedelta(hours=self.duration)).time(), format='short', locale='fr_FR')}`"
            ),
        )
        embed.add_field(
            name="⏳", value=f"<t:{int(round(self.start_datetime.timestamp()))}:R>"
        )
        embed.add_field(
            name=f"Participants ({len(self.participants)}/{self.max_participants}):",
            value=self.get_participant_list_pprint(),
            inline=False,
        )
        remark = ""
        if RAID_TEMPLATES[self.raid_name].get("opt_messages"):
            remark = (
                remark
                + "\n"
                + "\n".join(RAID_TEMPLATES[self.raid_name]["opt_messages"])
            )
        embed.add_field(name="Voc", value="<#722139478248128652>")
        embed.add_field(
            name="Remarque",
            value=remark,
            inline=False,
        )
        if self.nb_of_raids != 0:
            embed.add_field(name="Result", value=f"{self.nb_of_raids} raids")
        return embed

    def to_cancel_embed(self, guild_emojis: List[Emoji]) -> Embed:
        embed = Embed(
            title=f"Session {self.raid_name}",
            colour=Colour.from_rgb(*RAID_TEMPLATES[self.raid_name]["colour"]),
        )
        embed.set_author(name=f"{self.author.name} - {self.message.id}")
        thumbnail = next(
            (emoji for emoji in guild_emojis if self.raid_name.lower() in emoji.name),
            None,
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail.url)
        embed.add_field(
            name="Date",
            value="~~`"
            + format_date(
                self.start_datetime.date(), format="full", locale="fr_FR"
            ).capitalize()
            + "`~~",
        )
        embed.add_field(
            name="Heure",
            value=(
                f"~~`{format_time(self.start_datetime.time(), format='short', locale='fr_FR')}` - "
                f"`{format_time((self.start_datetime + timedelta(hours=self.duration)).time(), format='short', locale='fr_FR')}`~~"
            ),
        )
        embed.add_field(
            name=f"**__SESSION ANNULÉE__**",
            value=f"",
            inline=False,
        )
        return embed

    def get_participant_list_pprint(self):
        sorted_participants = sorted(
            self.participants.items(), key=lambda x: x[1]["reaction_emoji"]
        )
        return "\n".join(
            f"{reactions['reaction_emoji']} {participant.mention}"
            for participant, reactions in sorted_participants
        )

    def get_serialized_participants(self):
        serialized = {}
        for user, data in self.participants.items():
            serialized[user.id] = data
        return serialized

    def to_raid_sql(self):
        return RaidSQL(
            self.author.id,
            raid_name=self.raid_name,
            start_datetime=self.start_datetime,
            duration=self.duration,
            max_participants=self.max_participants,
            message_id=self.message.id,
            participants=self.get_serialized_participants(),
            nb_of_raids=self.nb_of_raids,
            guild_id=self.guild_id,
            channel_id=self.channel_id,
        )
