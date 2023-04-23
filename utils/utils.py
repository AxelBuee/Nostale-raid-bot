import asyncio
from datetime import datetime
from typing import List

from discord.ext import commands

from logger import logger
from db import RaidSQL, get_session
from models.raid import Raid


async def load_raids_from_db(bot: commands.Bot):
    session = get_session()
    today_end = datetime.combine(datetime.today(), datetime.max.time())
    raids_sql = session.query(RaidSQL).filter(RaidSQL.start_datetime >= today_end).all()
    to_raid_tasks = [raid_sql.to_raid(bot=bot) for raid_sql in raids_sql]
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


# def store_all_raids_in_db(raids: dict[int, Raid]):
#     session = get_session()
#     for message_id, raid in raids.items():
#         raid_sql = raid.to_raid_sql()
#         session.merge(raid_sql)
#         session.commit()
#     session.close()
