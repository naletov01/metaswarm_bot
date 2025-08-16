# services/referrals.py
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from models import Payment, PaymentStatus, User

ALLOWED_METHODS     = ("fondy", "cryptobot")
ALLOWED_CODES_SUB   = ("month", "year")
ALLOWED_CODES_PACK  = ("standard", "pro", "max")

def get_ref_unique_payers_count(db: Session, referrer_id: int) -> int:
    """
    Кол-во УНИКАЛЬНЫХ приглашённых этим referrer_id, у которых есть ≥1 успешный платёж
    (только fondy/cryptobot; SKU: sub:month/year, pack:standard/pro/max).
    Считаем по invited-пользователям через EXISTS, чтобы не засчитывать тех, кто просто перешёл.
    """
    if not referrer_id:
        return 0

    # EXISTS-подзапрос: у invited-пользователя есть ≥1 подходящий платёж
    paid_exists = db.query(Payment.user_id).filter(
        Payment.user_id == User.user_id,                         # платил именно этот invited
        Payment.status == PaymentStatus.success,                 # только успешные
        Payment.method.in_(ALLOWED_METHODS),                     # только карта/крипта
        or_(
            and_(Payment.item_kind == "sub",  Payment.item_code.in_(ALLOWED_CODES_SUB)),
            and_(Payment.item_kind == "pack", Payment.item_code.in_(ALLOWED_CODES_PACK)),
        )
    ).exists()

    cnt = (
        db.query(func.count())                                   # считаем людей, не платежи
          .select_from(User)
          .filter(
              User.referrer_id == referrer_id,                   # это приглашённые ЭТИМ юзером
              User.user_id != referrer_id,                       # на всякий случай исключим самореферал
              paid_exists                                        # у них есть ≥1 нужный платёж
          )
          .scalar()
    )
    return int(cnt or 0)
