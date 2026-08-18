from datetime import datetime, timedelta
from typing import Any, List

from babel.dates import format_date, format_time
from discord import Colour, Embed, Emoji, Member, Message

from db import RaidSQL
from templates.templates import RAID_TEMPLATES


PSP_LIST = [
    "akhenaton",
    "amon",
    "chloe",
    "ducat",
    "freya",
    "harle",
    "laurena",
    "lucifer",
    "dps",
    "palina",
    "perti",
    "ragnar",
    "venus",
    "all_psp",
]

ROLE_LABELS = {
    "🛡️": "Tank",
    "❤️": "Healer",
    "💀": "Debuffer",
    "⚔️": "DPS",
}
ROLE_ORDER = ["🛡️", "❤️", "💀", "⚔️"]


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
        role_limits: dict[str, int] | None = None,
        participants=None,
        nb_of_raids=0,
        guild_emojis=[],
    ):
        self.author: Member = author
        self.raid_name: str = raid_name
        self.start_datetime: datetime = start_datetime
        self.duration: int = duration
        self.message = message
        self.role_limits: dict[str, int] = role_limits or {}
        self.participants: dict[Member, dict[str, Any]] = participants
        self.nb_of_raids: int = nb_of_raids
        self.guild_id: int = guild_id
        self.channel_id: int = channel_id
        self.guild_emojis: List[Emoji] = guild_emojis

    @property
    def max_participants(self) -> int:
        """Total, calculé à partir des limites par rôle (garde la compat avec to_embed)."""
        return sum(self.role_limits.values())

    def __str__(self):
        str_raid = f"Session {self.raid_name}! \n Starting at : {self.start_datetime} \n Participants ({len(self.participants)}/{self.max_participants}):"
        str_raid += f"\n{self.get_participant_list_pprint()}"
        return str_raid

    def get_role_count(self, reaction_emoji: str) -> int:
        return sum(
            1
            for data in self.participants.values()
            if data["reaction_emoji"] == reaction_emoji
        )

    def has_room_for_role(self, reaction_emoji: str) -> bool:
        return self.get_role_count(reaction_emoji) < self.role_limits.get(
            reaction_emoji, 0
        )

    def add_participant(self, user: Member, reaction_emoji: str):
        if user in self.participants:
            return False
        if not self.has_room_for_role(reaction_emoji):
            return False
        self.participants[user] = {"reaction_emoji": reaction_emoji}
        return True

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
            (
                emoji
                for emoji in guild_emojis
                if RAID_TEMPLATES[self.raid_name]["boss_icon_name"].lower()
                in emoji.name
            ),
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
            name="Time",
            value=(
                f"`{format_time(self.start_datetime.time(), format='short', locale='fr_FR')}` - "
                f"`{format_time((self.start_datetime + timedelta(hours=self.duration)).time(), format='short', locale='fr_FR')}`"
            ),
        )
        embed.add_field(
            name="⏳", value=f"<t:{int(round(self.start_datetime.timestamp()))}:R>"
        )
        embed.add_field(name="👑 Leader", value=self.author.mention, inline=False)
        embed.add_field(
            name=f"👥 Team ({len(self.participants)}/{self.max_participants})",
            value="\u200b",
            inline=False,
        )
        for emoji in ROLE_ORDER:
            label = ROLE_LABELS[emoji]
            limit = self.role_limits.get(emoji, 0)
            count = self.get_role_count(emoji)
            participants_list = self.get_role_participant_list(emoji)
            embed.add_field(
                name=f"{emoji} {label} ({count}/{limit})",
                value=participants_list or "\u200b",
                inline=False,
            )
        remark = ""
        if RAID_TEMPLATES[self.raid_name].get("opt_messages"):
            remark = (
                remark
                + "\n"
                + "\n".join(RAID_TEMPLATES[self.raid_name]["opt_messages"])
            )
        if remark:
            embed.add_field(
                name="Remark",
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
            name="Time",
            value=(
                f"~~`{format_time(self.start_datetime.time(), format='short', locale='fr_FR')}` - "
                f"`{format_time((self.start_datetime + timedelta(hours=self.duration)).time(), format='short', locale='fr_FR')}`~~"
            ),
        )
        embed.add_field(
            name=f"**__SESSION CANCELLED__**",
            value=f"",
            inline=False,
        )
        return embed

    def get_participant_list_pprint(self, role=None):
        if role is None:
            sorted_participants = sorted(
                self.participants.items(), key=lambda x: x[1]["reaction_emoji"]
            )
        else:
            filtered_participants = filter(
                lambda x: x[1]["reaction_emoji"] == role, self.participants.items()
            )
            sorted_participants = sorted(
                filtered_participants, key=lambda x: x[1]["reaction_emoji"]
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
            role_limits=self.role_limits,
            message_id=self.message.id,
            participants=self.get_serialized_participants(),
            nb_of_raids=self.nb_of_raids,
            guild_id=self.guild_id,
            channel_id=self.channel_id,
        )

    def get_role_participant_list(self, reaction_emoji: str) -> str:
        """Liste des participants pour un rôle donné, en bullet points (sans l'emoji, déjà dans le header)."""
        participants = [
            (user, data)
            for user, data in self.participants.items()
            if data["reaction_emoji"] == reaction_emoji
        ]
        return "\n".join(f"• {user.mention}" for user, data in participants)
