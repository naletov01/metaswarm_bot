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
import replicate
import tempfile
import requests
import httpx
import threading
from telegram import ChatAction
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler



# ——— Настройка логирования ———
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ——— Конфиг ———
BOT_TOKEN           = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET      = os.getenv("WEBHOOK_SECRET")
WEBHOOK_PATH        = f"/webhook/{WEBHOOK_SECRET}"
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

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


# ——— Обязательная подписка ———
CHANNEL_LINK     = "https://t.me/metaswarm_01"  # ссылка на ваш канал
CHANNEL_USERNAME = "metaswarm_01"               # username канала без @


def _keep_upload_action(bot, chat_id, stop_event):
    """
    Каждые 15 секунд шлёт Telegram-у статус UPLOAD_VIDEO,
    пока stop_event не станет установлен.
    """
    while not stop_event.is_set():
        bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
        stop_event.wait(15)


def check_subscription(user_id: int) -> bool:
    try:
        status = bot.get_chat_member(
            chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id
        ).status
        return status in ("member", "creator", "administrator")
    except:
        return False

def send_subscribe_prompt(chat_id: int):
    kb = [
        [InlineKeyboardButton("✅ Подписаться", url=CHANNEL_LINK)],
        [InlineKeyboardButton("🔄 Я подписался", callback_data="check_sub")]
    ]
    bot.send_message(
        chat_id=chat_id,
        text="🔒 Подпишитесь на канал, чтобы пользоваться ботом:",
        reply_markup=InlineKeyboardMarkup(kb)
    )



if not all([BOT_TOKEN, WEBHOOK_SECRET, REPLICATE_API_TOKEN]):
    logger.error("Missing required environment variables")
    raise RuntimeError("Missing API keys or webhook secret")

bot = Bot(token=BOT_TOKEN)
app = FastAPI()
dp = Dispatcher(bot=bot, update_queue=None, use_context=True)
replicate_client = replicate.Client(token=REPLICATE_API_TOKEN)
executor = ThreadPoolExecutor(max_workers=2)

# ——— In-memory хранилище ———
user_data = {}  # user_id → {"last_image": ..., "last_action": ..., "prompt": ..., "model": ...}
user_limits = {}  # user_id → {"videos": int}

MIN_INTERVAL = 5  # сек между запросами

