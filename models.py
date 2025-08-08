from sqlalchemy import Column, Integer, Boolean, DateTime, String
from datetime import datetime
from db import Base

class User(Base):
    __tablename__ = 'users'
    
    user_id         = Column(Integer, primary_key=True, index=True)
    credits         = Column(Integer, default=0, nullable=False)
    premium         = Column(Boolean, default=False, nullable=False)
    subscription_type = Column(String, nullable=True)
    premium_until   = Column(DateTime, nullable=True)
    invited_count   = Column(Integer, default=0, nullable=False)
    bonus_credits   = Column(Integer, default=0, nullable=False)
    referrer_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
