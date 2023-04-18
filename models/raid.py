from discord import User,  Embed, Colour, Member
import datetime
from typing import List

class Raid:
    def __init__(self, author, raid_name, start_datetime, max_participants, message=None):
        self.author: Member = author,
        self.raid_name: str = raid_name
        self.start_datetime: datetime.datetime = start_datetime
        self.message = message
        self.max_participants: int = max_participants
        self.participants = []

    def __str__(self):
        header = f"Session {self.raid_name}! \n Starting at : {self.start_datetime} \n {len(self.participants)}/{self.max_participants}"
        participants = "\n".join(member.mention for member in self.participants)
        header+=f":\n{participants}"
        print(header)
        return header
    
    def add_participant(self, user: User):
        if len(self.participants) < self.max_participants and user not in self.participants:
            self.participants.append(user)
            return True
        else:
            return False
        
    def remove_participant(self, user: User):
        if user in self.participants:
            self.participants.remove(user)
        
    def check_timeout(self):
        if datetime.datetime.now() > self.start_time + datetime.timedelta(minutes=30):
            return True
        else:
            return False
        
    def to_embed(self) -> Embed:
        embed = Embed(title=f"{self.raid_name} Raid", colour=Colour.dark_teal())
        embed.set_author(name=self.author[0].name)
        embed.add_field(name="Date", value=self.start_datetime.strftime("%Y-%m-%d %H:%M:%S"))
        embed.add_field(name="Participants", value=self.get_participant_list_pretty_print())
        return embed
    
    def get_participant_list_pretty_print(self):
        participants = "\n".join(member.mention for member in self.participants)
        return f"Participants for {self.raid_name} ({len(self.participants)}/{self.max_participants}):\n{participants}"