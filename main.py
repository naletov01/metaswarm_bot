# main.py 

import logging, json, os
from anyio import to_thread
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse

# ——— Настройка логирования ———
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
# Сделаем телеграм-пакеты тише, если шумят:
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.INFO)

from telegram import Update, BotCommand
from sqlalchemy.orm import Session
from db import engine, Base, get_db, SessionLocal
import config
import handlers
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler,
    Filters, CallbackContext, CallbackQueryHandler,
    PreCheckoutQueryHandler
    )
from handlers import (
    start, image_upload_handler, text_handler, menu_callback, 
    on_check_sub, choose_model, profile, partner, handle_successful_payment,
    precheckout_ok
    )
from models import Payment, PaymentStatus
from services.billing import finalize_success, compute_price
from payments.fondy import _fondy_signature

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
log_fondy = logging.getLogger("pay.fondy")
log_crypto = logging.getLogger("pay.cryptobot")

# подтягиваем Bot и путь вебхука из config
bot = config.bot
WEBHOOK_PATH = config.WEBHOOK_PATH
WEBHOOK_URL = config.WEBHOOK_URL

app = FastAPI()


@app.on_event("startup")
async def startup():
    # 1) Инициализация БД (idempotent)
    try:
        await to_thread.run_sync(Base.metadata.create_all, engine)
        logger.info("DB init: OK")
    except Exception:
        logger.exception("DB init failed")
        raise
    # 2) Выставление вебхука
    try:
        # аккуратно склеиваем базовый URL и путь
        base = config.WEBHOOK_URL.rstrip("/")
        path = WEBHOOK_PATH if WEBHOOK_PATH.startswith("/") else "/" + WEBHOOK_PATH
        url = base + path

        ok = await to_thread.run_sync(bot.set_webhook, url,)
        
        if not ok:
            logger.warning("Webhook set failed for %s", url)
        else:
            info = await to_thread.run_sync(bot.get_webhook_info)
            logger.info("Webhook set: %s (pending_update_count=%s)", info.url, getattr(info, "pending_update_count", None))
    except Exception:
        logger.exception("Webhook setup failed")
        raise

# # main.py (startup)
# @app.on_event("startup")
# def startup():
#     Base.metadata.create_all(bind=engine)
#     from db import ensure_bigint_ids
#     try:
#         ensure_bigint_ids()
#     except Exception:
#         logger.exception("ensure_bigint_ids failed")  # не падаем на старте


dp = Dispatcher(bot=bot, update_queue=None, use_context=True)

bot.set_my_commands([
    BotCommand("start",        "🏠 Главное меню"),
    BotCommand("choose_model", "🎞 Генерация видео"),
    BotCommand("profile",      "👤 Профиль"),
    BotCommand("partner",      "🤑 Партнёрская программа"),
])

# ——— Регистрация хендлеров ———
dp.add_handler(CommandHandler("start", start, pass_args=True))
dp.add_handler(CommandHandler("choose_model", choose_model))
dp.add_handler(CommandHandler("profile",      profile))
dp.add_handler(CommandHandler("partner",      partner))
dp.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^(menu:|gen:)"))
dp.add_handler(CallbackQueryHandler(on_check_sub, pattern="^check_sub$"))

img_filter = Filters.photo | (Filters.document & Filters.document.mime_type("image/*"))
dp.add_handler(MessageHandler(img_filter, image_upload_handler))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

dp.add_handler(PreCheckoutQueryHandler(precheckout_ok))
dp.add_handler(MessageHandler(Filters.successful_payment, handle_successful_payment))


def error_handler(update, context):
    logger.exception("Error in handler", exc_info=context.error)
dp.add_error_handler(error_handler)


# ——— Webhook endpoint ———
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request, db=Depends(get_db)):
    data = await request.json()
    update = Update.de_json(data, bot)
    await to_thread.run_sync(dp.process_update, update)
    return {"ok": True}


@app.get("/")
@app.head("/")
def root():
    return {"status": "Bot is running"}


@app.get("/pay/fondy")
async def pay_fondy(order_id: str, amount: int, item: str, currency: str | None = None):
    currency = currency or config.FONDY_CURRENCY
    log_fondy.info("[REDIRECT] order_id=%s amount=%s currency=%s item=%s", order_id, amount, currency, item)

    # HTML auto-submit на Fondy
    try:
        sig = _fondy_signature({
            'merchant_id': int(config.FONDY_MERCHANT_ID),
            'order_id': order_id,
            'amount': amount,
            'currency': currency
        })
    except Exception:
        log_fondy.exception("[REDIRECT][SIGN_ERROR] order_id=%s", order_id)
        raise HTTPException(500, "signature failed")

    html = f"""
    <html><body onload="document.forms[0].submit()">
      <form action="https://pay.fondy.eu/api/checkout/redirect/" method="POST">
        <input type="hidden" name="merchant_id" value="{config.FONDY_MERCHANT_ID}">
        <input type="hidden" name="order_id" value="{order_id}">
        <input type="hidden" name="amount" value="{amount}">
        <input type="hidden" name="currency" value="{currency}">
        <input type="hidden" name="order_desc" value="{item}">
        <input type="hidden" name="server_callback_url" value="{config.WEBHOOK_URL}/webhook/fondy">
        <input type="hidden" name="response_url" value="{config.WEBHOOK_URL}/payment/thanks">
        <input type="hidden" name="signature" value="{sig}">
      </form>
    </body></html>
    """
    return HTMLResponse(html)


