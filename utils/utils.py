import asyncio
from datetime import datetime, date, time
from typing import List

import pytz
from discord.ext import commands

from db import RaidSQL, get_session
from logger import logger
from models.raid import Raid

DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]
TIME_FORMATS = ["%H:%M", "%Hh%M", "%HH%M"]


async def load_raids_from_db(bot: commands.Bot):
    session = get_session()
    today_start = datetime.now(pytz.timezone("Europe/Paris")).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    raids_sql = (
        session.query(RaidSQL).filter(RaidSQL.start_datetime >= today_start).all()
    )
    bot_guild_ids = [guild.id for guild in bot.guilds]
    to_raid_tasks = [
        raid_sql.to_raid(bot=bot)
        for raid_sql in raids_sql
        if raid_sql.guild_id in bot_guild_ids
    ]
    raids_list: List[Raid] = await asyncio.gather(*to_raid_tasks)
    session.close()
    return raids_list


def delete_raid_from_db(raid: Raid):
    session = get_session()
    raid = (
        session.query(RaidSQL)
        .filter_by(message_id=raid.message.id, channel_id=raid.channel_id)
        .first()
    )
    if raid:
        session.delete(raid)
        session.commit()
        logger.info(f"Deleted raid {raid.message_id} from database")
        return True
    return False


def update_raid_in_db(raid: Raid):
    session = get_session()
    raid_sql = raid.to_raid_sql()
    session.merge(raid_sql)
    session.commit()
    logger.info(f"Saved raid {raid.message.id} into database")


def generate_raids_dict(raids_list: List[Raid]) -> dict[int, Raid]:
    raids = {}
    for raid in raids_list:
        raids[raid.message.id] = raid
        logger.info(f"Loaded raid {raid.message.id} into memory dict")
    return raids


def parse_date(date_string: str) -> date | None:
    start_date_obj = None
    for date_format in DATE_FORMATS:
        try:
            start_date_obj = datetime.strptime(date_string, date_format).date()
            break
        except ValueError:
            pass
    return start_date_obj


def parse_time(time: str) -> time | None:
    start_time_obj = None
    for time_format in TIME_FORMATS:
        try:
            start_time_obj = datetime.strptime(time, time_format).time()
            break
        except ValueError:
            pass
    return start_time_obj