# ——— Фоновая генерация видео ———
def generate_and_send_video(user_id):
    data = user_data.get(user_id, {})
    image_url = data.get("last_image")
    prompt    = data.get("prompt")
    model     = data.get("model", "kling-pro")

    # запускаем фоновой поток, который шлёт «upload_video» раз в 15 сек
    stop_event = threading.Event()
    threading.Thread(
        target=_keep_upload_action,
        args=(bot, user_id, stop_event),
        daemon=True
    ).start()

    try:
        logger.info(f"Start video generation: model={model}, prompt={prompt}")
        logger.info(f"[{user_id}] 🌀 Генерация видео запущена...")

        # Скачиваем изображение из Telegram, если оно нужно
        tmp_file = None
        if model in ["kling-standard", "kling-pro", "kling-master"]:
            if not image_url:
                bot.send_message(chat_id=user_id, text="Сначала загрузите изображение.")
                return
            response = requests.get(image_url)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                tmp_file.write(response.content)
                tmp_file.flush()
            image_input = open(tmp_file.name, "rb")

        # Вызов нужной модели
        if model == "kling-standard":
            logger.info(f"[{user_id}] Генерация: модель={model}, prompt={prompt}, файл={image_url}")
            output = replicate.run(
                "kwaivgi/kling-v2.1",
                input={
                    "mode": "standard",
                    "prompt": f"{POSITIVE_PROMPT}, {prompt}",
                    "duration": 5,
                    "start_image": image_input,
                    "negative_prompt": NEGATIVE_PROMPT
                }
            )
        elif model == "kling-pro":
            logger.info(f"[{user_id}] Генерация: модель={model}, prompt={prompt}, файл={image_url}")
            output = replicate.run(
                "kwaivgi/kling-v2.1",
                input={
                    "mode": "pro",
                    "prompt": f"{POSITIVE_PROMPT}, {prompt}",
                    "duration": 5,
                    "start_image": image_input,
                    "negative_prompt": NEGATIVE_PROMPT
                }
            )
        elif model == "kling-master":
            logger.info(f"[{user_id}] Генерация: модель={model}, prompt={prompt}, файл={image_url}")
            output = replicate.run(
                "kwaivgi/kling-v2.1-master",
                input={
                    "prompt": f"{POSITIVE_PROMPT}, {prompt}",
                    "duration": 5,
                    "aspect_ratio": "9:16",
                    "start_image": image_input,
                    "negative_prompt": NEGATIVE_PROMPT
                }
            )
        elif model == "veo":
            logger.info(f"[{user_id}] Генерация: модель={model}, prompt={prompt}, файл={image_url}")
            output = replicate.run(
                "google/veo-3-fast",
                input={"prompt": prompt}
            )
        else:
            raise ValueError("Unknown model selected")

        video_url = output.url
        # 3) останавливаем поток с индикатором
        stop_event.set()
        logger.info(f"[{user_id}] ✅ Видео готово: {video_url}")
        
        # 🔍 HEAD-запрос к файлу (проверка доступности)
        try:
            check = httpx.head(video_url, timeout=10)
            logger.info(f"[{user_id}] HEAD status: {check.status_code}")
            if check.status_code != 200:
                bot.send_message(chat_id=user_id, text="⚠️ Видео ещё не готово. Попробуйте позже.\n" + video_url)
                return
        except Exception as e:
            logger.warning(f"[{user_id}] HEAD-запрос не удался: {e}")
            bot.send_message(chat_id=user_id, text="⚠️ Не удалось проверить видео. Вот ссылка:\n" + video_url)
            return
        
        # ✅ Твое видео готово!
        bot.send_message(
            chat_id=user_id,
            text="✅ Твое видео готово!"
        )

        # ✅ Отправка ролика как документ (скачаем и перешлём сами)
        try:
            # 1) скачиваем видео из replicate в tmp‑файл
            resp = requests.get(video_url, stream=True)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_vid:
                for chunk in resp.iter_content(chunk_size=8192):
                    tmp_vid.write(chunk)
                tmp_path = tmp_vid.name

            # 2) отправляем как документ
            with open(tmp_path, "rb") as f:
                bot.send_document(
                    chat_id=user_id,
                    document=f,
                    filename="video.mp4"
                )

            # 3) спрашиваем, делать ли ещё одно, и показываем клавиатуру
            keyboard = [
                ["🎞 Видео (Kling Standard)", "🎞 Видео (Kling Pro)"],
                ["🎞 Видео (Kling Master)",  "🎞 Видео (Veo)"]
            ]
            markup = ReplyKeyboardMarkup(
                keyboard,
                one_time_keyboard=True,
                resize_keyboard=True
            )
            bot.send_message(
                chat_id=user_id,
                text="Сделаем ещё видео? 🥹",
                reply_markup=markup
            )

        except Exception as e:
            logger.error(f"[{user_id}] ❌ Ошибка отправки документа: {e}")
            bot.send_message(
                chat_id=user_id,
                text="⚠️ Не удалось отправить видео. Вот ссылка:\n" + video_url
            )
        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)



        # ⏱ Обновляем лимиты
        user_limits.setdefault(user_id, {})["videos"] = user_limits[user_id].get("videos", 0) + 1

    except Exception as e:
        logger.error(f"Video generation error: {e}")
        bot.send_message(chat_id=user_id, text="❌ Ошибка генерации видео. Попробуйте позже.")
    finally:
        if tmp_file:
            try:
                os.remove(tmp_file.name)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
        if tmp_file:
            os.remove(tmp_file.name)


