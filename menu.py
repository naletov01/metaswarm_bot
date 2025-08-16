# menu.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config
from config import COST_KLING_STD, COST_KLING_PRO, COST_KLING_MAST, COST_VEO, MAX_INVITES
from typing import Tuple
from db     import SessionLocal
from db_utils import get_user
from services.urls import build_urls_for_item
from models import User as UserModel

# ——— CALLBACK_DATA КОНСТАНТЫ ———
CB_MAIN            = "menu:main"
CB_GENERATION      = "menu:generation"
CB_PROFILE         = "menu:profile"
CB_PARTNER         = "menu:partner"

CB_SUB_PREMIUM     = "menu:sub_premium"
CB_BUY_CREDITS     = "menu:buy_credits"
CB_FREE_GEN        = "menu:free_gen"

CB_SUB_3D          = "menu:sub_3d"
CB_SUB_MONTH       = "menu:sub_month"
CB_SUB_YEAR        = "menu:sub_year"

CB_CRED_STD        = "menu:cred_std"
CB_CRED_PRO        = "menu:cred_pro"
CB_CRED_MAX        = "menu:cred_max"

# ——— CALLBACK_DATA ДЛЯ ГЕНЕРАЦИИ ———
CB_GEN_KLING_STD   = "gen:kling_standard"
CB_GEN_KLING_PRO   = "gen:kling_pro"
CB_GEN_KLING_MAST  = "gen:kling_master"
CB_GEN_VEO         = "gen:veo"

MODEL_MAP = {
    CB_GEN_KLING_STD:  "kling-standard",
    CB_GEN_KLING_PRO:  "kling-pro",
    CB_GEN_KLING_MAST: "kling-master",
    CB_GEN_VEO:        "veo",
}


# 1) Жёсткое соответствие экрана → товар
MENU_ITEM_BY_KEY = {
    CB_SUB_3D:    ("sub",  "day"),
    CB_SUB_MONTH: ("sub",  "month"),
    CB_SUB_YEAR:  ("sub",  "year"),
    CB_CRED_STD:  ("pack", "standard"),
    CB_CRED_PRO:  ("pack", "pro"),
    CB_CRED_MAX:  ("pack", "max"),
}

def _patch_payment_urls(user_id: int, kb_rows, menu_key: str):
    """
    Заменяет url='https://example.com' на живые ссылки,
    опираясь НЕ на текст кнопки, а на ключ экрана (menu_key).
    """
    kind_code = MENU_ITEM_BY_KEY.get(menu_key)
    
    patched = []
        
    for row in kb_rows:
        new_row = []
        for btn in row:
            if isinstance(btn, InlineKeyboardButton) and getattr(btn, "url", None) == "https://example.com" and kind_code:
                urls = build_urls_for_item(user_id, kind_code[0], kind_code[1])
    
                label = (btn.text or "").lower()
                # выбор способа оплаты по тексту кнопки
                if "stars" in label or "⭐" in label:
                     new_row.append(InlineKeyboardButton(text=btn.text, url=urls["stars"]))
                elif "crypto" in label:
                     new_row.append(InlineKeyboardButton(text=btn.text, url=urls["cryptobot"]))
                else:
                     # всё карточное (Stripe/Fondy/Visa/Mastercard) — ведём на наш Fondy-роут
                    new_row.append(InlineKeyboardButton(text=btn.text, url=urls["fondy"]))
            else:
                new_row.append(btn)
        patched.append(new_row)
    return patched


