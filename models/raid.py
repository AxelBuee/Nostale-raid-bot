from discord import User

class Raid:
    def __init__(self, date, time, message, max_participants):
        self.date = date
        self.time = time
        self.message = message
        self.max_participants = max_participants
        self.participants = []

    def add_participant(self, user: User):
        if len(self.participants) < self.max_participants and user not in self.participants:
            self.participants.append(user)
            return True
        else:
            return False
        
    def check_timeout():
        if datetime.datetime.now() > start_time + datetime.timedelta(minutes=30):
            return True
        else:
            return False