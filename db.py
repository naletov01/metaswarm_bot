from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from sqlalchemy.orm import Session
from typing import Generator

Base = declarative_base()
SessionLocal = sessionmaker(autoflush=False, autocommit=False)

if DATABASE_URL.startswith("sqlite://"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=True # временно тру, поменять на False
    )
else:
    engine = create_engine(DATABASE_URL, echo=False)
SessionLocal.configure(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        # тут обычно не коммитим — коммитятся внутри endpoint’ов
    except Exception:
        db.rollback()               # 1. Откатываем при ошибке
        raise                       # 2. Пробрасываем дальше
    finally:
        db.close()                  # 3. Всегда закрываем


# — Получить или создать профиль
def get_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        user = User(user_id=user_id)
        db.add(user); db.commit(); db.refresh(user)
    return user
