# main.py 

import logging
from anyio import to_thread
from fastapi import FastAPI, Request, HTTPException, Depends
from telegram import Update, BotCommand
from sqlalchemy.orm import Session
from db import engine, Base, get_db
import config
import handlers
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler,
    Filters, CallbackContext, CallbackQueryHandler)
from handlers import (
    start, image_upload_handler, text_handler, menu_callback, 
    on_check_sub, choose_model, profile, partner)


# ——— Настройка логирования ———
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# подтягиваем Bot и путь вебхука из config
bot = config.bot
WEBHOOK_PATH = config.WEBHOOK_PATH
DATABASE_URL = config.DATABASE_URL

app = FastAPI()


@app.on_event("startup")
async def startup():
    # 1) Инициализация БД (idempotent)
    try:
        await to_thread.run_sync(Base.metadata.create_all, engine)
        logger.info("DB init: OK")
    except Exception:
        logger.exception("DB init failed")
        raise
    # 2) Выставление вебхука
    try:
        # аккуратно склеиваем базовый URL и путь
        base = config.WEBHOOK_URL.rstrip("/")
        path = WEBHOOK_PATH if WEBHOOK_PATH.startswith("/") else "/" + WEBHOOK_PATH
        url = base + path

        ok = await to_thread.run_sync(bot.set_webhook, url,)
        
        if not ok:
            logger.warning("Webhook set failed for %s", url)
        else:
            info = await to_thread.run_sync(bot.get_webhook_info)
            logger.info("Webhook set: %s (pending_update_count=%s)", info.url, getattr(info, "pending_update_count", None))
    except Exception:
        logger.exception("Webhook setup failed")
        raise

# # main.py (startup)
# @app.on_event("startup")
# def startup():
#     Base.metadata.create_all(bind=engine)
#     from db import ensure_bigint_ids
#     try:
#         ensure_bigint_ids()
#     except Exception:
#         logger.exception("ensure_bigint_ids failed")  # не падаем на старте


dp = Dispatcher(bot=bot, update_queue=None, use_context=True)

bot.set_my_commands([
    BotCommand("start",        "🏠 Главное меню"),
    BotCommand("choose_model", "🎞 Генерация видео"),
    BotCommand("profile",      "👤 Профиль"),
    BotCommand("partner",      "🤑 Партнёрская программа"),
])

# ——— Регистрация хендлеров ———
dp.add_handler(CommandHandler("start", start, pass_args=True))
dp.add_handler(CommandHandler("choose_model", choose_model))
dp.add_handler(CommandHandler("profile",      profile))
dp.add_handler(CommandHandler("partner",      partner))
dp.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^(menu:|gen:)"))
dp.add_handler(CallbackQueryHandler(on_check_sub, pattern="^check_sub$"))

img_filter = Filters.photo | (Filters.document & Filters.document.mime_type("image/*"))
dp.add_handler(MessageHandler(img_filter, image_upload_handler))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))


def error_handler(update, context):
    logger.exception("Error in handler", exc_info=context.error)
dp.add_error_handler(error_handler)


# ——— Webhook endpoint ———
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request, db=Depends(get_db)):
    data = await request.json()
    update = Update.de_json(data, bot)
    await to_thread.run_sync(dp.process_update, update)
    return {"ok": True}


@app.get("/")
@app.head("/")
def root():
    return {"status": "Bot is running"}


