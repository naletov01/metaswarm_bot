# test_db.py
from db import SessionLocal 
from models import User

db = SessionLocal()
# 1) добавляем тестового юзера
u = User(user_id=424242, credits=5)
db.add(u)
db.commit()

# 2) читаем его обратно
u2 = db.query(User).filter_by(user_id=424242).first()
print("Loaded user:", u2.user_id, "credits=", u2.credits)

# 3) чистим за собой (удаляем запись)
db.delete(u2)
db.commit()
db.close()
