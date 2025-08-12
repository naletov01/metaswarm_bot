from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, BigInteger, Enum as SAEnum
from datetime import datetime
import enum
from db import Base


class User(Base):
    __tablename__ = 'users'
    
    user_id         = Column(BigInteger, primary_key=True, index=True)
    credits         = Column(Integer, default=0, nullable=False)
    premium         = Column(Boolean, default=False, nullable=False)
    subscription_type = Column(String, nullable=True)
    premium_until   = Column(DateTime, nullable=True)
    invited_count   = Column(Integer, default=0, nullable=False)
    bonus_credits   = Column(Integer, default=0, nullable=False)
    referrer_id = Column(BigInteger, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentStatus(str, enum.Enum):
    created = "created"
    pending = "pending"
    success = "success"
    failed  = "failed"


class Payment(Base):
    __tablename__ = "payments"

    id                = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id           = Column(BigInteger, index=True, nullable=False)
    method            = Column(String, nullable=False)      # 'stars' | 'fondy' | 'cryptobot'
    item_kind         = Column(String, nullable=False)      # 'sub' | 'pack'
    item_code         = Column(String, nullable=False)      # 'day'|'month'|'year' или 'standart'|'pro'|'max'
    amount_usd        = Column(Numeric(10,2), nullable=True)
    amount_stars      = Column(Integer, nullable=True)
    external_id       = Column(String, nullable=True)       # id инвойса у провайдера
    payload           = Column(String, nullable=True)       # наш произвольный payload (подпись)
    status            = Column(SAEnum(PaymentStatus), default=PaymentStatus.created, nullable=False)
    error             = Column(String, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

