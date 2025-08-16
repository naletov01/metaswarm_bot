# services/referrals.py
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_, or_
from models import Payment, PaymentStatus, User

ALLOWED_METHODS     = ("fondy", "cryptobot")
ALLOWED_CODES_SUB   = ("month", "year")
ALLOWED_CODES_PACK  = ("standard", "pro", "max")

def get_ref_unique_payers_count(db: Session, referrer_id: int) -> int:
    """
    Кол-во УНИКАЛЬНЫХ приглашённых этим referrer_id, у которых есть ≥1 успешный платёж
    картой/криптой по SKU: sub:{month,year} и pack:{standard,pro,max}.
    Считаем по invited-пользователям через коррелированный EXISTS.
    """
    if not referrer_id:
        return 0

    u = aliased(User)  # явный алиас, чтобы корректно коррелировать подзапрос

    paid_exists = db.query(Payment.user_id).filter(
        Payment.user_id == u.user_id,                       # платил именно ЭТОТ приглашённый
        Payment.status == PaymentStatus.success,            # только успешные
        Payment.method.in_(ALLOWED_METHODS),                # только карта/крипта
        or_(
            and_(Payment.item_kind == "sub",  Payment.item_code.in_(ALLOWED_CODES_SUB)),
            and_(Payment.item_kind == "pack", Payment.item_code.in_(ALLOWED_CODES_PACK)),
        ),
    ).exists()

    cnt = (
        db.query(func.count())
          .select_from(u)
          .filter(
              u.referrer_id == referrer_id,                # приглашённые ЭТИМ юзером
              u.user_id != referrer_id,                    # на всякий случай отсекаем самореферал
              paid_exists                                  # у которых существует ≥1 подходящий платёж
          )
          .scalar()
    )
    return int(cnt or 0)
