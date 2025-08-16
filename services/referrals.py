# services/referrals.py
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from models import Payment, PaymentStatus, User

ALLOWED_METHODS    = ("fondy", "cryptobot")
ALLOWED_CODES_SUB  = ("month", "year")
ALLOWED_CODES_PACK = ("standard", "pro", "max")

def get_ref_unique_payers_count(db: Session, referrer_id: int) -> int:
    """
    Кол-во УНИКАЛЬНЫХ приглашённых этим referrer_id, у которых есть ≥1 успешный платёж
    (только fondy/cryptobot; SKU: sub:month/year, pack:standard/pro/max).
    """
    if not referrer_id:
        return 0

    # 1) список user_id всех приглашённых этим реферером
    invited_ids_sq = (
        db.query(User.user_id)
          .filter(User.referrer_id == referrer_id)
          .subquery()
    )

    # 2) считаем DISTINCT плательщиков только из этого списка
    cnt = (
        db.query(func.count(func.distinct(Payment.user_id)))
          .filter(
              Payment.user_id.in_(invited_ids_sq),
              Payment.status == PaymentStatus.success,
              Payment.method.in_(ALLOWED_METHODS),
              or_(
                  and_(Payment.item_kind == "sub",  Payment.item_code.in_(ALLOWED_CODES_SUB)),
                  and_(Payment.item_kind == "pack", Payment.item_code.in_(ALLOWED_CODES_PACK)),
              )
          )
          .scalar()
    )
    return int(cnt or 0)
