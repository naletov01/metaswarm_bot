# from db import SessionLocal
from sqlalchemy.orm import Session
from models import User
import logging

logger = logging.getLogger(__name__)

# — Получить или создать профиль
def get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id)
        db.add(user)#; db.commit(); db.refresh(user)
        logger.info(f"[{user_id}] 👤 Новый пользователь добавлен в БД")
    return user
