import os
from nostale_bot import NostaleRaidHelperBot

from dotenv import load_dotenv


load_dotenv()

bot = NostaleRaidHelperBot()
bot.run(os.getenv("BOT_TOKEN"))
