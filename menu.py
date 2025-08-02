# menu.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config
from config import ADMIN_IDS

# ——— CALLBACK_DATA КОНСТАНТЫ ———
CB_MAIN            = "menu:main"
CB_GENERATION      = "menu:generation"
CB_PROFILE         = "menu:profile"
CB_INFO            = "menu:info"
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

# ——— ВСПОМОГАТЕЛЬ —————
def _maybe_lock(text: str, has_premium: bool) -> str:
    """Если нет премиум-подписки — добавляем эмоджи замка спереди."""
    return ("🔒 " + text) if not has_premium else text

# ——— ОПИСАНИЕ ВСЕХ МЕНЮ ———
MENUS = {
    # Главное меню
    CB_MAIN: {
        "text": "🏠 <b>Главное меню</b>\n\nВыберите раздел:",
        "buttons": [
            [InlineKeyboardButton("🎞 Генерация видео", callback_data=CB_GENERATION),],
            [InlineKeyboardButton("🔥 Купить подписку",    callback_data=CB_SUB_PREMIUM),],
            [InlineKeyboardButton("👤 Профиль",          callback_data=CB_PROFILE),],
            [InlineKeyboardButton("ℹ️ О моделях",        callback_data=CB_INFO),],
            [InlineKeyboardButton("🤑 Партнёрка",        callback_data=CB_PARTNER),],
        ],
    },

    # Меню «Генерация»
    CB_GENERATION: {
        "text": "🎞 <b>Генерация видео</b>\n\nВыберите модель:",
        # в render_menu мы подставим замок, если нет премиума
        "buttons": [
            [ InlineKeyboardButton("🎬 Kling Standard 🎬", callback_data=CB_GEN_KLING_STD) ],
            [ InlineKeyboardButton("🎥 Kling Pro 🎥",       callback_data=CB_GEN_KLING_PRO) ],
            [ InlineKeyboardButton("🏆 Kling Master 🏆",    callback_data=CB_GEN_KLING_MAST) ],
            [ InlineKeyboardButton("🔥 Veo3 со звуком 🔥",  callback_data=CB_GEN_VEO) ],
            [ InlineKeyboardButton("⬅️ Назад",              callback_data=CB_MAIN) ],
        ],
    },

    # Меню «Профиль»
    CB_PROFILE: {
        "text": "👤 <b>Ваш профиль</b>\n\nУправление подпиской и кредитами:",
        "buttons": [
            [ InlineKeyboardButton("🔥 Купить подписку",    callback_data=CB_SUB_PREMIUM) ],
            [ InlineKeyboardButton("💳 Купить кредиты",     callback_data=CB_BUY_CREDITS) ],
            [ InlineKeyboardButton("🆓 Бесплатные генерации", callback_data=CB_FREE_GEN) ],
            [ InlineKeyboardButton("⬅️ Назад",               callback_data=CB_MAIN) ],
        ],
    },

    # Меню «О генеративных моделях»
    CB_INFO: {
        "text": "ℹ️ <b>О генеративных моделях</b>\n\nКраткое описание доступных режимов:",
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
        "text": "🤑 <b>Партнёрская программа</b>\n\nВаша реферальная ссылка:\n"
                f"`https://example.com/ref={{{{user_id}}}}`",
        "buttons": [
            [ InlineKeyboardButton("📋 Скопировать ссылку", callback_data=CB_PARTNER + ":copy") ],
            [ InlineKeyboardButton("⬅️ Назад",              callback_data=CB_MAIN) ],
        ],
    },

    # Меню «Подписка Premium»
    CB_SUB_PREMIUM: {
        "text": "🔥 <b>Подписка Premium</b>\n\nВыберите тариф:",
        "buttons": [
            [ InlineKeyboardButton("💰 3 дня — 1 $",      callback_data=CB_SUB_3D) ],
            [ InlineKeyboardButton("🔥 Месяц — 10 $",     callback_data=CB_SUB_MONTH) ],
            [ InlineKeyboardButton("💎 Год — 120 $ 65 $", callback_data=CB_SUB_YEAR) ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_PROFILE) ],
        ],
    },

    # Меню «Кредиты для генерации»
    CB_BUY_CREDITS: {
        "text": "💳 <b>Пакеты кредитов</b>\n\nВыберите объём:",
        "buttons": [
            [ InlineKeyboardButton("💰 Standart — 10 $", callback_data=CB_CRED_STD) ],
            [ InlineKeyboardButton("🔥 Pro — 30 $",      callback_data=CB_CRED_PRO) ],
            [ InlineKeyboardButton("💎 Max — 50 $",      callback_data=CB_CRED_MAX) ],
            [ InlineKeyboardButton("⬅️ Назад",            callback_data=CB_PROFILE) ],
        ],
    },

    # Меню «Бесплатные генерации»
    CB_FREE_GEN: {
        "text": "🆓 <b>Бесплатные генерации</b>\n\nВаша реферальная ссылка:\n"
                f"`https://example.com/free={{{{user_id}}}}`",
        "buttons": [
            [ InlineKeyboardButton("⬅️ Назад", callback_data=CB_PROFILE) ],
        ],
    },

    # Оплаты: 3 дня / Месяц / Год
    CB_SUB_3D: {
        "text": (
            "💰 <b>3 дня подписка</b>\n\n"
            "Пожалуйста, выберите метод оплаты:\n\n"
            "⚠️ Переходя на оплату вы соглашаетесь с регламентом рекуррентных платежей."
        ),
        "buttons": [
            [ InlineKeyboardButton("TG Stars — 150 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe — 1 $",       url="https://example.com") ],
            [ InlineKeyboardButton("Crypto — 1 $",       url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",            callback_data=CB_SUB_PREMIUM) ],
        ],
    },
    CB_SUB_MONTH: {
        "text": (
            "🔥 <b>Месячная подписка</b>\n\n"
            "Пожалуйста, выберите метод оплаты:\n\n"
            "⚠️ Переходя на оплату вы соглашаетесь с регламентом рекуррентных платежей."
        ),
        "buttons": [
            [ InlineKeyboardButton("TG Stars — 1000 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe — 10 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto — 10 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",            callback_data=CB_SUB_PREMIUM) ],
        ],
    },
    CB_SUB_YEAR: {
        "text": (
            "💎 <b>Годовая подписка</b>\n\n"
            "Пожалуйста, выберите метод оплаты:\n\n"
            "⚠️ Переходя на оплату вы соглашаетесь с регламентом рекуррентных платежей."
        ),
        "buttons": [
            [ InlineKeyboardButton("TG Stars — 3500 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe — 120 $ 65 $", url="https://example.com") ],
            [ InlineKeyboardButton("Crypto — 120 $ 65 $", url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_SUB_PREMIUM) ],
        ],
    },

    # Пакеты кредитов
    CB_CRED_STD: {
        "text": "💰 <b>Пакет Standart</b>\n\nВыберите метод оплаты:",
        "buttons": [
            [ InlineKeyboardButton("TG Stars — 1000 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe — 10 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto — 10 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_BUY_CREDITS) ],
        ],
    },
    CB_CRED_PRO: {
        "text": "🔥 <b>Пакет Pro</b>\n\nВыберите метод оплаты:",
        "buttons": [
            [ InlineKeyboardButton("TG Stars — 2500 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe — 30 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto — 30 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_BUY_CREDITS) ],
        ],
    },
    CB_CRED_MAX: {
        "text": "💎 <b>Пакет Max</b>\n\nВыберите метод оплаты:",
        "buttons": [
            [ InlineKeyboardButton("TG Stars — 3500 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe — 50 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto — 50 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_BUY_CREDITS) ],
        ],
    },
}


# ——— ФУНКЦИЯ ОТРИСОВКИ МЕНЮ ———
def render_menu(menu_key: str, user_id: int) -> (str, InlineKeyboardMarkup):
    """
    Возвращает (text, InlineKeyboardMarkup) для указанного меню.
    Подставляет замок '🔒' перед пунктами Генерации,
    если у пользователя нет премиум-подписки.
    """
    m = MENUS[menu_key]
    has_premium = (user_id in ADMIN_IDS) or (config.user_limits.get(user_id, 0) > 0)  # <- пример проверки
    buttons = []

    # если это меню Генерации — ставим замок
    if menu_key == CB_GENERATION:
        for row in m["buttons"]:
            text = row[0].text
            cb   = row[0].callback_data
            buttons.append([
                InlineKeyboardButton(
                    _maybe_lock(text, has_premium),
                    callback_data=cb
                )
            ])
    else:
        buttons = m["buttons"]

    markup = InlineKeyboardMarkup(buttons)
    # заменяем {{user_id}} в тексте на реальный ID
    text = m["text"].replace("{{user_id}}", str(user_id))
    return text, markup

