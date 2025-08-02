# main.py 

import logging
from fastapi import FastAPI, Request, HTTPException
from concurrent.futures import ThreadPoolExecutor
import replicate

import config
import handlers
from telegram.ext import (
    Dispatcher,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
from telegram.ext import CallbackQueryHandler


# ——— Настройка логирования ———
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

replicate_client = replicate.Client(token=REPLICATE_API_TOKEN)
executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)

app = FastAPI()
dp = Dispatcher(bot=bot, update_queue=None, use_context=True)


# ——— Регистрация хендлеров ———
dp.add_handler(CallbackQueryHandler(on_check_sub, pattern="^check_sub$"))
dp.add_handler(CommandHandler("start", start))
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










