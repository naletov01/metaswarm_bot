import hmac, hashlib, base64, json, logging
from config import WEBHOOK_SECRET, WEBHOOK_URL
from payments.stars import build_stars_invoice_link
from payments.fondy import build_fondy_link
from payments.cryptobot import build_cryptobot_link

logger = logging.getLogger(__name__)

def _sign(data: dict) -> str:
    raw = json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    sig = hmac.new(WEBHOOK_SECRET.encode('utf-8'), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode('utf-8')

def build_urls_for_item(user_id: int, item_kind: str, item_code: str):
    """Возвращает словарь со ссылками для трёх способов оплаты."""
    payload = {"uid": user_id, "kind": item_kind, "code": item_code}
    token = _sign(payload)
    payload["sig"] = token

    # было (создавало инвойс заранее — так больше не делаем):
    stars_url = build_stars_invoice_link(user_id, item_kind, item_code)
    # Stars — создаём invoice-link сразу
    # stars_url = f"{WEBHOOK_URL}/pay/stars?data={base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()}"

    # Fondy / CryptoBot — отдадим внешнюю ссылку на наш backend,
    # он выдаст редирект на реальный инвойс и зафиксирует payment.created
    fondy_url = f"{WEBHOOK_URL}/pay/fondy?data={base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()}"
    crypto_url = f"{WEBHOOK_URL}/pay/cryptobot?data={base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()}"

    return {
        "stars": stars_url,
        "fondy": fondy_url,
        "cryptobot": crypto_url,
    }

