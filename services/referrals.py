# services/referrals.py
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from models import Payment, PaymentStatus, User

ALLOWED_METHODS   = ("fondy", "cryptobot")
ALLOWED_CODES_SUB  = ("month", "year")
ALLOWED_CODES_PACK = ("standard", "pro", "max")

def get_ref_unique_payers_count(db: Session, referrer_id: int) -> int:
    """
    Считает КОЛ-ВО УНИКАЛЬНЫХ приглашённых, у которых есть ≥1 успешный платёж
    через карту/крипту по SKU: sub:month/year и pack:standard/pro/max.
    """
    return int(
        db.query(func.count(func.distinct(Payment.user_id)))
          .select_from(Payment)
          .join(User, User.user_id == Payment.user_id)  # платил именно приглашённый
          .filter(
              User.referrer_id == referrer_id,
              Payment.status == PaymentStatus.success,
              Payment.method.in_(ALLOWED_METHODS),
              or_(
                  and_(Payment.item_kind == "sub",  Payment.item_code.in_(ALLOWED_CODES_SUB)),
                  and_(Payment.item_kind == "pack", Payment.item_code.in_(ALLOWED_CODES_PACK)),
              ),
              Payment.user_id != referrer_id,  # на всякий случай исключим самореферал
          )
          .scalar() or 0
    )
