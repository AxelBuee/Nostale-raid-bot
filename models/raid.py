from discord import User, Embed, Colour, Member, PartialEmoji
import datetime
from typing import List
from .participant import Participant
from babel.dates import format_date, format_time, get_timezone


class Raid:
    def __init__(
        self,
        author,
        raid_name="Kiro",
        start_datetime=datetime.datetime(
            year=2023,
            month=4,
            day=19,
            hour=23,
            minute=10,
            tzinfo=get_timezone("Europe/Paris"),
        ),
        max_participants=2,
        message=None,
    ):
        self.author: Member = author
        self.raid_name: str = raid_name
        self.start_datetime: datetime.datetime = start_datetime
        self.message = message
        self.max_participants: int = max_participants
        self.participants: List[Participant] = []

    def __str__(self):
        header = f"Session {self.raid_name}! \n Starting at : {self.start_datetime} \n {len(self.participants)}/{self.max_participants}"
        participants = "\n".join(
            participant.mention for participant in self.participants
        )
        header += f":\n{participants}"
        return header

    def add_participant(self, user: User, reaction_emoji):
        if (
            len(self.participants) < self.max_participants
            and user not in self.participants
        ):
            self.participants.append(Participant(user, reaction_emoji))
            return True
        return False

    def remove_participant(self, user: User):
        for participant in self.participants:
            if participant.user == user:
                self.participants.remove(participant)
                return True
        return False

    def get_participant_emoji(self, user: User) -> str | None:
        for participant in self.participants:
            if participant.user == user:
                return participant.reaction_emoji
        return None

    def set_participant_emoji(self, user: User, reaction_emoji):
        for participant in self.participants:
            if participant.user == user:
                participant.reaction_emoji = reaction_emoji
                return True
        return False

    def check_timeout(self):
        if datetime.datetime.now() > self.start_time + datetime.timedelta(minutes=30):
            return True
        else:
            return False

    def to_embed(self) -> Embed:
        embed = Embed(title=f"{self.raid_name} Raid", colour=Colour.dark_teal())
        bench_emoji = PartialEmoji(name="boss_a7_kirollas", id=1098302563520102471)
        embed.set_thumbnail(url=bench_emoji.url)
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
        return embed

    def get_participant_list_pprint(self):
        return "\n".join(
            f"{participant.reaction_emoji} {participant.user.mention}"
            for participant in self.participants
        )
