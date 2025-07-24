import asyncio
from telegram import Bot

BOT_TOKEN = "8055550422:AAHJBLWXMDPagmVN2epGQOb5ig0xtdcb0_U"
CHAT_ID = "-1002773253048"

bot = Bot(token=BOT_TOKEN)

async def send_test_message():
    await bot.send_message(chat_id=CHAT_ID, text="Hy")

asyncio.run(send_test_message())