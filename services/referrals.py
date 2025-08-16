# services/referrals.py

from sqlalchemy.orm import Session
from models import Payment, PaymentStatus, User

ALLOWED_METHODS = ("fondy", "cryptobot")
ALLOWED_CODES   = ("month", "year", "standard", "pro", "max")

def get_ref_paid_count(db: Session, referrer_id: int) -> int:
    """
    Считает, сколько оплат прошло по твоей ссылке:
      — только приглашённые (User.referrer_id == referrer_id)
      — только успешные платежи
      — только методы fondy/cryptobot (без Stars)
      — только подписки month/year и пакеты standard/pro/max
    """
    q = (
        db.query(Payment)
        .join(User, User.user_id == Payment.user_id)
        .filter(
            User.referrer_id == referrer_id,
            Payment.status == PaymentStatus.success,
            Payment.method.in_(ALLOWED_METHODS),
            Payment.item_kind.in_(("sub", "pack")),
            Payment.item_code.in_(ALLOWED_CODES),
        )
    )
    return q.count()