@app.post("/webhook/fondy")
async def webhook_fondy(request: Request):
    data = await request.form()
    fields = dict(data)

    # Логируем входящие поля компактно
    try:
        log_fondy.info("[WEBHOOK][RAW] %s", {k: (str(v)[:200]) for k, v in fields.items()})
    except Exception:
        log_fondy.warning("[WEBHOOK][RAW_LOG_FAIL]")

    # Проверка подписи
    try:
        sign = fields.get("signature")
        expected = _fondy_signature({
            "merchant_id": int(fields["merchant_id"]),
            "order_id": fields["order_id"],
            "amount": int(fields["amount"]),
            "currency": fields["currency"],
        })
    except Exception:
        log_fondy.exception("[WEBHOOK][BAD_FIELDS]")
        raise HTTPException(400, "Bad fields")

    if sign != expected:
        log_fondy.warning("[WEBHOOK][BAD_SIGNATURE] got=%s expected=%s", sign, expected)
        raise HTTPException(400, "Bad signature")
    else:
        log_fondy.info("[WEBHOOK][SIGNATURE_OK] order_id=%s", fields.get("order_id"))

    order_id = fields["order_id"]
    status = fields.get("order_status")

    with SessionLocal() as db:
        p = db.query(Payment).filter(Payment.external_id == order_id).first()
        if not p:
            log_fondy.error("[WEBHOOK][NOT_FOUND] order_id=%s", order_id)
            return JSONResponse({"ok": True})

        if p.status == PaymentStatus.success:
            log_fondy.info("[WEBHOOK][IDEMPOTENT] id=%s order_id=%s", p.id, order_id)
            return JSONResponse({"ok": True})

        if status == "approved":
            log_fondy.info("[WEBHOOK][APPROVED] id=%s uid=%s", p.id, p.user_id)
            if finalize_success(db, p):
                log_fondy.info("[FINALIZE][SUCCESS] id=%s uid=%s", p.id, p.user_id)
                # ВАЖНО: передаём метод, а не объект
                from handlers import send_safe
                send_safe(bot.send_message, p.user_id, "✅ Оплата через Fondy прошла успешно. Начисления выполнены.")
            else:
                log_fondy.info("[FINALIZE][FAILED] id=%s uid=%s", p.id, p.user_id)
                from handlers import send_safe
                send_safe(bot.send_message, p.user_id, "❌ Платёж отклонён.")
            return JSONResponse({"ok": True})
        else:
            from db_utils import mark_payment_failed
            mark_payment_failed(db, p.id, f"Fondy status={status}")
            log_fondy.info("[WEBHOOK][DECLINED] id=%s status=%s", p.id, status)
            return JSONResponse({"ok": True})


@app.post("/webhook/cryptobot")
async def webhook_cryptobot(request: Request):
    try:
        body = await request.json()
    except Exception:
        log_crypto.exception("[WEBHOOK][BAD_JSON]")
        return JSONResponse({"ok": True})

    # Компактный лог входящих данных
    try:
        log_crypto.info("[WEBHOOK][RAW] %s", {k: (str(v)[:200]) for k, v in body.items()})
    except Exception:
        log_crypto.warning("[WEBHOOK][RAW_LOG_FAIL]")

    event = body.get("update_type")
    if event != "invoice_paid":
        log_crypto.info("[WEBHOOK][SKIP] update_type=%s", event)
        return JSONResponse({"ok": True})

    inv = body.get("invoice_paid") or {}
    invoice_id = str(inv.get("invoice_id"))

    with SessionLocal() as db:
        p = db.query(Payment).filter(Payment.external_id == invoice_id).first()
        if not p:
            log_crypto.error("[WEBHOOK][NOT_FOUND] invoice_id=%s", invoice_id)
            return JSONResponse({"ok": True})

        if p.status == PaymentStatus.success:
            log_crypto.info("[WEBHOOK][IDEMPOTENT] id=%s invoice_id=%s", p.id, invoice_id)
            return JSONResponse({"ok": True})

        log_crypto.info("[WEBHOOK][PAID] id=%s uid=%s invoice_id=%s", p.id, p.user_id, invoice_id)
        if finalize_success(db, p):
            log_crypto.info("[FINALIZE][SUCCESS] id=%s uid=%s", p.id, p.user_id)
            from handlers import send_safe
            send_safe(bot.send_message, p.user_id, "✅ Оплата через CryptoBot прошла успешно. Начисления выполнены.")
        else:
            log_crypto.info("[FINALIZE][FAILED] id=%s uid=%s", p.id, p.user_id)
            from handlers import send_safe
            send_safe(bot.send_message, p.user_id, "❌ Платёж отклонён.")
    return JSONResponse({"ok": True})




