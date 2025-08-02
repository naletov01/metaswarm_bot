import os
from collections import defaultdict
from telegram.utils.request import Request as TelegramRequest

# 1) Токены и ссылки
BOT_TOKEN           = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET      = os.getenv("WEBHOOK_SECRET")
WEBHOOK_PATH        = f"/webhook/{WEBHOOK_SECRET}"
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

CHANNEL_LINK     = "https://t.me/metaswarm_01"
CHANNEL_USERNAME = "metaswarm_01"

# 2) Пулы и семафор
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "6"))
REQUEST_KWARGS = TelegramRequest(con_pool_size=(MAX_CONCURRENT * 2) + 10)

# 3) Внутреннее хранилище
user_data   = {}               # {user_id: {...}}
user_limits = defaultdict(int) # {user_id: int}

# 4) Промпты
NEGATIVE_PROMPT = (
    "bad eyes, bad hands, missing fingers, extra fingers, ugly, bad anatomy, blurry, "
    "bad quality, worst quality, worst detail, sketch, watermark, signature, artist name, "
    "extra limbs, lowres, disfigured face, malformed, deformities, fused limbs, disconnected limbs, "
    "duplicate limbs, mutated hands, mutated limbs, unnatural pose, asymmetrical eyes, asymmetry, "
    "physical-defects, unhealthy-deformed-joints, unhealthy-hands, unhealthy-feet, "
    "jpeg artifacts, cropped, duplicate"
)
POSITIVE_PROMPT = (
    "masterpiece, best quality, high resolution, cinematic lighting, detailed, "
    "perfect composition, ultra realistic, 4k, colorful, sharp focus, "
    "depth of field, detailed eyes, perfect eyes, realistic eyes"
)

# 5) Спиннер-интервал
MIN_INTERVAL = 5  # сек между сообщениями UPLOAD_VIDEO

