# config.py

import os
import threading
from collections import defaultdict
from telegram import Bot
from telegram.utils.request import Request as TelegramRequest
import replicate
from concurrent.futures import ThreadPoolExecutor

ADMIN_IDS = {487950979} 

# ——— Конфиг ———
BOT_TOKEN           = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET      = os.getenv("WEBHOOK_SECRET")
WEBHOOK_PATH        = f"/webhook/{WEBHOOK_SECRET}"
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

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

replicate_client = replicate.Client(token=REPLICATE_API_TOKEN)
executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)


if not all([BOT_TOKEN, WEBHOOK_SECRET, REPLICATE_API_TOKEN]):
    logger.error("Missing required environment variables")
    raise RuntimeError("Missing API keys or webhook secret")
