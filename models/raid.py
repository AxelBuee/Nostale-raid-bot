from discord import User, Embed, Colour, PartialEmoji, Message
import datetime
from typing import Any
from babel.dates import format_date, format_time, get_timezone
from db import RaidSQL


class Raid:
    def __init__(
        self,
        message: Message,
        author: User,
        raid_name="Kiro",
        start_datetime=datetime.datetime(
            year=2023,
            month=4,
            day=23,
            hour=23,
            minute=10,
            tzinfo=get_timezone("Europe/Paris"),
        ),
        max_participants=2,
        participants=None,
        nb_of_raids=0,
    ):
        self.author: User = author
        self.raid_name: str = raid_name
        self.start_datetime: datetime.datetime = start_datetime
        self.message = message
        self.max_participants: int = max_participants
        self.participants: dict[User, dict[str, Any]] = participants
        self.nb_of_raids: int = nb_of_raids

    def __str__(self):
        str_raid = f"Session {self.raid_name}! \n Starting at : {self.start_datetime} \n Participants ({len(self.participants)}/{self.max_participants}):"
        str_raid += f"\n{self.get_participant_list_pprint()}"
        return str_raid

    def add_participant(self, user: User, reaction_emoji: str):
        if (
            len(self.participants) < self.max_participants
            and user not in self.participants
        ):
            self.participants[user] = {"reaction_emoji": reaction_emoji}
            return True
        return False

    def remove_participant(self, user: User):
        if user in self.participants:
            del self.participants[user]
            return True
        return False

    def get_participant_emoji(self, user: User):
        return self.participants.get(user, {}).get("reaction_emoji")

    def to_embed(self) -> Embed:
        embed = Embed(title=f"{self.raid_name} Raid", colour=Colour.dark_teal())
        # raid_boss_emoji = PartialEmoji(name="boss_a7_kirollas", id=1098302563520102471)
        # embed.set_thumbnail(url=raid_boss_emoji.url)
        embed.set_author(name=self.author.name)
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
            value="`"
            + format_time(self.start_datetime.time(), format="short", locale="fr_FR")
            + "`",
        )
        embed.add_field(
            name=f"Participants ({len(self.participants)}/{self.max_participants}):",
            value=self.get_participant_list_pprint(),
            inline=False,
        )
        embed.add_field(name="Voc", value="<#688757693850452065>")
        if self.nb_of_raids != 0:
            embed.add_field(name="Result", value=f"{self.nb_of_raids} raids")
        return embed

    def get_participant_list_pprint(self):
        return "\n".join(
            f"{reactions['reaction_emoji']} {participant.mention}"
            for participant, reactions in self.participants.items()
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
            max_participants=self.max_participants,
            message_id=self.message.id,
            participants=self.get_serialized_participants(),
            nb_of_raids=self.nb_of_raids,
        )
