# services/referrals.py

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from models import Payment, PaymentStatus, User

ALLOWED_METHODS = ("fondy", "cryptobot")
ALLOWED_CODES_SUB  = ("month", "year")
ALLOWED_CODES_PACK = ("standard", "pro", "max")

def get_ref_paid_count(db: Session, referrer_id: int) -> int:
    """
    Считает кол-во успешных оплат у приглашённых этим referrer_id.
    Учитываем только карту/крипту и только SKU: sub:month/year, pack:standard/pro/max.
    Исключаем самореферал на всякий случай.
    """
    if not referrer_id:
        return 0

    q = (
        db.query(func.count())
        .select_from(Payment)
        .join(User, User.user_id == Payment.user_id)  # платил именно приглашённый
        .filter(
            User.referrer_id == referrer_id,              # приглашённые этим юзером
            Payment.status == PaymentStatus.success,       # только успешные
            Payment.method.in_(ALLOWED_METHODS),           # только карта/крипто
            or_(
                and_(Payment.item_kind == "sub",  Payment.item_code.in_(ALLOWED_CODES_SUB)),
                and_(Payment.item_kind == "pack", Payment.item_code.in_(ALLOWED_CODES_PACK)),
            ),
            Payment.user_id != referrer_id                 # на всякий исключим самореферал
        )
    )
    return int(q.scalar() or 0)
