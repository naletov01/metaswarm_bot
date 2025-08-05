# test_db_extended.py
from datetime import datetime, timedelta
from db import SessionLocal 
from models import User

db = SessionLocal()

try:
    # 1) Создаем тестового пользователя
    u = User(
        user_id=999999,
        credits=100,
        premium=False,
        subscription_type=None,
        premium_until=None,
        invited_count=0,
        bonus_credits=0
    )
    db.add(u)
    db.commit()
    print("✅ Пользователь создан:", u.user_id, "credits=", u.credits)

    # 2) Загружаем его обратно
    u2 = db.query(User).filter_by(user_id=999999).first()
    print("📌 Загружен:", u2.user_id, "credits=", u2.credits, "premium=", u2.premium)

    # 3) Обновляем кредиты
    u2.credits += 200
    db.commit()
    print("💰 Кредиты обновлены:", u2.credits)

    # 4) Включаем подписку Premium
    u2.premium = True
    u2.subscription_type = "monthly"
    u2.premium_until = datetime.utcnow() + timedelta(days=30)
    db.commit()
    print("🔥 Подписка Premium активирована до:", u2.premium_until)

    # 5) Добавляем бонусы и друзей
    u2.invited_count += 3
    u2.bonus_credits += 50
    db.commit()
    print("👥 Приглашено друзей:", u2.invited_count, "| Бонусные кредиты:", u2.bonus_credits)

    # 6) Проверяем результат
    u3 = db.query(User).filter_by(user_id=999999).first()
    print("📊 Итог:", {
        "credits": u3.credits,
        "premium": u3.premium,
        "type": u3.subscription_type,
        "until": u3.premium_until,
        "invites": u3.invited_count,
        "bonus": u3.bonus_credits,
    })

finally:
    # 7) Удаляем тестового пользователя
    u_del = db.query(User).filter_by(user_id=999999).first()
    if u_del:
        db.delete(u_del)
        db.commit()
        print("🗑 Пользователь удалён")

    db.close()
