# menu.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config
from config import ADMIN_IDS
from config import COST_KLING_STD, COST_KLING_PRO, COST_KLING_MAST, COST_VEO, MAX_INVITES
from typing import Tuple
from db     import SessionLocal, get_user

# ——— CALLBACK_DATA КОНСТАНТЫ ———
CB_MAIN            = "menu:main"
CB_GENERATION      = "menu:generation"
CB_PROFILE         = "menu:profile"
# CB_INFO            = "menu:info"
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

# ——— ВСПОМОГАТЕЛЬ —————
def _maybe_lock(text: str, has_premium: bool) -> str:
    """Если нет премиум-подписки — добавляем эмоджи замка спереди."""
    return ("🔒 " + text) if not has_premium else text

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
            "🆓 Или пригласи <b>5 друзей</b> и протестируй совершенно бесплатно!\n\n"
            "👉 Это дешевле чашки кофе, но может стать началом твоего нового контента!"
        ),
        "buttons": [
            [InlineKeyboardButton("🎞 Генерация видео", callback_data=CB_GENERATION),],
            [InlineKeyboardButton("🔥 Купить подписку",    callback_data=CB_SUB_PREMIUM),],
            [InlineKeyboardButton("👤 Профиль",          callback_data=CB_PROFILE),],
            # [InlineKeyboardButton("ℹ️ О моделях",        callback_data=CB_INFO),],
            [InlineKeyboardButton("🤑 Партнёрка",        callback_data=CB_PARTNER),],
        ],
    },

    # Меню «Генерация»
    CB_GENERATION: {
        "text": (
            "🎞 <b>Генерация видео</b>\nСамые современные модели для создания реалистичных и креативных видео.\n\n"
            "🎬 <b>Kling Standar:</b>\n\nБыстрая и доступная модель для базовой генерации видео. Подходит для тестов и простых идей.\n\n"
            "🎥 <b>Kling Pro:</b>\n\nУлучшенная версия с более высокой детализацией и качеством. Отличный баланс скорости и реализма.\n\n"
            "🏆 <b>Kling Master:</b>\n\nМаксимальное качество и кинематографичность. Для тех, кто хочет получить лучшее видео из своих фото.\n\n"
            "🔥 <b>Veo3:</b>\n\nМодель от Google для генерации видео с озвучкой по текстовому описанию. Создаёт яркие и креативные ролики без загрузки фото.\n\n"
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

    # # Меню «О генеративных моделях»
    # CB_INFO: {
    #     "text": "ℹ️ <b>О генеративных моделях</b>\n\nКраткое описание доступных режимов:",
    #     "buttons": [
    #         [ InlineKeyboardButton("🎬 Kling Standard 🎬", callback_data=CB_GEN_KLING_STD) ],
    #         [ InlineKeyboardButton("🎥 Kling Pro 🎥",       callback_data=CB_GEN_KLING_PRO) ],
    #         [ InlineKeyboardButton("🏆 Kling Master 🏆",    callback_data=CB_GEN_KLING_MAST) ],
    #         [ InlineKeyboardButton("🔥 Veo3 со звуком 🔥",  callback_data=CB_GEN_VEO) ],
    #         [ InlineKeyboardButton("⬅️ Назад",              callback_data=CB_MAIN) ],
    #     ],
    # },

    # Меню «Партнёрская программа»
    CB_PARTNER: {
        "text": (
            "🤑 <b>Партнёрская программа</b>\n\n"
            "Зарабатывайте вместе с нами!\n\n"
            "📌 Условия:\n"
            "→ Снимайте видео с помощью нашего бота и делитесь ими в соцсетях\n"
            "→ Добавляйте в описание свою реферальную ссылку\n"
            "→ За каждую оплату подписки по вашей ссылке вы получаете <b>50%</b> от суммы\n\n"
            "Ваша персональная реферальная ссылка:\n"
            f"`https://example.com/ref={{{{user_id}}}}`"
        ),
        "buttons": [
            [ InlineKeyboardButton("📋 Скопировать ссылку", callback_data=CB_PARTNER + ":copy") ],
            [ InlineKeyboardButton("⬅️ Назад",              callback_data=CB_MAIN) ],
        ],
    },

    # Меню «Подписка Premium»
    CB_SUB_PREMIUM: {
        "text": (
            "🔥 <b>Подписка Premium</b>\n\n"
            "Получите полный доступ к возможностям бота:\n\n"
            "⤷ Доступ ко всем моделям генерации видео (Kling Standard, Pro, Master и Veo3)\n"
            "⤷ Повышенные лимиты на количество генераций\n"
            "⤷ Приоритетная очередь (ваши видео создаются быстрее)\n"
            "⤷ Кинематографичное качество и расширенные настройки\n"
            "⤷ Поддержка популярных трендовых промптов\n\n"
            "🍓 Лимиты:\n"
            "→ Kling Standard: 120 генераций в год\n"
            "→ Kling Pro: 80 генераций в год\n"
            "→ Kling Master: 40 генераций в год\n"
            "→ Veo3: 20 генераций в год\n\n"
            "👉 Выберите тариф ниже:"
        ),
        "buttons": [
            [ InlineKeyboardButton("💰 3 дня | 1 $",      callback_data=CB_SUB_3D) ],
            [ InlineKeyboardButton("🔥 Месяц | 10 $",     callback_data=CB_SUB_MONTH) ],
            [ InlineKeyboardButton("💎 Год | 65 $", callback_data=CB_SUB_YEAR) ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_PROFILE) ],
        ],
    },

    # Меню «Кредиты для генерации»
    CB_BUY_CREDITS: {
        "text": "💳 <b>Пакеты кредитов</b>\n\nВыберите объём:",
        "buttons": [
            [ InlineKeyboardButton("💰 Standart | 10 $", callback_data=CB_CRED_STD) ],
            [ InlineKeyboardButton("🔥 Pro | 30 $",      callback_data=CB_CRED_PRO) ],
            [ InlineKeyboardButton("💎 Max | 50 $",      callback_data=CB_CRED_MAX) ],
            [ InlineKeyboardButton("⬅️ Назад",            callback_data=CB_PROFILE) ],
        ],
    },

    # Меню «Бесплатные генерации»
    CB_FREE_GEN: {
        "text": (
            "🆓 <b>Бонусная программа</b>\n\n"
            "Приглашайте друзей и получайте бонусы!\n\n"
            "📌 Условия:\n"
            "→ За каждых 5 приглашённых друзей вы получаете 1 бесплатную генерацию видео\n"
            "→ Максимум можно пригласить 10 друзей (и получить до 2 бесплатных генераций)\n\n"
            "Ваша реферальная ссылка:\n"
            f"`https://example.com/free={{{{user_id}}}}`"
        ),
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
            [ InlineKeyboardButton("TG Stars | 125 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe | 1 $",       url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 1 $",       url="https://example.com") ],
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
            [ InlineKeyboardButton("TG Stars | 1000 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe | 10 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 10 $",      url="https://example.com") ],
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
            [ InlineKeyboardButton("TG Stars | 3500 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe | 65 $", url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 65 $", url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_SUB_PREMIUM) ],
        ],
    },

    # Пакеты кредитов
    CB_CRED_STD: {
        "text": "💰 <b>Пакет Standart</b>\n\nВыберите метод оплаты:",
        "buttons": [
            [ InlineKeyboardButton("TG Stars | 1000 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe | 10 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 10 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_BUY_CREDITS) ],
        ],
    },
    CB_CRED_PRO: {
        "text": "🔥 <b>Пакет Pro</b>\n\nВыберите метод оплаты:",
        "buttons": [
            [ InlineKeyboardButton("TG Stars | 2500 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe | 30 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 30 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_BUY_CREDITS) ],
        ],
    },
    CB_CRED_MAX: {
        "text": "💎 <b>Пакет Max</b>\n\nВыберите метод оплаты:",
        "buttons": [
            [ InlineKeyboardButton("TG Stars | 3500 ⭐", url="https://example.com") ],
            [ InlineKeyboardButton("Stripe | 50 $",      url="https://example.com") ],
            [ InlineKeyboardButton("Crypto | 50 $",      url="https://example.com") ],
            [ InlineKeyboardButton("⬅️ Назад",             callback_data=CB_BUY_CREDITS) ],
        ],
    },
}

# Меню «Профиль»
def get_profile_text(user_id: int) -> Tuple[str, InlineKeyboardMarkup]:
    
    with SessionLocal() as db:
        user = get_user(db, user_id)
    
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
            f"Бесплатных генераций (бонус): {user.bonus_credits}\n",
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
def render_menu(menu_key: str, user_id: int) -> (str, InlineKeyboardMarkup):
    """
    Возвращает (text, InlineKeyboardMarkup) для указанного меню.
    Подставляет замок '🔒' перед пунктами Генерации,
    если у пользователя нет премиум-подписки.
    """
    if menu_key == CB_PROFILE:
        # get_profile_text возвращает (text, InlineKeyboardMarkup)
        return get_profile_text(user_id)
        
    m = MENUS[menu_key]
    has_premium = (user_id in ADMIN_IDS) or (config.user_limits.get(user_id, 0) > 0)  # <- пример проверки
    buttons = []

    # если это меню Генерации — ставим замок
    if menu_key == CB_GENERATION:
        for row in m["buttons"]:
            orig_text = row[0].text
            cb        = row[0].callback_data
            if cb == CB_MAIN:
                btn_text = orig_text
            else:
                btn_text = _maybe_lock(orig_text, has_premium)
            buttons.append([InlineKeyboardButton(btn_text, callback_data=cb)])
    else:
        buttons = m["buttons"]

    markup = InlineKeyboardMarkup(buttons)
    # заменяем {{user_id}} в тексте на реальный ID
    text = m["text"].replace("{{user_id}}", str(user_id))
    return text, markup

