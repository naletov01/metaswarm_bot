# main.py 

import logging
from anyio import to_thread
from fastapi import Depends
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, BotCommand
from menu import CB_MAIN, CB_PROFILE

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
from handlers import (
    start, image_upload_handler, text_handler, menu_callback, 
    on_check_sub, choose_model, profile, partner)

# ─────────────────────────────────────────────────────────────────────────────
from sqlalchemy import (
    Column, Integer, Boolean, DateTime, String, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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

Base = declarative_base()
SessionLocal = sessionmaker(autoflush=False, autocommit=False)

if DATABASE_URL.startswith("sqlite://"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    engine = create_engine(DATABASE_URL, echo=False)
SessionLocal.configure(bind=engine)

class User(Base):
    __tablename__ = 'users'
    user_id         = Column(Integer, primary_key=True, index=True)
    credits         = Column(Integer, default=0, nullable=False)
    premium         = Column(Boolean, default=False, nullable=False)
    subscription_type = Column(String, nullable=True)
    premium_until   = Column(DateTime, nullable=True)
    invited_count   = Column(Integer, default=0, nullable=False)
    bonus_credits   = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

@app.on_event("startup")
def init_db():
    Base.metadata.create_all(bind=engine)

@app.on_event("startup")
async def setup_webhook():
    result: bool = await to_thread.run_sync(
        bot.set_webhook,
        f"{config.WEBHOOK_URL}{WEBHOOK_PATH}"
    )
    if not result:
        logger.warning("Не удалось установить webhook")

# ─────────────────────────────────────────────────────────────────────────────


dp = Dispatcher(bot=bot, update_queue=None, use_context=True)

bot.set_my_commands([
    BotCommand("start",        "🏠 Главное меню"),
    BotCommand("choose_model", "🎞 Генерация видео"),
    BotCommand("profile",      "👤 Профиль"),
    # BotCommand("info",         "ℹ️ О генеративных моделях"),
    BotCommand("partner",      "🤑 Партнёрская программа"),
])

# ——— Регистрация хендлеров ———
dp.add_handler(CommandHandler("start",        start))
dp.add_handler(CommandHandler("choose_model", choose_model))
dp.add_handler(CommandHandler("profile",      profile))
# dp.add_handler(CommandHandler("info",         info))
dp.add_handler(CommandHandler("partner",      partner))
dp.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^(menu:|gen:)"))
dp.add_handler(CallbackQueryHandler(on_check_sub, pattern="^check_sub$"))
dp.add_handler(CallbackQueryHandler(menu_callback, pattern=f"^{CB_PROFILE}$"))
dp.add_handler(CallbackQueryHandler(menu_callback, pattern=f"^{CB_MAIN}$"))

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
def root():
    return {"status": "Bot is running"}







