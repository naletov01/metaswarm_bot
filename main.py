# main.py

import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, Request, HTTPException
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import (
    Dispatcher,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
from openai import OpenAI
import replicate

import requests, io
from PIL import Image
import json

FUNCTIONS = [
  {
    "name": "generate_image",
    "description": "Создаёт изображение по текстовому промпту",
    "parameters": {
      "type": "object",
      "properties": {
        "prompt":   {"type":"string", "description":"Текстовый промпт"},
        "size":     {"type":"string", "enum":["1024x1024","512x512","256x256"]},
        "n":        {"type":"integer", "default":1}
      },
      "required": ["prompt","size"]
    }
  },
  {
    "name": "edit_image",
    "description": "Редактирует ранее загруженное изображение по промпту и маске (RGBA)",
    "parameters": {
      "type": "object",
      "properties": {
        "prompt":      {"type":"string"},
        "size":        {"type":"string", "enum":["1024x1024","512x512","256x256"]},
        "image_file":  {"type":"string","description":"ID файла в Telegram"},
        "mask_file":   {"type":"string","description":"PNG-маска в память как base64 или ID"}
      },
      "required": ["prompt","size","image_file"]
    }
  }
]

# ——— Настройка логирования ———
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ——— Конфиг ———
BOT_TOKEN           = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET      = os.getenv("WEBHOOK_SECRET")  # задайте в Render отдельно
WEBHOOK_PATH        = f"/webhook/{WEBHOOK_SECRET}"
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

if not all([BOT_TOKEN, WEBHOOK_SECRET, OPENAI_API_KEY, REPLICATE_API_TOKEN]):
    logger.error("Missing required environment variables")
    raise RuntimeError("Missing API keys or webhook secret")

# ——— Инициализация ———
bot = Bot(token=BOT_TOKEN)
app = FastAPI()
dp = Dispatcher(bot=bot, update_queue=None, use_context=True)

client = OpenAI(api_key=OPENAI_API_KEY)
replicate_client = replicate.Client(token=REPLICATE_API_TOKEN)

executor = ThreadPoolExecutor(max_workers=2)

# ——— In-memory хранилище ———
user_data   = {}  # user_id → {"mode": ..., "last_image": ..., "last_action": timestamp}
user_limits = {}  # user_id → {"images": int, "videos": int}

MIN_INTERVAL = 5  # сек между запросами

# ——— Вспомогательная функция для фоновой генерации видео ———
def generate_and_send_video(user_id, last_img, prompt):
    data   = user_data.setdefault(user_id, {})
    limits = user_limits.setdefault(user_id, {"images": 0, "videos": 0})
    try:
        output = replicate.run(
            "kwaivgi/kling-v2.1",
            input={
                "mode": "pro",
                "prompt": prompt,
                "duration": 5,
                "start_image": last_img,
                "negative_prompt": "",
            },
        )
        video_url = output.url()
        limits["videos"]    += 1
        data["last_action"]  = time.time()
        bot.send_video(chat_id=user_id, video=video_url)
    except Exception as e:
        logger.error(f"Background video generation failed: {e}")
        bot.send_message(chat_id=user_id, text="Ошибка генерации видео. Попробуйте позже.")

# ——— Хендлеры ———
def error_handler(update, context):
    logger.exception("Unhandled error in update")
dp.add_error_handler(error_handler)

def start(update: Update, context: CallbackContext):
    keyboard = [["🖼 Картинка", "🎞 Видео"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Выберите тип генерации:", reply_markup=markup)

def image_upload_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    # Обрабатываем фото или документ-изображение
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document and update.message.document.mime_type.startswith("image/"):
        file_id = update.message.document.file_id
    else:
        update.message.reply_text("Пожалуйста, отправьте изображение.")
        return

    try:
        file = context.bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        data = user_data.setdefault(user_id, {})
        data["last_image"] = file_url
        data["last_image_id"] = file_id
        data["upload_for_edit"] = True      # <-- флаг, что это исходное изображение для Image-to-Image
        update.message.reply_text(
            "Изображение сохранено для редактирования.\n"
            "Теперь введите текстовый промпт — будет использоваться вместе с загруженной картинкой."
        )
    except Exception as e:
        logger.error(f"Error saving uploaded image: {e}")
        update.message.reply_text("Не удалось сохранить изображение. Попробуйте ещё раз.")

def text_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text    = update.message.text.strip()
    now     = time.time()

    data   = user_data.setdefault(user_id, {})
    limits = user_limits.setdefault(user_id, {"images": 0, "videos": 0})

    # Защита от слишком частых запросов
    last = data.get("last_action", 0)
    if now - last < MIN_INTERVAL:
        wait = int(MIN_INTERVAL - (now - last))
        update.message.reply_text(f"Пожалуйста, подождите ещё {wait} сек.")
        return

    # Выбор режима
    if text in ["🖼 Картинка", "🎞 Видео"]:
        data["mode"] = "image" if "Картинка" in text else "video"
        update.message.reply_text("Введите текстовый промпт:")
        return

    mode = data.get("mode")

    # ——— Генерация изображения (T2I или I2I) ———
    if data.get("mode") == "image":
        update.message.reply_text("⏳ Обрабатываю запрос через GPT-4 Vision…")
    
        # Собираем сообщения
        messages = [
            {"role":"system","content":"Ты ассистент по генерации и редактированию изображений."}
        ]
        if data.get("last_image_id"):
            messages.append({
                "role":"user",
                "content":"Пожалуйста, отредактируй это изображение по промпту.",
                "image_file": data["last_image_id"]
            })
        else:
            messages.append({"role":"user","content": text})
    
        # Вызываем GPT с функциями
        resp = client.chat.completions.create(
            model="gpt-4o-mini",   # или gpt-4vision
            messages=messages,
            functions=FUNCTIONS,
            function_call="auto"
        )
    
        msg = resp.choices[0].message

        # функция вызвана?
        fn = getattr(msg, "function_call", None)
        if not fn:
            # ни одна функция не была вызвана — отправляем обычный текст
            text = msg.content or "Извините, не понял."
            update.message.reply_text(text)
            return
        
        name = fn.name
        args = json.loads(fn.arguments)
    
        if name == "generate_image":
            img = client.images.generate(
                model="dall-e-3",
                prompt=args["prompt"],
                size=args["size"],
                n=args.get("n",1)
            )
            url = img.data[0].url
            update.message.reply_photo(photo=url)
            data["last_image"] = url
    
        elif name == "edit_image":
            tg_file   = bot.get_file(args["image_file"])
            img_bytes = tg_file.download_as_bytearray()
            orig      = io.BytesIO(img_bytes)
    
            pil      = Image.open(orig).convert("RGBA")
            mask     = Image.new("RGBA", pil.size, (0,0,0,0))
            mb       = io.BytesIO(); mask.save(mb,"PNG"); mb.seek(0); orig.seek(0)
    
            out = client.images.edit(
                image  = ("image.png", orig, "image/png"),
                mask   = ("mask.png",  mb,   "image/png"),
                prompt = args["prompt"],
                size   = args["size"],
                n      = args.get("n",1)
            )
            url = out.data[0].url
            update.message.reply_photo(photo=url)
            data["last_image"] = url
    
        data.pop("upload_for_edit", None)
        limits["images"] += 1
        data["last_action"] = time.time()
        return

    # — Генерация видео —
    if mode == "video":
        last_img = data.get("last_image")
        if not last_img:
            update.message.reply_text("Сначала сгенерируйте или загрузите изображение.")
            return
        if limits["videos"] >= 1:
            update.message.reply_text("Лимит видео-генераций исчерпан.")
            return

        update.message.reply_text("⏳ Видео в работе, отправлю как будет готово.")
        # Запуск в фоне
        executor.submit(generate_and_send_video, user_id, last_img, text)
        return

    update.message.reply_text("Непонятно. Используйте /start для начала.")

# ——— Регистрация хендлеров ———
dp.add_handler(CommandHandler("start", start))
dp.add_handler(
    MessageHandler(
        Filters.photo | (Filters.document & Filters.document.mime_type("image/")),
        image_upload_handler
    )
)
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

# ——— Webhook endpoint (секрет в URL) ———
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
