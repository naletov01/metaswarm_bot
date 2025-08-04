# handlers.py

import config
import logging
import replicate

import time
import tempfile, requests, httpx, os 
import threading
from threading import Thread, Event
from telegram import (
    ChatAction, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    Update)
from telegram.ext import CallbackContext

from menu import render_menu, MENUS
from menu import CB_MAIN, CB_GENERATION, CB_PROFILE, CB_PARTNER 
from menu import CB_GEN_KLING_STD, CB_GEN_KLING_PRO, CB_GEN_KLING_MAST, CB_GEN_VEO  
from menu import MODEL_MAP, CB_SUB_PREMIUM
from config import (
    bot,                    # Telegram Bot
    executor,               # ThreadPoolExecutor
    generate_semaphore,     # Semaphore для очереди
    MIN_INTERVAL,           # Интервал анти-спама
    POSITIVE_PROMPT,        # Константа для prompt-а
    NEGATIVE_PROMPT,        # Константа для negative_prompt
    logger,                 # Логгер (или создайте свой через logging.getLogger)
    user_data,
    user_limits,
    CHANNEL_USERNAME,
    CHANNEL_LINK,
    replicate_client,
    ADMIN_IDS
)



def _keep_upload_action(bot, chat_id, stop_event):
    """
    Каждые 10 секунд шлёт Telegram-у статус UPLOAD_VIDEO,
    пока stop_event не станет установлен.
    """
    while not stop_event.is_set():
        bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
        stop_event.wait(10)


def check_subscription(user_id: int) -> bool:
    try:
        status = config.bot.get_chat_member(
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
    config.bot.send_message(
        chat_id=chat_id,
        text = (
            "👋 Привет!\n"
            "Перед тем как начать пользоваться ботом, подпишись на наш Telegram‑канал.\n\n"
            "Почему это важно?\n"
            "📌 Там я делюсь готовыми промптами для создания трендовых и красивых видео.\n"
            "📌 Ты сможешь быстрее находить идеи и получать лучшие результаты.\n"
            "📌 Канал — это не спам, а практическая библиотека, которая экономит твое время.\n\n"
            "👉 Подписка обязательна, ведь именно там будут публиковаться актуальные промпты и обновления для бота."
        ),
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ——— Фоновая генерация видео ———
def generate_and_send_video(user_id):
    logger.info(f"[{user_id}] ▶️ Запущена фоновая генерация видео")
    data = user_data.get(user_id, {})
    image_url = data.get("last_image")
    prompt    = data.get("prompt")
    model     = data.get("model", "kling-pro")
    
    # запускаем фоновой поток, который шлёт «upload_video» раз в 10 сек
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

            # 3) отправляем inline-меню «Сделать ещё видео»
            text, markup = render_menu(CB_GENERATION, user_id)
            bot.send_message(
                chat_id=user_id,
                text="Сделаем ещё видео? 🥹",
                reply_markup=markup,
                parse_mode="HTML"
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
        user_limits[user_id] += 1

    except Exception:
        logger.exception("Video generation error")
        bot.send_message(chat_id=user_id, text="❌ Ошибка генерации видео. Попробуйте позже.")

    finally:
        if tmp_file:
            try:
                os.remove(tmp_file.name)
            except OSError:
                pass                


def queued_generate_and_send_video(user_id):
    # дождаться свободного слота
    generate_semaphore.acquire()
    try:
        generate_and_send_video(user_id)
    finally:
        # отпустить слот
        generate_semaphore.release()


# ——— Хендлеры ———
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # 1) проверяем подписку — если не подписан, выходим и показываем промпт
    if not check_subscription(user_id):
        return send_subscribe_prompt(chat_id)

    # 2) если подписан — рендерим главное меню через menu.render_menu
    text, markup = render_menu(CB_MAIN, user_id)

    # 3) шлём его как HTML (чтобы теги <b> работали)
    update.message.reply_text(
        text,
        reply_markup=markup,
        parse_mode="HTML"
    )

# 2) Привязываем каждый «гл. пункт» к командам:
# /choose_model → Генерация
def choose_model(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if not check_subscription(user_id):
        return send_subscribe_prompt(chat_id)
    text, markup = render_menu(CB_GENERATION, user_id)
    update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")

# /profile → Профиль
def profile(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if not check_subscription(user_id):
        return send_subscribe_prompt(chat_id)
    text, markup = render_menu(CB_PROFILE, user_id)
    update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")

# # /info → О моделях
# def info(update: Update, context: CallbackContext):
#     user_id = update.effective_user.id
#     chat_id = update.effective_chat.id
#     if not check_subscription(user_id):
#         return send_subscribe_prompt(chat_id)
#     text, markup = render_menu(CB_INFO, user_id)
#     update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")

# /partner → Партнёрка
def partner(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if not check_subscription(user_id):
        return send_subscribe_prompt(chat_id)
    text, markup = render_menu(CB_PARTNER, user_id)
    update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")


def menu_callback(update: Update, context: CallbackContext):
    q = update.callback_query
    q.answer()
    uid = q.from_user.id
    chat_id = q.message.chat.id
    data = q.data
    
    has_premium = (uid in ADMIN_IDS) or (config.user_limits.get(uid, 0) > 0)
    
    # 1) Блокировка и выбор моделей
    if data in MODEL_MAP:
        if not has_premium:
            text, markup = render_menu(CB_SUB_PREMIUM, uid)
            return context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=markup,
                parse_mode="HTML"
            )

        # у пользователя есть премиум — сохраняем модель
        model = MODEL_MAP[data]
        user_data.setdefault(uid, {})["model"] = model

        if data == CB_GEN_VEO:
            return context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ Режим «{model}» выбран.\n"
                    "Теперь введите текстовый промпт для генерации видео (без загрузки изображения)."
                )
            )
        else:
            return context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ Режим «{model}» выбран.\n"
                    "Загрузите изображение, затем введите промпт для видео."
                )
            )

    # 2) блокируем навигацию, если отписался
    if not check_subscription(uid):
        return send_subscribe_prompt(chat_id)
        
    try:
        q.message.delete()
    except:
        pass

    # отрисовываем новое
    text, markup = render_menu(q.data, uid)
    context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=markup,
        parse_mode="HTML"
    )


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

        # 3) отправляем главное меню inline-кнопками
        text, markup = render_menu(CB_MAIN, uid)
        context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup,
            parse_mode="HTML"
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

        # 📌 если пользователь сразу указал подпись
        if update.message.caption:
            prompt = update.message.caption.strip()
            data["prompt"] = prompt
            update.message.reply_text("⏳ Генерирую видео по изображению и промпту… Обычно это занимает 3-5 минут, но иногда до 20 минут при большой очереди")
            executor.submit(queued_generate_and_send_video, user_id)
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
    limits = user_limits[user_id]

    # Защита от спама
    last = data.get("last_action", 0)
    if now - last < MIN_INTERVAL:
        wait = int(MIN_INTERVAL - (now - last))
        update.message.reply_text(f"Пожалуйста, подождите ещё {wait} сек.")
        return

    # Обработка промпта
    if data.get("last_image"):
        data["model"] = data.get("model", "kling-pro")
        data["prompt"] = text
        data["last_action"] = now
        update.message.reply_text("⏳ Видео генерируется… Обычно это занимает 3-5 минут, но иногда до 20 минут при большой очереди")
        executor.submit(queued_generate_and_send_video, user_id)
    else:
        update.message.reply_text("Пожалуйста, сначала загрузите изображение.")
