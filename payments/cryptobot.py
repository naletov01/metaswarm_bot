import logging, json, requests
from config import CRYPTOBOT_TOKEN, CRYPTOBOT_CURRENCY, WEBHOOK_URL
from services.billing import compute_price
from db_utils import create_payment
from models import PaymentStatus

logger = logging.getLogger(__name__)
API = "https://pay.crypt.bot/api"

def build_cryptobot_link(user_id: int, item_kind: str, item_code: str) -> str:
    usd, _ = compute_price(item_kind, item_code)
    amount = float(usd)

    payload = {
        "amount": amount,
        "currency_type": "fiat",
        "fiat": "USD",
        "asset": CRYPTOBOT_CURRENCY,
        "description": f"{item_kind}:{item_code}",
        "paid_btn_name": "callback",
        "paid_btn_url": f"{WEBHOOK_URL}/payment/thanks",
        "allow_comments": False,
        "allow_anonymous": True,
        "expires_in": 1200  # 20 мин
    }
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN, "Content-Type": "application/json"}
    logger.info("[CREATE] uid=%s kind=%s code=%s usd=%.2f", user_id, item_kind, item_code, amount)

    try:
        r = requests.post(f"{API}/createInvoice", data=json.dumps(payload), headers=headers, timeout=10)
        logger.debug("[HTTP] status=%s body=%s", r.status_code, (r.text[:800] if r.text else ""))
        r.raise_for_status()
        data = r.json()["result"]
        invoice_id = str(data.get("invoice_id"))
        pay_url = data.get("pay_url")

        # Записываем платеж (draft)
        create_payment(
            user_id=user_id,
            method="cryptobot",
            item_kind=item_kind,
            item_code=item_code,
            amount_usd=usd,
            amount_stars=None,
            external_id=str(data["invoice_id"]),
            payload="cryptobot",
            status=PaymentStatus.created
        )
        logger.info("[LINK] uid=%s invoice_id=%s url=%s", user_id, invoice_id, pay_url)
        return pay_url
    except Exception as e:
        logger.exception("[ERROR] createInvoice failed")
        return f"{WEBHOOK_URL}/payment/error"