# ——— ОПИСАНИЕ ВСЕХ МЕНЮ ———
MENUS = {
    # Главное меню
    CB_MAIN: {
        "text": (
            "👋 Привет!\n\n"
            "Представь, что твоя фотография оживает и превращается в трендовое видео для TikTok или Reels.\n\n"
            "📽 Наш бот сделает это за тебя:\n"
            "⤷ Загрузи фото и напиши пару слов\n"
            "⤷ Через пару минут получи стильное видео\n"
            "⤷ Делись им в соцсетях и собирай просмотры\n\n"
            "🔥 Попробуй всё без ограничений с тестовой подпиской на <b>3 дня за $1.</b>\n\n"
            "🆓 Или пригласи <b>друзей</b> и протестируй совершенно бесплатно!\n\n"
            "👉 Это дешевле чашки кофе, но может стать началом твоего нового контента!"
        ),
        "buttons": [
            [InlineKeyboardButton("🎞 Генерация видео", callback_data=CB_GENERATION),],
            [InlineKeyboardButton("🔥 Купить подписку",    callback_data=CB_SUB_PREMIUM),],
            [InlineKeyboardButton("👤 Профиль",          callback_data=CB_PROFILE),],
            [InlineKeyboardButton("🤑 Партнёрка",        callback_data=CB_PARTNER),],
        ],
    },

    # Меню «Генерация»
    CB_GENERATION: {
        "text": (
            f"🎞 <b>Генерация видео</b>\nСамые современные модели для создания реалистичных и креативных видео.\n\n"
            f"🎬 <b>Kling Standard:</b>\n\nБыстрая и доступная модель для базовой генерации видео. Подходит для тестов и простых идей.(стоимость <b>{COST_KLING_STD}</b> кредитов)\n\n"
            f"🎥 <b>Kling Pro:</b>\n\nУлучшенная версия с более высокой детализацией и качеством. Отличный баланс скорости и реализма.(стоимость <b>{COST_KLING_PRO}</b> кредитов)\n\n"
            f"🏆 <b>Kling Master:</b>\n\nМаксимальное качество и кинематографичность. Для тех, кто хочет получить лучшее видео из своих фото.(стоимость <b>{COST_KLING_MAST}</b> кредитов)\n\n"
            f"🔥 <b>Veo3:</b>\n\nМодель от Google для генерации видео с озвучкой по текстовому описанию. Создаёт яркие и креативные ролики без загрузки фото.(стоимость <b>{COST_VEO}</b> кредитов)\n\n"
            "Выберите модель:"
        ),
        # в render_menu мы подставим замок, если нет премиума
        "buttons": [
            [ InlineKeyboardButton("🎬 Kling Standard 🎬", callback_data=CB_GEN_KLING_STD) ],
            [ InlineKeyboardButton("🎥 Kling Pro 🎥",       callback_data=CB_GEN_KLING_PRO) ],
            [ InlineKeyboardButton("🏆 Kling Master 🏆",    callback_data=CB_GEN_KLING_MAST) ],
            [ InlineKeyboardButton("🔥 Veo3 со звуком 🔥",  callback_data=CB_GEN_VEO) ],
            [ InlineKeyboardButton("⬅️ Назад",              callback_data=CB_MAIN) ],
        ],
    },

    # Меню «Партнёрская программа»
    CB_PARTNER: {
        "text": (
            "🤑 <b>Партнёрская программа</b>\n\n"
            "Зарабатывай вместе с нами!\n\n"
            "📌 Условия:\n"
            "→ Снимай видео с помощью нашего бота и делись ими в соцсетях\n"
            "→ Добавляй в описание профиля свою реферальную ссылку\n"
            "→ За каждую оплату подписки по твоей ссылке ты получаешь <b>35%</b> от суммы\n\n"
            "Твоя персональная реферальная ссылка:\n"
            "https://t.me/{bot_username}?start={{user_id}}"
        ),
        "buttons": [
            [ InlineKeyboardButton("⬅️ Назад",              callback_data=CB_MAIN) ],
        ],
    },

    # Меню «Подписка Premium»
    CB_SUB_PREMIUM: {
        "text": (
            "🔥 <b>Подписка Premium</b>\n\n"
            "Получи полный доступ к возможностям бота:\n\n"
            "⤷ Доступ ко всем моделям генерации видео (Kling Standard, Pro, Master и Veo3)\n"
            "⤷ Повышенные лимиты на количество генераций\n"
            "⤷ Приоритетная очередь (твои видео создаются быстрее)\n"
            "⤷ Кинематографичное качество и расширенные настройки\n"
            "⤷ Поддержка популярных трендовых промптов\n\n"
            "🍓 Лимиты:\n"
            "→ Kling Standard: 120 генераций в год\n"
            "→ Kling Pro: 80 генераций в год\n"
            "→ Kling Master: 30 генераций в год\n"
            "→ Veo3: 18 генераций в год\n\n"
            "👉 Выбери тариф ниже:"
        ),
        "buttons": [
            [ InlineKeyboardButton("💰 3 дня | 1 $",      callback_data=CB_SUB_3D) ],
            [ InlineKeyboardButton("🔥 Месяц | 10 $",     callback_data=CB_SUB_MONTH) ],
            [ InlineKeyboardButton("💎 Год | 85 $", callback_data=CB_SUB_YEAR) ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_PROFILE) ],
        ],
    },

    # Меню «Кредиты для генерации»
    CB_BUY_CREDITS: {
        "text": "💳 <b>Пакеты кредитов</b>\n\nВыберите объём:",
        "buttons": [
            [ InlineKeyboardButton("💰 Standard | 15 $ | 1800 кредитов", callback_data=CB_CRED_STD) ],
            [ InlineKeyboardButton("🔥 Pro | 30 $ | 3 600 кредитов",      callback_data=CB_CRED_PRO) ],
            [ InlineKeyboardButton("💎 Max | 50 $ | 6 000 кредитов",      callback_data=CB_CRED_MAX) ],
            [ InlineKeyboardButton("⬅️ Назад",            callback_data=CB_PROFILE) ],
        ],
    },

    # Меню «Бесплатные генерации»
    CB_FREE_GEN: {
        "text": (
            "🆓 <b>Бонусная программа</b>\n\n"
            "Приглашай друзей и получай бонусы!\n\n"
            "📌 Условия:\n"
            "→ За каждого приглашённого друга ты получаешь 30 кредитов\n"
            "→ Приглашай до 10 друзей и получай до 3х бесплатных генераций\n\n"
            "Твоя реферальная ссылка:\n"
            "https://t.me/{bot_username}?start={{user_id}}"
        ),
        "buttons": [
            [ InlineKeyboardButton("⬅️ Назад", callback_data=CB_PROFILE) ],
        ],
    },

    # Оплаты: 3 дня / Месяц / Год
    CB_SUB_3D: {
        "text": (
            "💰 <b>3 дня подписка</b>\n\n"
            "Тестовая подписка в которой ты получишь 300 кредитов и возможность создать до 3х видео.\n\n"
            "Тестовую подписку можно купить только 1 раз.\n\n"
            "Кредиты можно докупить в любой момент.\n\n"
            "Пожалуйста, выбери метод оплаты:"
        ),
        "buttons": [
            [ InlineKeyboardButton("TG Stars | 150 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("AppPay/G-Pay | 1 $",       url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 1 $",       url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",            callback_data=CB_SUB_PREMIUM) ],
        ],
    },
    CB_SUB_MONTH: {
        "text": (
            "🔥 <b>Месячная подписка</b>\n\n"
            "За оплату месячной подписки ты получишь 1 000 кредитов в месяц и возможность создать до 10 видео.\n\n"
            "Кредиты можно докупить в любой момент.\n\n"
            "Пожалуйста, выбери метод оплаты:"
        ),
        "buttons": [
            [ InlineKeyboardButton("TG Stars | 1000 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("AppPay/G-Pay | 10 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 10 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",            callback_data=CB_SUB_PREMIUM) ],
        ],
    },
    CB_SUB_YEAR: {
        "text": (
            "💎 <b>Годовая подписка</b>\n\n"
            "За оплату годовой подписки ты получишь 12 000 кредитов в год и возможность создать до 120 видео.\n\n"
            "Кредиты можно докупить в любой момент.\n\n"
            "Пожалуйста, выбери метод оплаты:"
        ),
        "buttons": [
            [ InlineKeyboardButton("TG Stars | 8500 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("AppPay/G-Pay | 85 $", url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 85 $", url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_SUB_PREMIUM) ],
        ],
    },

    # Пакеты кредитов
    CB_CRED_STD: {
        "text": (
            "💰 <b>Пакет Standard</b>\n\n"
            "1800 кредидов на генерацию видео, создание до 18 видео.\n\n"
            "Выберите метод оплаты:"
        ),
        "buttons": [
            [ InlineKeyboardButton("TG Stars | 1500 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("AppPay/G-Pay | 15 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 15 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_BUY_CREDITS) ],
        ],
    },
    CB_CRED_PRO: {
        "text": (
            "🔥 <b>Пакет Pro</b>\n\n"
            "3600 кредидов на генерацию видео, создание до 36 видео.\n\n"
            "Выберите метод оплаты:"
        ),
        "buttons": [
            [ InlineKeyboardButton("TG Stars | 3000 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("AppPay/G-Pay | 30 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 30 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_BUY_CREDITS) ],
        ],
    },
    CB_CRED_MAX: {
        "text": (
            "💎 <b>Пакет Max</b>\n\n"
            "6000 кредидов на генерацию видео, создание до 60 видео.\n\n"
            "Выберите метод оплаты:"
        ),
        "buttons": [
            [ InlineKeyboardButton("TG Stars | 5000 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("AppPay/G-Pay | 50 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 50 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_BUY_CREDITS) ],
        ],
    },
}

# Меню «Профиль»
def get_profile_text(user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    
    with SessionLocal() as db:
        user = get_user(db, user_id)

        # ⬇️ одно число из БД: сколько людей указали этого юзера реферером
        invited_total = db.query(UserModel.user_id).filter(UserModel.referrer_id == user_id).count()
    
        c = user.credits + user.bonus_credits
        lines = [
            "👤 <b>Ваш профиль</b>\n",
            f"Кредитов осталось: {c}\n",
            "Генераций осталось:",
            f"→ Kling Standard: {c // COST_KLING_STD}",
            f"→ Kling Pro:      {c // COST_KLING_PRO}",
            f"→ Kling Master:   {c // COST_KLING_MAST}",
            f"→ Veo3:           {c // COST_VEO}\n",
            f"Приглашённых друзей: {user.invited_count}/{MAX_INVITES}",
            f"Бонусных кредитов: {user.bonus_credits}\n",
            f"Всего приглашенных пользователей: {invited_total}\n",
            f"Подписка Premium: {'Активна ✅' if user.premium else 'Не активна ❌'}"
        ]
        if user.premium and user.premium_until:
              lines.append(f"∙ Срок истечения: {user.premium_until.strftime('%Y-%m-%d')}")
        lines.append("\n💡 Если генерации закончились — их всегда можно докупить!")
        
        buttons = [
            ("🔥 Купить подписку", CB_SUB_PREMIUM),
            ("💳 Купить кредиты", CB_BUY_CREDITS),
            ("🆓 Бесплатные генерации", CB_FREE_GEN),
            ("⬅️ Назад", CB_MAIN),
        ]
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=cb)] for t, cb in buttons])
        
        return "\n".join(lines), keyboard


# ——— ФУНКЦИЯ ОТРИСОВКИ МЕНЮ ———
def render_menu(menu_key: str, user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    """
    Возвращает (text, InlineKeyboardMarkup) для указанного меню.
    """
    if menu_key == CB_PROFILE:
        return get_profile_text(user_id)

    m = MENUS[menu_key]

    buttons = m["buttons"]
    markup = InlineKeyboardMarkup(buttons)

    patched = _patch_payment_urls(user_id, markup.inline_keyboard, menu_key)
    markup = InlineKeyboardMarkup(patched)

    # Подставляем user_id и имя бота в текст
    text = m["text"].replace("{{user_id}}", str(user_id))
    text = text.replace("{bot_username}", config.bot.username)

    return text, markup


