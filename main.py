import os

from dotenv import load_dotenv

from nostale_bot import NostaleRaidHelperBot

load_dotenv()

bot = NostaleRaidHelperBot()
bot.run(os.getenv("BOT_TOKEN"))
