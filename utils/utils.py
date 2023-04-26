import asyncio
from datetime import datetime
from typing import List

import pytz
from discord.ext import commands

from db import RaidSQL, get_session
from logger import logger
from models.raid import Raid


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


def update_raid_in_db(raid: Raid):
    session = get_session()
    raid_sql = raid.to_raid_sql()
    session.merge(raid_sql)
    session.commit()
    logger.info(f"Saved {raid} into database")


def generate_raids_dict(raids_list: List[Raid]) -> dict[int, Raid]:
    raids = {}
    for raid in raids_list:
        raids[raid.message.id] = raid
        logger.info(f"Loaded {raid} into memory")
    return raids
