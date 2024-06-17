import datetime
import os
from typing import Any

from discord import Guild, Message, PartialMessage
from discord.ext import commands
from dotenv import load_dotenv
import pytz
from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

Base = declarative_base()


def get_session():
    db_password = os.getenv("DB_PASSWORD")
    engine = create_engine(
        f"postgresql://postgres.mufzuhmjkoamnhljvgsn:{db_password}@aws-0-eu-west-2.pooler.supabase.com:6543/postgres"
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
    duration = Column(Integer)
    max_participants = Column(Integer)
    participants = Column(JSON)
    nb_of_raids = Column(Integer)
    guild_id = Column(BigInteger)
    channel_id = Column(BigInteger)

    def __init__(
        self,
        author_id,
        raid_name,
        start_datetime,
        duration,
        max_participants,
        message_id,
        participants,
        nb_of_raids,
        guild_id,
        channel_id,
    ):
        self.author_id: int = author_id
        self.raid_name: str = raid_name
        self.start_datetime: datetime.datetime = start_datetime
        self.duration: int = duration
        self.message_id = message_id
        self.max_participants: int = max_participants
        self.participants: dict[int, dict[str, Any]] = participants
        self.nb_of_raids: int = nb_of_raids
        self.guild_id: int = guild_id
        self.channel_id: int = channel_id

    async def get_message(self, bot: commands.Bot) -> Message:
        channel = bot.get_channel(self.channel_id)
        partial_message: PartialMessage = channel.get_partial_message(self.message_id)
        message = await partial_message.fetch()
        return message

    async def recreate_participants(self, part_serialized: dict, guild: Guild):
        participants = {}
        for user_id, data in part_serialized.items():
            user = guild.get_member(int(user_id))
            participants[user] = data
        return participants

    async def to_raid(self, bot: commands.Bot):
        from models.raid import Raid

        guild = bot.get_guild(self.guild_id)
        author = guild.get_member(self.author_id)
        message = await self.get_message(bot)
        participants = await self.recreate_participants(self.participants, guild)
        raid = Raid(
            message=message,
            raid_name=self.raid_name,
            author=author,
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            start_datetime=self.start_datetime.astimezone(
                pytz.timezone("Europe/Paris")
            ),
            duration=self.duration,
            max_participants=self.max_participants,
            participants=participants,
            nb_of_raids=self.nb_of_raids,
        )
        return raid
