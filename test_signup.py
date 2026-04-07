import models
from database import SessionLocal, engine
from passlib.context import CryptContext
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def run_test():
    try:
        db = SessionLocal()
        username = "testuser2"
        password = "password"
        role = "user"
        new_user = models.User(
            username=username, 
            password_hash=pwd_context.hash(password), 
            role=role
        )
        new_user.membership_number = f"MEM-{datetime.utcnow().timestamp()}"
        new_user.membership_expiry = datetime.utcnow() + timedelta(days=30)
        
        db.add(new_user)
        db.commit()
        print("SUCCESS")
    except Exception as e:
        import traceback
        traceback.print_exc()

run_test()
