from discord import User, Embed, Colour, Member, PartialEmoji
import datetime
from typing import List


class Raid:
    def __init__(
        self,
        author,
        raid_name="Kiro",
        start_datetime=datetime.datetime.today(),
        max_participants=2,
        message=None,
    ):
        self.author: Member = author
        self.raid_name: str = raid_name
        self.start_datetime: datetime.datetime = start_datetime
        self.message = message
        self.max_participants: int = max_participants
        self.participants: List[User] = []

    def __str__(self):
        header = f"Session {self.raid_name}! \n Starting at : {self.start_datetime} \n {len(self.participants)}/{self.max_participants}"
        participants = "\n".join(member.mention for member in self.participants)
        header += f":\n{participants}"
        print(header)
        return header

    def add_participant(self, user: User):
        if (
            len(self.participants) < self.max_participants
            and user not in self.participants
        ):
            self.participants.append(user)
            return True
        return False

    def remove_participant(self, user: User):
        if user in self.participants:
            self.participants.remove(user)
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
            name="Date", value=self.start_datetime.strftime("%Y-%m-%d %H:%M:%S")
        )
        embed.add_field(
            name=f"Participants ({len(self.participants)}/{self.max_participants}):",
            value=self.get_participant_list_pprint(),
            inline=False,
        )
        return embed

    def get_participant_list_pprint(self):
        return "\n".join(member.mention for member in self.participants)
