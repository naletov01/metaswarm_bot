# main.py 

import logging
from fastapi import Depends
from datetime import datetime
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

from menu import CB_MAIN
from handlers import (
    start, image_upload_handler, text_handler, menu_callback, 
    on_check_sub, choose_model, profile, partner)

# ─────────────────────────────────────────────────────────────────────────────
from sqlalchemy import (
    Column, Integer, Boolean, DateTime, String, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine(
    if config.DATABASE_URL.startswith("sqlite://"):
        engine = create_engine(
        config.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
        )
    else:
        engine = create_engine(config.DATABASE_URL, echo=False)
        )
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

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

# При старте приложения:
@app.on_event("startup")
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# ─────────────────────────────────────────────────────────────────────────────

# подтягиваем Bot и путь вебхука из config
bot = config.bot
WEBHOOK_PATH = config.WEBHOOK_PATH

# ——— Настройка логирования ———
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()
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
# dp.add_handler(CommandHandler("profile",      profile))
dp.add_handler(CommandHandler("profile",     handlers.profile))
# dp.add_handler(CommandHandler("info",         info))
dp.add_handler(CommandHandler("partner",      partner))
dp.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^(menu:|gen:)"))
dp.add_handler(CallbackQueryHandler(on_check_sub, pattern="^check_sub$"))
dp.add_handler(MessageHandler(Filters.photo | (Filters.document & Filters.document.mime_type("image/")), image_upload_handler))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))



# ——— Webhook endpoint ———
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request, db=Depends(get_db)):
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







