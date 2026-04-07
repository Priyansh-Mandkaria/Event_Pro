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
            password_hash=bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            role="admin"
        )
        db.add(admin)
        db.commit()

init_db()

app = FastAPI()

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def get_current_user_from_cookie(request: Request, db: Session):
    session_id = request.cookies.get("session_id")
    if not session_id: return None
    return db.query(models.User).filter(models.User.email == session_id).first()

# ================= AUTH ROUTES ================= #

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request, error: str = None):
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request, "error": error})

@app.post("/login")
def login_post(response: Response, email: str = Form(...), password: str = Form(...), is_admin: bool = Form(False), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user and verify_password(password, user.password_hash):
        if is_admin and user.role != "admin":
            return RedirectResponse(url="/login?error=Not an admin", status_code=status.HTTP_302_FOUND)
        response = RedirectResponse(url=f"/{user.role}", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="session_id", value=user.email)
        return response
    return RedirectResponse(url="/login?error=Invalid credentials", status_code=status.HTTP_302_FOUND)

@app.get("/admin_login", response_class=HTMLResponse)
def admin_login_get(request: Request, error: str = None):
    return templates.TemplateResponse(request=request, name="admin_login.html", context={"request": request, "error": error})

@app.post("/admin_login")
def admin_login_post(response: Response, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email, models.User.role == "admin").first()
    if user and verify_password(password, user.password_hash):
        response = RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="session_id", value=user.email)
        return response
    return RedirectResponse(url="/admin_login?error=Invalid admin credentials", status_code=status.HTTP_302_FOUND)

@app.get("/signup", response_class=HTMLResponse)
def signup_get(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html", context={"request": request})

@app.post("/signup")
def signup_post(name: str = Form(...), email: str = Form(...), password: str = Form(...), role: str = Form(...), vendor_category: str = Form(None), db: Session = Depends(get_db)):
    if role == "admin": return RedirectResponse(url="/signup?error=Admin signup restricted", status_code=status.HTTP_302_FOUND)
    if db.query(models.User).filter(models.User.email == email).first():
        return RedirectResponse(url="/signup?error=Email exists", status_code=status.HTTP_302_FOUND)
    
    hashed_pass = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    new_user = models.User(name=name, email=email, password_hash=hashed_pass, role=role, vendor_category=vendor_category)
    if role == "user":
        new_user.membership_number = f"MEM-{int(datetime.utcnow().timestamp())}"
        new_user.membership_expiry = datetime.utcnow() + timedelta(days=365)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@app.get("/logout")
def logout(response: Response):
    response = RedirectResponse(url="/login")
    response.delete_cookie("session_id")
    return response

# ================= ADMIN ROUTES ================= #

@app.get("/admin")
def admin_home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="admin_dashboard.html", context={"request": request, "user": user})

@app.get("/admin/maintain_user")
def admin_maintain_user(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="admin_maintain_user.html", context={"request": request, "user": user})

@app.get("/admin/maintain_vendor")
def admin_maintain_vendor(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="admin_maintain_vendor.html", context={"request": request, "user": user})

# ================= VENDOR ROUTES ================= #

@app.get("/vendor")
def vendor_home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != "vendor": return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="vendor_dashboard.html", context={"request": request, "user": user})

@app.get("/vendor/add_item")
def vendor_add_item_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != "vendor": return RedirectResponse(url="/login")
    products = db.query(models.Product).filter(models.Product.vendor_id == user.id).all()
    return templates.TemplateResponse(request=request, name="vendor_add_item.html", context={"request": request, "products": products, "user": user})

