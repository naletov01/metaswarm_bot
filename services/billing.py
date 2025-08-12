import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import Payment, PaymentStatus
from config import SUB_CREDITS, SUB_PERIOD_DAYS
from db_utils import get_user, update_user_credits, set_user_subscription, create_payment, mark_payment_success, mark_payment_failed

logger = logging.getLogger(__name__)

# Стоимость в $ и в звёздах
USD_PRICE_BY_SUB = {'day': 1, 'month': 10, 'year': 85}
STARS_PRICE_BY_SUB = {'day': 150, 'month': 1000, 'year': 8500} # {'day': 150, 'month': 1000, 'year': 8500}
STARS_PRICE_BY_PACK = {'standart': 999, 'pro': 3000, 'max': 5000} # {'standart': 1000, 'pro': 3000, 'max': 5000}
USD_PRICE_BY_PACK = {'standart': 10, 'pro': 30, 'max': 50}

def compute_price(item_kind: str, item_code: str):
    if item_kind == 'sub':
        return USD_PRICE_BY_SUB[item_code], STARS_PRICE_BY_SUB[item_code]
    else:
        return USD_PRICE_BY_PACK[item_code], STARS_PRICE_BY_PACK[item_code]

def grant_benefit(db: Session, user_id: int, item_kind: str, item_code: str):
    """Начисление после успешной оплаты."""
    if item_kind == 'sub':
        # одноразовость 'day'
        if item_code == 'day':
            # проверяем — не покупал ли раньше успешно 3-дневную
            prev = db.query(Payment).filter(
                Payment.user_id==user_id,
                Payment.item_kind=='sub',
                Payment.item_code=='day',
                Payment.status==PaymentStatus.success
            ).first()
            if prev:
                logger.info(f"[{user_id}] попытка повторной 3-дн подписки — блокируем")
                return False

        days = SUB_PERIOD_DAYS[item_code]
        credits = SUB_CREDITS[item_code]
        expires_at = datetime.utcnow() + timedelta(days=days)
        set_user_subscription(db, user_id, sub_type=item_code, expires_at=expires_at, add_credits=credits)
        return True

    elif item_kind == 'pack':
        add_credits = {
            'standart': 800,
            'pro': 3000,
            'max': 6000,
        }[item_code]
        update_user_credits(db, user_id, delta=add_credits)
        return True

    return False

def finalize_success(db: Session, payment: Payment):
    ok = grant_benefit(db, payment.user_id, payment.item_kind, payment.item_code)
    if not ok:
        # если не начислили из-за повторной 3-дн подписки — пометим fail
        mark_payment_failed(db, payment.id, "day-subscription already used")
        return False
    mark_payment_success(db, payment.id)
    return True