# ——— Хендлеры ———
def start(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not check_subscription(uid):
        return send_subscribe_prompt(uid)

    keyboard = [
       ["🎞 Видео (Kling Standard)", "🎞 Видео (Kling Pro)"],
       ["🎞 Видео (Kling Master)",  "🎞 Видео (Veo)"],
       ["🔄 Сменить модель"]  # новая кнопка
    ]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
    update.message.reply_text("Выберите модель генерации видео:", reply_markup=markup)


def on_check_sub(update: Update, context: CallbackContext):
    q = update.callback_query
    # сразу отвечаем на callback, чтобы убрать спиннер
    q.answer()

    user_id = q.from_user.id
    chat_id = q.message.chat.id

    if check_subscription(user_id):
        # удаляем старое сообщение-приглашение (молча, без падений)
        try:
            q.message.delete()
        except:
            pass

        # шлём меню выбора модели
        keyboard = [
            ["🎞 Видео (Kling Standard)", "🎞 Видео (Kling Pro)"],
            ["🎞 Видео (Kling Master)",  "🎞 Видео (Veo)"],
            ["🔄 Сменить модель"]
        ]
        markup = ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )
        context.bot.send_message(
            chat_id=chat_id,
            text="Выберите модель генерации видео:",
            reply_markup=markup
        )
    else:
        # если всё ещё не подписан — показываем alert
        q.answer("Я всё ещё не вижу вашу подписку.", show_alert=True)


def image_upload_handler(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not check_subscription(uid):
        return send_subscribe_prompt(uid)

    user_id = update.effective_user.id

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document and update.message.document.mime_type.startswith("image/"):
        file_id = update.message.document.file_id
    else:
        update.message.reply_text("Пожалуйста, отправьте изображение.")
        return

    try:
        file = context.bot.get_file(file_id)
        file_url = file.file_path

        data = user_data.setdefault(user_id, {})
        data["last_image"] = file_url
        data["last_image_id"] = file_id
        data["mode"] = "video"  # поскольку в новом флоу только видео

        # 📌 если пользователь сразу указал подпись
        if update.message.caption:
            prompt = update.message.caption.strip()
            data["prompt"] = prompt
            update.message.reply_text("⏳ Генерирую видео по изображению и промпту… Обычно это занимает 3-5 минут, но иногда до 20 минут при большой очереди")
            executor.submit(generate_and_send_video, user_id)
        else:
            update.message.reply_text("Изображение получено. Теперь введите промпт для генерации видео.")
    except Exception as e:
        logger.error(f"Error saving uploaded image: {e}")
        update.message.reply_text("Не удалось сохранить изображение. Попробуйте ещё раз.")
        

def text_handler(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not check_subscription(uid):
        return send_subscribe_prompt(uid)

    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if text == "🔄 Сменить модель":
        return start(update, context)
        
    now = time.time()
    data = user_data.setdefault(user_id, {})
    limits = user_limits.setdefault(user_id, {"videos": 0})

    # Защита от спама
    last = data.get("last_action", 0)
    if now - last < MIN_INTERVAL:
        wait = int(MIN_INTERVAL - (now - last))
        update.message.reply_text(f"Пожалуйста, подождите ещё {wait} сек.")
        return

    # Обработка выбора модели
    model_map = {
        "🎞 Видео (Kling Standard)": "kling-standard",
        "🎞 Видео (Kling Pro)": "kling-pro",
        "🎞 Видео (Kling Master)": "kling-master",
        "🎞 Видео (Veo)": "veo",
    }
    if text in model_map:
        data["model"] = model_map[text]
        update.message.reply_text(
        "Режим выбран. Теперь загрузите изображение и введите промпт. \n\n"
        "⚠️Важно!\n\n"
        "Чем качественнее изображение и точнее промпт(инструкция для видео), тем лучше генерация!"
        )
        return

    # Обработка промпта
    if data.get("last_image") and data.get("model"):
        data["prompt"] = text
        data["last_action"] = now
        update.message.reply_text("⏳ Видео генерируется… Обычно это занимает 3-5 минут, но иногда до 20 минут при большой очереди")
        executor.submit(generate_and_send_video, user_id)
    else:
        update.message.reply_text("Пожалуйста, сначала выберите модель и загрузите изображение.")

# ——— Регистрация хендлеров ———
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
