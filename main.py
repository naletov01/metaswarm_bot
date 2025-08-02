# main.py 

import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, BotCommand

import config
import handlers
from telegram.ext import (
    Dispatcher,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler
)
import replicate

from menu import CB_MAIN
from config import bot, WEBHOOK_PATH
from handlers import (
    start, image_upload_handler, text_handler, menu_callback, 
    on_check_sub, choose_model, profile, info, partner)

# подтягиваем Bot и путь вебхука из config
bot = config.bot
WEBHOOK_PATH = config.WEBHOOK_PATH

# ——— Настройка логирования ———
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
dp = Dispatcher(bot=bot, update_queue=None, use_context=True)

bot.set_my_commands([
    BotCommand("start",        "🏠 Главное меню"),
    BotCommand("choose_model", "🎞 Генерация видео"),
    BotCommand("profile",      "👤 Профиль"),
    BotCommand("info",         "ℹ️ О генеративных моделях"),
    BotCommand("partner",      "🤑 Партнёрская программа"),
])

# ——— Регистрация хендлеров ———
dp.add_handler(CommandHandler("start",        start))
dp.add_handler(CommandHandler("choose_model", choose_model))
dp.add_handler(CommandHandler("profile",      profile))
dp.add_handler(CommandHandler("info",         info))
dp.add_handler(CommandHandler("partner",      partner))
dp.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu:"))
dp.add_handler(CallbackQueryHandler(on_check_sub, pattern="^check_sub$"))
dp.add_handler(MessageHandler(Filters.photo | (Filters.document & Filters.document.mime_type("image/")), image_upload_handler))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))


# ——— Webhook endpoint ———
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    update = Update.de_json(data, bot)
    dp.process_update(update)
    return {"ok": True}

@app.get("/")
def root():
    return {"status": "Bot is running"}










