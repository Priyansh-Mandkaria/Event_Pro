from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String) # 'admin', 'vendor', 'user'
    vendor_category = Column(String, nullable=True) # Catering, Florist, Decoration, Lightning
    membership_number = Column(String, nullable=True)
    membership_expiry = Column(DateTime, nullable=True)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    image_name = Column(String, default="default.jpg")
    status = Column(String, default="Available")

class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    vendor_id = Column(Integer, ForeignKey("users.id")) # Important for vendor tracking
    status = Column(String, default="Received") # Received, Ready for Shipping, Out For Delivery
    
    # Checkout Data
    cust_name = Column(String)
    cust_email = Column(String)
    address = Column(String)
    city = Column(String)
    phone_number = Column(String)
    payment_method = Column(String) # Cash / UPI
    state = Column(String)
    pincode = Column(String)
    total_amount = Column(Float)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price_at_time = Column(Float)

class ItemRequest(Base):
    __tablename__ = "item_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    vendor_id = Column(Integer, ForeignKey("users.id"))
    item_name = Column(String)
    status = Column(String, default="Requested")
