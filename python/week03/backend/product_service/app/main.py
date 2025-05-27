# app/main.py

"""
FastAPI Product Service with image upload, CRUD, validation, and stock management.
"""

from fastapi import (
    FastAPI, Depends, HTTPException, Query, File, UploadFile, Form
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging

from db import Base, engine, get_db
from models import Product
from schemas import ProductCreate, ProductUpdate, ProductResponse
from azure_utils import upload_to_azure_blob

from typing import Optional

# Configure Logging
logging.basicConfig(level=logging.INFO)
RESTOCK_THRESHOLD = 5

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title="Product Service API",
    description="Manages products and stock for mini-ecommerce app",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CRUD Endpoints

@app.post("/products/", response_model=ProductResponse, status_code=201)
def create_product(
        name: str = Form(...),
        description: str = Form(None),
        price: float = Form(...),
        stock_quantity: int = Form(...),
        image: UploadFile = File(None),
        db: Session = Depends(get_db)
    ):
    """
    Create a new product, including optional image upload to Azure.
    """
    image_url = None
    if image:
        image_url = upload_to_azure_blob(image)
    db_product = Product(
        name=name,
        description=description,
        price=price,
        stock_quantity=stock_quantity,
        image_url=image_url
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
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    stock_quantity: Optional[int] = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """
    Update product details and optionally upload a new image.
    Only provided fields will be updated.
    """
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    updated = False
    if name is not None:
        product.name = name
        updated = True
    if description is not None:
        product.description = description
        updated = True
    if price is not None:
        if price <= 0:
            raise HTTPException(status_code=422, detail="Price must be positive")
        product.price = price
        updated = True
    if stock_quantity is not None:
        if stock_quantity < 0:
            raise HTTPException(status_code=422, detail="Stock quantity cannot be negative")
        product.stock_quantity = stock_quantity
        updated = True
    if image:
        image_url = upload_to_azure_blob(image)
        product.image_url = image_url
        updated = True

    if updated:
        db.commit()
        db.refresh(product)
    return product

@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"detail": "Product deleted successfully"}

@app.put("/products/{product_id}/stock", response_model=ProductResponse)
def update_stock(
    product_id: int,
    stock_quantity: int = Query(..., ge=0),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.stock_quantity = stock_quantity
    db.commit()
    db.refresh(product)
    if product.stock_quantity < RESTOCK_THRESHOLD:
        logging.info(
            f"Restock needed for product {product.name}: only {product.stock_quantity} left"
        )
    return product
