# week02/backend/product_service/app/main.py

"""
FastAPI Product Service with enhanced CRUD, validation, and stock management.
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, Numeric
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime
from pydantic import BaseModel, Field, validator
from db import engine, Base, get_db
import logging
from datetime import datetime

# -----------------------------
# Configure Logging
# -----------------------------
logging.basicConfig(level=logging.INFO)
RESTOCK_THRESHOLD = 5  # Threshold for restock notification

# -----------------------------
# Database Model
# -----------------------------
class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Create tables
Base.metadata.create_all(bind=engine)

# -----------------------------
# Pydantic Schemas
# -----------------------------
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(None, max_length=2000)
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)

class ProductUpdate(BaseModel):
    name: str = Field(None, min_length=1, max_length=255)
    description: str = Field(None, max_length=2000)
    price: float = Field(None, gt=0)
    stock_quantity: int = Field(None, ge=0)

class ProductResponse(ProductCreate):
    product_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True

# -----------------------------
# FastAPI App Initialization
# -----------------------------
app = FastAPI(
    title="Product Service API",
    description="Manages products and stock for mini-ecommerce app",
    version="1.0.0"
)

# Enable CORS (for frontend dev/testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# CRUD Endpoints
# -----------------------------

@app.post("/products/", response_model=ProductResponse, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Create a new product with validation.
    """
    db_product = Product(
        name=product.name,
        description=product.description,
        price=product.price,
        stock_quantity=product.stock_quantity,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products/", response_model=list[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: str = Query(None, max_length=255)
):
    """
    List products, with optional pagination and search by name/description.
    """
    query = db.query(Product)
    if search:
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) |
            (Product.description.ilike(f"%{search}%"))
        )
    products = query.offset(skip).limit(limit).all()
    return products

@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single product by ID.
    """
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int, updated: ProductUpdate, db: Session = Depends(get_db)
):
    """
    Update product information. Only supplied fields will be updated.
    """
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for field, value in updated.dict(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product

@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Delete a product by ID.
    """
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"detail": "Product deleted successfully"}

# -----------------------------
# Stock Management Endpoint
# -----------------------------

@app.put("/products/{product_id}/stock", response_model=ProductResponse)
def update_stock(
    product_id: int,
    stock_quantity: int = Query(..., ge=0),
    db: Session = Depends(get_db)
):
    """
    Update stock quantity for a product. Logs a message if stock falls below threshold.
    """
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.stock_quantity = stock_quantity
    db.commit()
    db.refresh(product)
    if product.stock_quantity < RESTOCK_THRESHOLD:
        logging.info(
            f"Restock needed for product {product.name}: "
            f"only {product.stock_quantity} left"
        )
    return product
