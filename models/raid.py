from discord import User
import datetime
from typing import List

class Raid:
    def __init__(self, raid_name, start_datetime, max_participants, message=None):
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
    
    def get_participant_list_pretty_print(self):
        participants = "\n".join(member.mention for member in self.participants)
        return f"Participants for {self.raid_name} ({len(self.participants)}/{self.max_participants}):\n{participants}"