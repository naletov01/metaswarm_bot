# db_utils.py

from db import SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
from models import Payment, PaymentStatus, User
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# — Получить или создать профиль
def get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id)
        db.add(user)#; db.commit(); db.refresh(user)
        logger.info(f"[{user_id}] 👤 Новый пользователь добавлен в БД")
    return user


def create_payment(user_id, method, item_kind, item_code, amount_usd, amount_stars, external_id, payload, status):
    with SessionLocal() as db:
        p = Payment(
            user_id=user_id,
            method=method,
            item_kind=item_kind,
            item_code=item_code,
            amount_usd=amount_usd,
            amount_stars=amount_stars,
            external_id=external_id,
            payload=payload,
            status=status,
        )
        db.add(p)
        db.commit()
        logging.getLogger(__name__).info(
            "[PAY][DB][CREATE] uid=%s method=%s kind=%s code=%s amount_usd=%s amount_stars=%s external_id=%s id=%s",
            user_id, method, item_kind, item_code, amount_usd, amount_stars, external_id, p.id
        )


def mark_payment_success(db, payment_id):
    p = db.query(Payment).get(payment_id)
    if not p: return
    p.status = PaymentStatus.success
    db.commit()
    logging.getLogger(__name__).info("[PAY][DB][SUCCESS] id=%s uid=%s", p.id, p.user_id)


def mark_payment_failed(db, payment_id, reason=""):
    p = db.query(Payment).get(payment_id)
    if not p: return
    p.status = PaymentStatus.failed
    p.error = (reason or "")[:500]
    db.commit()
    logging.getLogger(__name__).info("[PAY][DB][FAILED] id=%s uid=%s reason=%s", p.id, p.user_id, reason)


# db_utils.py — ДОПОЛНЕНИЯ (оставь твой get_user как есть)
def update_user_credits(db: Session, user_id: int, delta: int):
    user = get_user(db, user_id)
    user.credits = (user.credits or 0) + delta
    db.commit()


def set_user_subscription(db: Session, user_id: int, sub_type: str, expires_at, add_credits: int):
    user = get_user(db, user_id)
    user.premium = True
    user.subscription_type = sub_type
    user.premium_until = expires_at          # ← важно: используем твоё поле
    user.credits = (user.credits or 0) + add_credits
    db.commit()


def cleanup_stale_payments(db, max_age_hours: int = 24) -> int:
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    q = db.query(Payment).filter(
        Payment.status == PaymentStatus.created,
        Payment.created_at < cutoff,
    )
    removed = q.delete(synchronize_session=False)
    db.commit()
    logger.info("[PAY][CLEANUP] removed=%s older_than=%sh cutoff=%s",
             removed, max_age_hours, cutoff.isoformat())
    return removed



