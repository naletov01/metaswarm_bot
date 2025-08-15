# config.py

import os
import threading
import logging
from collections import defaultdict
from telegram import Bot
from telegram.utils.request import Request as TelegramRequest
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_IDS = {487950979} 

# ——— Конфиг ———
BOT_TOKEN           = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET      = os.getenv("WEBHOOK_SECRET")
WEBHOOK_PATH        = f"/webhook/{WEBHOOK_SECRET}"
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://metaswarm-bot.onrender.com")

#__________________________________________________________________________________
# Платежи Stars (через Bot API) — провайдер-токен НЕ нужен для XTR invoice link
STARS_ENABLED = True

# Fondy
FONDY_MERCHANT_ID = os.getenv("FONDY_MERCHANT_ID", "")
FONDY_MERCHANT_SECRET = os.getenv("FONDY_MERCHANT_SECRET", "")
FONDY_CURRENCY = "USD"

# CryptoBot
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")  # токен бота @CryptoBot
CRYPTOBOT_ACCEPTED_ASSETS = os.getenv("CRYPTOBOT_ACCEPTED_ASSETS")
CRYPTOBOT_FIAT = os.getenv("CRYPTOBOT_FIAT", "USD")
# CRYPTOBOT_CURRENCY = "USDT"
#__________________________________________________________________________________

# ——— Обязательная подписка ———
CHANNEL_LINK     = "https://t.me/metaswarm_01"  
CHANNEL_USERNAME = "metaswarm_01"               

# 2) Пулы и семафор
# максимально допустимое число параллельных видео‑генераций
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "6"))

# семафор, который будет блокировать вызовы сверх лимита
generate_semaphore = threading.Semaphore(MAX_CONCURRENT)

# создаём Bot с расширенным пулом соединений
telegram_req = TelegramRequest(con_pool_size=(MAX_CONCURRENT * 2) + 10)
bot = Bot(token=BOT_TOKEN, request=telegram_req)

# ——— In-memory хранилище ———
user_data = {}  # user_id → {"last_image": ..., "last_action": ..., "prompt": ..., "model": ...}
user_limits = defaultdict(int)  # user_id → {"videos": int}

# ——— Negative Prompt ———
NEGATIVE_PROMPT = (
    "bad eyes, bad hands, missing fingers, extra fingers, ugly, bad anatomy, blurry, "
    "bad quality, worst quality, worst detail, sketch, watermark, signature, artist name, "
    "extra limbs, lowres, disfigured face, malformed, deformities, fused limbs, disconnected limbs, "
    "duplicate limbs, mutated hands, mutated limbs, unnatural pose, asymmetrical eyes, asymmetry, "
    "physical-defects, unhealthy-deformed-joints, unhealthy-hands, unhealthy-feet, "
    "jpeg artifacts, cropped, duplicate"
)

# ——— Positive Prompt ———
POSITIVE_PROMPT = (
    "masterpiece, best quality, high resolution, cinematic lighting, detailed, "
    "perfect composition, ultra realistic, 4k, colorful, sharp focus, "
    "depth of field, detailed eyes, perfect eyes, realistic eyes"
)

# 5) Спиннер-интервал
MIN_INTERVAL = 5  # сек между сообщениями UPLOAD_VIDEO

executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)


# Стоимость одной генерации
COST_KLING_STD  = 100   # кредитов
COST_KLING_PRO  = 150
COST_KLING_MAST = 400
COST_VEO        = 650

# Подписки: сколько кредитов и на какой срок (в днях)
SUB_CREDITS   = {
    'day':   300,     # 3-дн. одноразово
    'month': 1000,    # ежемесячно
    'year':  12000,   # ежегодно
}
SUB_PERIOD_DAYS = {
    'day':   3,
    'month': 30,
    'year':  365,
}

# Пакеты кредитов (цена в $, кредиты)
PACKAGE_OPTIONS = {
    'standard': {'price_usd': 10, 'credits': 800},
    'pro':      {'price_usd': 30, 'credits': 3000},
    'max':      {'price_usd': 50, 'credits': 6000},
}

# Реферальная программа
BONUS_PER_INVITE = 30   # за каждые 5 приглашённых
MAX_INVITES      = 10     # максимум друзей

COSTS = {
    'kling-standard': COST_KLING_STD,
    'kling-pro':      COST_KLING_PRO,
    'kling-master':   COST_KLING_MAST,
    'veo':            COST_VEO,
}


if not all([BOT_TOKEN, WEBHOOK_SECRET, REPLICATE_API_TOKEN]):
    logger.error("Missing required environment variables")
    raise RuntimeError("Missing API keys or webhook secret")
