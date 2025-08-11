from db import SessionLocal
from sqlalchemy.orm import Session
from models import User
import logging
from models import Payment, PaymentStatus
from datetime import datetime

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


def mark_payment_success(db, payment_id):
    p = db.query(Payment).get(payment_id)
    if not p: return
    p.status = PaymentStatus.success
    db.commit()


def mark_payment_failed(db, payment_id, reason=""):
    p = db.query(Payment).get(payment_id)
    if not p: return
    p.status = PaymentStatus.failed
    p.error = (reason or "")[:500]
    db.commit()


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


