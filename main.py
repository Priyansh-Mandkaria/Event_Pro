from fastapi import FastAPI, Depends, Request, Form, Response, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os

import models
import bcrypt
from database import engine, get_db

# Use absolute path for static/templates to ensure they load on Vercel
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

models.Base.metadata.create_all(bind=engine)

# Ensure default admin exists (especially for Vercel /tmp DB)
def init_db():
    db = next(get_db())
    admin_email = "admin@eventpro.com"
    if not db.query(models.User).filter(models.User.email == admin_email).first():
        admin = models.User(
            name="Super Admin",
            email=admin_email,
            password_hash=bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            role="admin"
        )
        db.add(admin)
        db.commit()

init_db()

app = FastAPI()

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# [rest of the app continues here...]
