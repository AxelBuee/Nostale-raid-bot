from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    JSON,
    BigInteger,
    String,
    DateTime,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from discord import User, Embed, Colour, Member, PartialEmoji, PartialMessage, Message
from discord.ext import commands
import datetime
from typing import List, Any
from babel.dates import format_date, format_time, get_timezone

load_dotenv()

Base = declarative_base()


def get_session():
    db_password = os.getenv("DB_PASSWORD")
    engine = create_engine(
        f"postgresql://postgres:{db_password}@db.mufzuhmjkoamnhljvgsn.supabase.co:5432/postgres"
    )
    Session = sessionmaker(bind=engine)
    session = Session()
    # Create tables if they don't exist
    Base.metadata.create_all(engine)

    return session


class RaidSQL(Base):
    __tablename__ = "raids"
    message_id = Column(BigInteger, primary_key=True)
    author_id = Column(BigInteger)
    raid_name = Column(String)
    start_datetime = Column(DateTime(timezone=True))
    max_participants = Column(Integer)
    participants = Column(JSON)
    nb_of_raids = Column(Integer)

    def __init__(
        self,
        author_id,
        raid_name,
        start_datetime,
        max_participants,
        message_id,
        participants,
        nb_of_raids,
    ):
        self.author_id: int = author_id
        self.raid_name: str = raid_name
        self.start_datetime: datetime.datetime = start_datetime
        self.message_id = message_id
        self.max_participants: int = max_participants
        self.participants: dict[int, dict[str, Any]] = participants
        self.nb_of_raids: int = nb_of_raids

    async def get_message(self, bot: commands.Bot) -> Message:
        channel_id = os.getenv("GENERAL_CH_ID")
        channel = bot.get_channel(int(channel_id))
        partial_message: PartialMessage = channel.get_partial_message(self.message_id)
        message = await partial_message.fetch()
        return message

    async def reacreate_participants(self, part_serialized: dict, bot: commands.Bot):
        participants = {}
        for user_id, data in part_serialized.items():
            user = await bot.fetch_user(int(user_id))
            participants[user] = data
        return participants

    async def to_raid(self, bot: commands.Bot):
        from models.raid import Raid

        author = await bot.fetch_user(self.author_id)
        message = await self.get_message(bot)
        participants = await self.reacreate_participants(self.participants, bot)
        raid = Raid(
            author=author,
            raid_name=self.raid_name,
            start_datetime=self.start_datetime,
            max_participants=self.max_participants,
            message=message,
            participants=participants,
            nb_of_raids=self.nb_of_raids,
        )
        return raid
