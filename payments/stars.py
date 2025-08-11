import logging
from decimal import Decimal
from telegram import LabeledPrice
from telegram.utils.request import Request
from config import bot
from services.billing import compute_price
from db_utils import create_payment
from models import PaymentStatus

logger = logging.getLogger(__name__)

def build_stars_invoice_link(user_id: int, item_kind: str, item_code: str) -> str:
    """
    Создаём invoice-link через Bot API для валюты XTR (Stars).
    Для Stars можно использовать createInvoiceLink с currency='XTR'.
    """
    usd, stars = compute_price(item_kind, item_code)
    title = f"{'Subscription' if item_kind=='sub' else 'Credits'}: {item_code}"
    description = f"Payment via Telegram Stars ({stars}⭐)"

    payload = f"{user_id}:{item_kind}:{item_code}:stars"
    prices = [LabeledPrice(label=title, amount=stars)]  # amount — в звездах для XTR

    link = bot.create_invoice_link(
        title=title,
        description=description,
        payload=payload,
        provider_token="",        # для XTR провайдер не нужен
        currency="XTR",
        prices=prices,
    )

    # предварительно фиксируем платеж со статусом 'created'
    create_payment(
        user_id=user_id,
        method="stars",
        item_kind=item_kind,
        item_code=item_code,
        amount_usd=None,
        amount_stars=stars,
        external_id=None,
        payload=payload,
        status=PaymentStatus.created
    )
    return link

