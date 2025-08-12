import logging, uuid, hashlib, base64, json
from config import FONDY_MERCHANT_ID, FONDY_MERCHANT_SECRET, FONDY_CURRENCY, WEBHOOK_URL
from services.billing import compute_price
from db_utils import create_payment
from models import PaymentStatus

logger = logging.getLogger(__name__)

FONDY_GATEWAY = "https://pay.fondy.eu/api/checkout/url/"

def _fondy_signature(data: dict) -> str:
    # RFC: подпись fondy — sha1(merchant_secret|ordered_fields|)
    # Для простоты: используем их "order_id|merchant_id|amount|currency"
    signature_str = "|".join([
        FONDY_MERCHANT_SECRET,
        str(data["order_id"]),
        str(data["merchant_id"]),
        str(data["amount"]),
        data["currency"]
    ])
    return hashlib.sha1(signature_str.encode()).hexdigest()

def build_fondy_link(user_id: int, item_kind: str, item_code: str):
    usd, _ = compute_price(item_kind, item_code)
    order_id = f"{user_id}-{item_kind}-{item_code}-{uuid.uuid4().hex[:8]}"
    amount_cents = int(float(usd) * 100)

    logger.info("[CREATE] uid=%s kind=%s code=%s usd=%.2f amount_cents=%s order_id=%s",
                user_id, item_kind, item_code, float(usd), amount_cents, order_id)

    payload = {
        "merchant_id": int(FONDY_MERCHANT_ID),
        "order_id": order_id,
        "amount": amount_cents,
        "currency": FONDY_CURRENCY,
        "order_desc": f"{item_kind}:{item_code}",
        "server_callback_url": f"{WEBHOOK_URL}/webhook/fondy",
        "response_url": f"{WEBHOOK_URL}/payment/thanks",  # опционально
    }
    payload["signature"] = _fondy_signature(payload)

    # создаём запись платежа (draft)
    create_payment(
        user_id=user_id,
        method="fondy",
        item_kind=item_kind,
        item_code=item_code,
        amount_usd=usd,
        amount_stars=None,
        external_id=order_id,
        payload=json.dumps({"gateway":"fondy"}),
        status=PaymentStatus.created
    )

    # Возвращаем ссылку на шлюз (redirect POST/GET).
    # Удобно: вернём наш REST-роут /pay/fondy, который сделает 307 POST к FONDY
    url = f"{WEBHOOK_URL}/pay/fondy?order_id={order_id}&amount={amount_cents}&item={item_kind}:{item_code}"
    logger.info("[LINK] uid=%s order_id=%s url=%s", user_id, order_id, url)
    return url