@app.post("/vendor/add_product")
async def vendor_add_product(request: Request, name: str = Form(...), price: float = Form(...), description: str = Form(""), image: UploadFile = File(None), db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user: return RedirectResponse(url="/login")
    
    image_filename = "default.jpg"
    if image and image.filename:
        os.makedirs(os.path.join(BASE_DIR, "static/uploads"), exist_ok=True)
        image_filename = f"{int(datetime.utcnow().timestamp())}_{image.filename}"
        with open(os.path.join(BASE_DIR, "static/uploads", image_filename), "wb") as f:
            f.write(await image.read())
            
    new_product = models.Product(vendor_id=user.id, name=name, price=price, description=description, image_name=image_filename)
    db.add(new_product)
    db.commit()
    return RedirectResponse(url="/vendor/add_item", status_code=status.HTTP_302_FOUND)

@app.get("/vendor/product_status")
def vendor_product_status(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != "vendor": return RedirectResponse(url="/login")
    orders = db.query(models.Order).filter(models.Order.vendor_id == user.id).all()
    return templates.TemplateResponse(request=request, name="vendor_product_status.html", context={"request": request, "orders": orders, "user": user})

@app.get("/vendor/update_status/{order_id}")
def vendor_update_status_get(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user: return RedirectResponse(url="/login")
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    return templates.TemplateResponse(request=request, name="vendor_update_status.html", context={"request": request, "order": order})

@app.post("/vendor/update_status/{order_id}")
def vendor_update_status_post(order_id: int, order_status: str = Form(...), db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if order:
        order.status = order_status
        db.commit()
    return RedirectResponse(url="/vendor/product_status", status_code=status.HTTP_302_FOUND)

@app.get("/vendor/requests")
def vendor_requests(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != "vendor": return RedirectResponse(url="/login")
    item_requests = db.query(models.ItemRequest).filter(models.ItemRequest.vendor_id == user.id).all()
    requests_data = []
    for ir in item_requests:
        cust = db.query(models.User).filter(models.User.id == ir.user_id).first()
        requests_data.append({"id": ir.id, "cust_name": cust.name if cust else "Unknown", "cust_email": cust.email if cust else "N/A", "item_name": ir.item_name, "status": ir.status})
    return templates.TemplateResponse(request=request, name="vendor_requests.html", context={"request": request, "requests": requests_data})

@app.post("/vendor/request/delete/{req_id}")
def delete_vendor_request(req_id: int, db: Session = Depends(get_db)):
    req = db.query(models.ItemRequest).filter(models.ItemRequest.id == req_id).first()
    if req:
        db.delete(req)
        db.commit()
    return RedirectResponse(url="/vendor/requests", status_code=status.HTTP_302_FOUND)

# ================= USER ROUTES ================= #

@app.get("/user")
def user_portal(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user or user.role != "user": return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="user_portal.html", context={"request": request, "user": user})

@app.get("/user/vendors")
def list_vendors(request: Request, category: str, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user: return RedirectResponse(url="/login")
    vendors = db.query(models.User).filter(models.User.role == "vendor", models.User.vendor_category == category).all()
    return templates.TemplateResponse(request=request, name="user_vendors.html", context={"request": request, "vendors": vendors, "category": category})

@app.get("/user/products/{vendor_id}")
def list_products(request: Request, vendor_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user: return RedirectResponse(url="/login")
    vendor = db.query(models.User).filter(models.User.id == vendor_id).first()
    products = db.query(models.Product).filter(models.Product.vendor_id == vendor_id).all()
    return templates.TemplateResponse(request=request, name="user_products.html", context={"request": request, "products": products, "vendor": vendor})

@app.post("/user/add_to_cart")
def add_to_cart(request: Request, product_id: int = Form(...), db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user: return RedirectResponse(url="/login")
    existing = db.query(models.CartItem).filter(models.CartItem.user_id == user.id, models.CartItem.product_id == product_id).first()
    if existing:
        existing.quantity += 1
    else:
        new_item = models.CartItem(user_id=user.id, product_id=product_id, quantity=1)
        db.add(new_item)
    db.commit()
    p = db.query(models.Product).filter(models.Product.id == product_id).first()
    return RedirectResponse(url=f"/user/products/{p.vendor_id}", status_code=status.HTTP_302_FOUND)

@app.get("/user/cart")
def view_cart(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user: return RedirectResponse(url="/login")
    items = db.query(models.CartItem).filter(models.CartItem.user_id == user.id).all()
    cart_data = []
    total = 0
    for i in items:
        p = db.query(models.Product).filter(models.Product.id == i.product_id).first()
        if p:
            line_total = p.price * i.quantity
            total += line_total
            cart_data.append({"cart_id": i.id, "name": p.name, "price": p.price, "quantity": i.quantity, "total": line_total})
    return templates.TemplateResponse(request=request, name="cart.html", context={"request": request, "items": cart_data, "total": total})

@app.post("/cart/update/{cart_id}")
def update_cart_quantity(cart_id: int, change: int = Form(...), db: Session = Depends(get_db)):
    item = db.query(models.CartItem).filter(models.CartItem.id == cart_id).first()
    if item:
        item.quantity += change
        if item.quantity < 1: db.delete(item)
        db.commit()
    return RedirectResponse(url="/user/cart", status_code=status.HTTP_302_FOUND)

@app.post("/cart/remove/{cart_id}")
def remove_cart_item(cart_id: int, db: Session = Depends(get_db)):
    item = db.query(models.CartItem).filter(models.CartItem.id == cart_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/user/cart", status_code=status.HTTP_302_FOUND)

@app.post("/cart/delete_all")
def delete_all_cart(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if user:
        db.query(models.CartItem).filter(models.CartItem.user_id == user.id).delete()
        db.commit()
    return RedirectResponse(url="/user/cart", status_code=status.HTTP_302_FOUND)

@app.get("/user/checkout")
def checkout_get(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user: return RedirectResponse(url="/login")
    items = db.query(models.CartItem).filter(models.CartItem.user_id == user.id).all()
    total = 0
    for i in items:
        p = db.query(models.Product).filter(models.Product.id == i.product_id).first()
        if p: total += p.price * i.quantity
    return templates.TemplateResponse(request=request, name="checkout.html", context={"request": request, "total": total, "user": user})

@app.post("/user/checkout")
def checkout_post(request: Request, name: str = Form(...), email: str = Form(...), address: str = Form(...), city: str = Form(...), 
                  phone: str = Form(...), payment: str = Form(...), total_amount: float = Form(...), db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user: return RedirectResponse(url="/login")
    cart_items = db.query(models.CartItem).filter(models.CartItem.user_id == user.id).all()
    if not cart_items: return RedirectResponse(url="/user")
    
    # Group items by Vendor
    vendor_items = {}
    for ci in cart_items:
        p = db.query(models.Product).filter(models.Product.id == ci.product_id).first()
        if p.vendor_id not in vendor_items: vendor_items[p.vendor_id] = []
        vendor_items[p.vendor_id].append({"item": ci, "product": p})
        
    new_orders = []
    for v_id, items_list in vendor_items.items():
        v_total = sum(i["product"].price * i["item"].quantity for i in items_list)
        new_order = models.Order(user_id=user.id, vendor_id=v_id, cust_name=name, cust_email=email, address=address, city=city, phone_number=phone, payment_method=payment, total_amount=v_total)
        db.add(new_order)
        db.commit() # Commit to get order.id
        for i_data in items_list:
            oi = models.OrderItem(order_id=new_order.id, product_id=i_data["item"].product_id, quantity=i_data["item"].quantity, price_at_time=i_data["product"].price)
            db.add(oi)
        new_orders.append(new_order)
    
    db.query(models.CartItem).filter(models.CartItem.user_id == user.id).delete()
    db.commit()
    return templates.TemplateResponse(request=request, name="checkout_success.html", context={"request": request, "orders": new_orders})

@app.get("/user/order_status")
def view_order_status(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user: return RedirectResponse(url="/login")
    orders = db.query(models.Order).filter(models.Order.user_id == user.id).all()
    return templates.TemplateResponse(request=request, name="user_order_status.html", context={"request": request, "orders": orders})

@app.post("/user/request_item")
def request_item(request: Request, vendor_id: int = Form(...), item_name: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user: return RedirectResponse(url="/login")
    new_req = models.ItemRequest(user_id=user.id, vendor_id=vendor_id, item_name=item_name)
    db.add(new_req)
    db.commit()
    return RedirectResponse(url="/user", status_code=status.HTTP_302_FOUND)
