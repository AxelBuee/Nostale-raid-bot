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
from models.raid import Raid

# replace 'postgresql://user:password@host:port/dbname' with your actual database connection string
# engine = create_engine('postgresql://user:password@host:port/dbname')

load_dotenv()

Base = declarative_base()


class RaidSQL(Base):
    __tablename__ = "raids"
    id = Column(Integer, primary_key=True)
    author_id = Column(BigInteger)
    raid_name = Column(String)
    start_datetime = Column(DateTime)
    max_participants = Column(Integer)
    message_id = Column(BigInteger)
    participants = Column(JSON)

    def __init__(
        self,
        author_id,
        raid_name,
        start_datetime,
        max_participants,
        message_id,
    ):
        self.author_id: int = author_id
        self.raid_name: str = raid_name
        self.start_datetime: datetime.datetime = start_datetime
        self.message_id = message_id
        self.max_participants: int = max_participants
        self.participants: dict[int, dict[str, Any]] = {}

    async def get_author(self, bot: commands.Bot) -> User:
        return await bot.fetch_user(self.author_id)

    async def get_message(self, bot: commands.Bot) -> Message:
        channel_id = os.getenv("GENERAL_CH_ID")
        channel = bot.get_channel(channel_id)
        partial_message: PartialMessage = await channel.get_partial_message(
            self.message_id
        )
        message = await partial_message.fetch()
        return message

    async def to_raid(self, bot: commands.Bot) -> Raid:
        author = await self.get_author(bot)
        message = await self.get_message(bot)
        raid = Raid(
            author=author,
            raid_name=self.raid_name,
            start_datetime=self.start_datetime,
            max_participants=self.max_participants,
            message=message,
            participants=self.participants,
        )
        return raid


def connect_to_db():
    # Retrieve the database URL from an environment variable
    db_password = os.getenv("DB_PASSWORD")
    print(db_password)
    engine = create_engine(
        f"postgresql://postgres:{db_password}@db.mufzuhmjkoamnhljvgsn.supabase.co:5432/postgres"
    )
    Session = sessionmaker(bind=engine)

    # Create tables if they don't exist
    Base.metadata.create_all(engine)

    return Session
