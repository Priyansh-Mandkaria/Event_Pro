import models
import bcrypt
from database import SessionLocal, engine

def init_admin():
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    admin_email = "admin@eventpro.com"
    admin_pass = "admin123"
    
    existing_admin = db.query(models.User).filter(models.User.email == admin_email).first()
    if not existing_admin:
        hashed_pass = bcrypt.hashpw(admin_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin_user = models.User(
            name="Super Admin",
            email=admin_email,
            password_hash=hashed_pass,
            role="admin"
        )
        db.add(admin_user)
        db.commit()
        print(f"Admin created: {admin_email} / {admin_pass}")
    else:
        print("Admin user already exists.")
    db.close()

if __name__ == "__main__":
    init_admin()
