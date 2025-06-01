# week02/backend/product_service/app/main.py

"""
FastAPI Product Service API.
Manages product information including creation, retrieval, updates, deletion,
and stock management. This service demonstrates a structured approach with
separate database models and Pydantic schemas.
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Text, Numeric
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime
from pydantic import BaseModel, Field, validator
from db import engine, Base, get_db
from models import Product
from schemas import ProductCreate, ProductUpdate, ProductResponse
import logging
from datetime import datetime
from typing import Optional, List

# -----------------------------
# Configure Logging
# -----------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
RESTOCK_THRESHOLD = 5  # Threshold for restock notification

# -----------------------------
# Database Table Creation
# -----------------------------
# This line attempts to create all tables defined by Base (Product model)
# if they do not already exist in the connected database.
# It's typically run once when the application starts.
Base.metadata.create_all(bind=engine)

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

@app.post("/products/", response_model=ProductResponse, status_code=201, summary="Create a new product")
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Creates a new product entry in the database.

    - Takes a `ProductCreate` schema as input, ensuring validation of name, description, price, and stock.
    - Returns the created product's details, including its auto-generated `product_id` and timestamps.
    """
    logging.info(f"Creating product: {product.name}")
    db_product = Product(
        name=product.name,
        description=product.description,
        price=product.price,
        stock_quantity=product.stock_quantity,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    logging.info(f"Product '{db_product.name}' (ID: {db_product.product_id}) created successfully.")
    return db_product

@app.get("/products/", response_model=List[ProductResponse], summary="List all products with pagination and search")
def list_products(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip (for pagination)."),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of items to return (for pagination)."),
    search: str = Query(None, max_length=255, description="Search term for product name or description (case-insensitive).")
):
    """
    Retrieves a list of products from the database.

    - Supports pagination via `skip` and `limit` query parameters.
    - Allows searching products by `name` or `description` using a case-insensitive partial match.
    - Returns a list of `ProductResponse` objects.
    """
    logging.info(f"Listing products with skip={skip}, limit={limit}, search='{search}'")
    query = db.query(Product)
    if search:
        # Apply case-insensitive search filter on name and description
        query = query.filter(
            (Product.name.ilike(f"%{search}%")) |
            (Product.description.ilike(f"%{search}%"))
        )
    products = query.offset(skip).limit(limit).all()
    logging.info(f"Found {len(products)} products.")
    return products

@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db), summary="Retrieve a product by ID"):
    """
    Retrieves details of a single product by its unique ID.
    
    - Returns a `ProductResponse` object if the product is found.
    - Raises a 404 HTTP exception if the product does not exist.
    """
    logging.info(f"Fetching product with ID: {product_id}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logging.warning(f"Product with ID: {product_id} not found.")
        raise HTTPException(status_code=404, detail="Product not found")
    logging.info(f"Product '{product.name}' (ID: {product_id}) retrieved.")
    return product

@app.put("/products/{product_id}", response_model=ProductResponse, summary="Update an existing product")
def update_product(
    product_id: int, updated: ProductUpdate, db: Session = Depends(get_db)
):
    """
    Updates existing product information in the database.
    
    - Takes a `ProductUpdate` schema, allowing only specified fields to be updated.
    - Returns the updated product's details.
    - Raises a 404 HTTP exception if the product does not exist.
    """
    logging.info(f"Updating product with ID: {product_id} with data: {updated.model_dump(exclude_unset=True)}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logging.warning(f"Product with ID: {product_id} not found for update.")
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Iterate over fields in the updated schema that were actually provided
    for field, value in updated.dict(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    logging.info(f"Product '{product.name}' (ID: {product_id}) updated successfully.")
    return product

@app.delete("/products/{product_id}", status_code=204, summary="Delete a product by ID")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Deletes a product from the database by its unique ID.
    
    - Returns a 204 No Content status code upon successful deletion.
    - Raises a 404 HTTP exception if the product does not exist.
    """
    logging.info(f"Attempting to delete product with ID: {product_id}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logging.warning(f"Product with ID: {product_id} not found for deletion.")
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    logging.info(f"Product (ID: {product_id}) deleted successfully.")
    return {"detail": "Product deleted successfully"}

# -----------------------------
# Stock Management Endpoint
# -----------------------------

@app.put("/products/{product_id}/stock", response_model=ProductResponse, summary="Update stock quantity for a product")
def update_stock(
    product_id: int,
    stock_quantity: int = Query(..., ge=0, description="New stock quantity for the product. Must be non-negative."),
    db: Session = Depends(get_db)
):
    """
    Updates the stock quantity of a specific product.
    
    - Takes the product ID and the new `stock_quantity` as a query parameter.
    - Logs a warning message if the stock quantity falls below the predefined `RESTOCK_THRESHOLD`.
    - Returns the updated product's details.
    - Raises a 404 HTTP exception if the product does not exist.
    """
    logging.info(f"Updating stock for product ID: {product_id} to {stock_quantity}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logging.warning(f"Product with ID: {product_id} not found for stock update.")
        raise HTTPException(status_code=404, detail="Product not found")
    product.stock_quantity = stock_quantity
    db.commit()
    db.refresh(product)
    
    if product.stock_quantity < RESTOCK_THRESHOLD:
        logging.info(
            f"ALERT: Restock needed for product '{product.name}' (ID: {product.product_id}): "
            f"only {product.stock_quantity} units left. Threshold is {RESTOCK_THRESHOLD}."
        )
    logging.info(f"Stock for product '{product.name}' (ID: {product.product_id}) updated to {product.stock_quantity}.")
    return product
