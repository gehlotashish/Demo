from telegram.ext import ApplicationBuilder, CommandHandler

# TOKEN = ""

# async def chatid(update, context):
#     chat_id = update.effective_chat.id
#     await update.message.reply_text(f"Your Chat ID is: `{chat_id}`", parse_mode="Markdown")

# def main():
#     app = ApplicationBuilder().token(TOKEN).build()
#     app.add_handler(CommandHandler("chatid", chatid))
#     app.run_polling()

# if __name__ == "__main__":
#     main()


import telebot

BOT_TOKEN = '8055550422:AAHJBLWXMDPagmVN2epGQOb5ig0xtdcb0_U'

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda message: True)
def get_group_id(message):
    chat = message.chat
    print(f"Chat Name: {chat.title}")
    print(f"Chat ID: {chat.id}")

bot.polling()