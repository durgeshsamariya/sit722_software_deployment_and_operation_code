# app/main.py

"""
FastAPI Product Service with image upload, CRUD, validation, and stock management.

This service manages product data, including creation, retrieval, updates, and deletion.
It supports image uploads to Azure Blob Storage and provides API endpoints
for comprehensive product management in a mini-ecommerce application.
"""

from fastapi import (
    FastAPI, Depends, HTTPException, Query, File, UploadFile, Form, status
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError # For more specific database error handling
import logging

from db import Base, engine, get_db
from models import Product
from schemas import ProductCreate, ProductUpdate, ProductResponse
from azure_utils import upload_to_azure_blob

from typing import Optional

# --- Logging Configuration ---
# Set up basic logging for the application.
# INFO level messages and above will be displayed, formatted with timestamp, logger name, level, and message.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Get a logger instance for this module

# --- Application Constants ---
# Define a threshold for product stock to trigger a restock notification.
RESTOCK_THRESHOLD = 5

# --- Database Initialization ---
# Create database tables defined in models.py.
# This ensures that tables exist when the application starts.
# In a production environment, database migrations (e.g., using Alembic) are typically used for schema management.
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title="Product Service API",
    description="""
    This API provides comprehensive product management functionalities for a mini-ecommerce application.
    It supports:
    - **Creating, reading, updating, and deleting** product records.
    - Managing product **stock quantities**.
    - Uploading product **images to Azure Blob Storage**.
    - **Pagination and search** capabilities for product listings.
    """,
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

@app.post(
    "/products/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="""
    Creates a new product record in the database, optionally uploading an image
    to Azure Blob Storage if provided. Returns the newly created product details.
    """
)
async def create_product(
    name: str = Form(..., min_length=1, max_length=255, description="Name of the product (1-255 chars)."),
    description: Optional[str] = Form(None, max_length=2000, description="Detailed description of the product (max 2000 chars)."),
    price: float = Form(..., gt=0, description="Price of the product (must be positive)."),
    stock_quantity: int = Form(..., ge=0, description="Current stock quantity (non-negative)."),
    image: Optional[UploadFile] = File(None, description="Optional image file to upload for the product."),
    db: Session = Depends(get_db) # Dependency to get database session
):
    """
    Handles the creation of a new product record.

    If an `image` file is provided, it's uploaded to Azure Blob Storage, and its URL
    is stored with the product. Logs successful creation or errors.
    """
    logger.info(f"Attempting to create a new product: {name}")
    image_url = None
    if image and image.filename:
        try:
            image_url = await upload_to_azure_blob(image)
            logger.info(f"Image '{image.filename}' uploaded to Azure. URL: {image_url}")
        except Exception as e:
            # If image upload fails, log the error and return a 500 Internal Server Error.
            logger.error(f"Failed to upload image for product '{name}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not upload product image: {e}"
            )

    # Create a new Product ORM object using the validated data.
    db_product = Product(
        name=name,
        description=description,
        price=price,
        stock_quantity=stock_quantity,
        image_url=image_url
    )
    
    try:
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        logger.info(f"Product '{db_product.name}' (ID: {db_product.product_id}) created successfully.")
    except SQLAlchemyError as e:
        # If a database error occurs, rollback the session to prevent partial commits.
        db.rollback()
        logger.error(f"Database error while creating product '{name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while creating the product."
        )
    return db_product

@app.get(
    "/products/",
    response_model=list[ProductResponse],
    summary="List all products",
    description="""
    Retrieves a list of all products from the database.
    Supports **pagination** (using `skip` and `limit`) and an optional **search query**
    to filter products by name or description.
    """
)
def list_products(
    db: Session = Depends(get_db), # Dependency to get database session
    skip: int = Query(0, ge=0, description="Number of items to skip (for pagination)."),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of items to return (for pagination, max 100)."),
    search: Optional[str] = Query(
        None,
        max_length=255,
        description="Search term to filter products by name or description (case-insensitive)."
    )
):
    """
    Retrieves a paginated and optionally filtered list of products.

    Products can be searched by `name` or `description` (case-insensitive).
    """
    logger.info(f"Listing products with skip={skip}, limit={limit}, search='{search}'")
    query = db.query(Product)
    # Apply search filter if a search term is provided.
    if search:
        search_pattern = f"%{search}%" # Wildcard pattern for SQL LIKE
        query = query.filter(
            (Product.name.ilike(search_pattern)) |  # Case-insensitive search on product name
            (Product.description.ilike(search_pattern)) # Case-insensitive search on product description
        )

    # Apply pagination using offset and limit.
    products = query.offset(skip).limit(limit).all()
    logger.info(f"Retrieved {len(products)} products.")
    return products

@app.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
    description="Retrieves a single product's details using its unique product ID."
    )
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Retrieves details of a single product specified by its ID.

    Raises a 404 HTTPException if the product is not found.
    """
    logger.info(f"Attempting to retrieve product with ID: {product_id}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(f"Product with ID {product_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    logger.info(f"Successfully retrieved product '{product.name}' (ID: {product_id}).")
    return product

@app.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update an existing product",
    description="""
    Updates details of an existing product. Only fields that are provided
    in the request body will be updated. Supports optional image upload,
    which replaces any existing image.
    """
)
async def update_product(
    product_id: int,
    name: Optional[str] = Form(None, min_length=1, max_length=255, description="New name for the product."),
    description: Optional[str] = Form(None, max_length=2000, description="New description for the product."),
    price: Optional[float] = Form(None, gt=0, description="New price for the product (must be positive)."),
    stock_quantity: Optional[int] = Form(None, ge=0, description="New stock quantity (non-negative)."),
    image: Optional[UploadFile] = File(None, description="New image file to replace the current one."),
    db: Session = Depends(get_db)
):
    """
    Updates an existing product's details based on its ID.

    Allows partial updates: only the fields provided in the form data will be changed.
    If a new `image` is provided, it replaces the existing product image in Azure Blob Storage.
    """
    logger.info(f"Attempting to update product with ID: {product_id}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(f"Attempted to update non-existent product with ID {product_id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )

    updated_fields_count = 0 # Track how many fields were successfully updated
    if name is not None:
        product.name = name
        updated_fields_count += 1
    if description is not None:
        product.description = description
        updated_fields_count += 1
    if price is not None:
        product.price = price
        updated_fields_count += 1
    if stock_quantity is not None:
        product.stock_quantity = stock_quantity
        updated_fields_count += 1
    if image and image.filename:
        try:
            # Upload the new image and update the product's image URL.
            new_image_url = await upload_to_azure_blob(image)
            product.image_url = new_image_url
            updated_fields_count += 1
            logger.info(f"Image for product {product_id} updated. New URL: {new_image_url}")
        except Exception as e:
            # Log error and return a 500 Internal Server Error if image upload fails.
            logger.error(f"Failed to upload new image for product {product_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not upload new product image: {e}"
            )

    if updated_fields_count > 0:
        try:
            db.commit()
            db.refresh(product)
            logger.info(f"Product {product_id} updated successfully. Total fields modified: {updated_fields_count}.")
        except SQLAlchemyError as e:
            db.rollback() # Rollback changes in case of a database error
            logger.error(f"Database error while updating product {product_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while updating the product."
            )
    else:
        logger.info(f"No fields provided for update for product {product_id}. No changes were committed to the database.")
    return product

@app.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
    description="Deletes a product record from the database using its unique product ID."
)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Deletes a product specified by its ID from the database.

    Raises a 404 HTTPException if the product is not found.
    Returns a 204 No Content status upon successful deletion.
    """
    
    logger.info(f"Attempting to delete product with ID: {product_id}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(f"Attempted to delete non-existent product with ID {product_id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    try:
        db.delete(product)
        db.commit()
        logger.info(f"Product '{product.name}' (ID: {product_id}) deleted successfully.")
    except SQLAlchemyError as e:
        db.rollback() # Rollback in case of database error
        logger.error(f"Database error while deleting product {product_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while deleting the product."
        )
    # FastAPI automatically handles the 204 No Content response correctly when status_code is set.
    return {"detail": "Product deleted successfully"}

@app.put(
    "/products/{product_id}/stock",
    response_model=ProductResponse,
    summary="Update product stock quantity",
    description="Updates only the stock quantity for a specific product."
)
def update_stock(
    product_id: int,
    stock_quantity: int = Query(..., ge=0),
    db: Session = Depends(get_db)
):
    """
    Updates the stock quantity of a specific product by its ID.

    Logs a restock alert if the new stock quantity falls below a predefined threshold.
    Raises a 404 HTTPException if the product is not found.
    """
    logger.info(f"Attempting to update stock for product ID: {product_id} to {stock_quantity}")

    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(f"Attempted to update stock for non-existent product with ID {product_id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found"
        )
    
    old_stock = product.stock_quantity # Store old stock for logging
    product.stock_quantity = stock_quantity # Update the stock quantity
    
    try:
        db.commit() # Commit the change to the database
        db.refresh(product) # Refresh to get the latest state from DB, including updated_at
        logger.info(f"Product '{product.name}' (ID: {product_id}) stock updated from {old_stock} to {product.stock_quantity}.")
        
        # Check and log if restock is needed after the update.
        if product.stock_quantity < RESTOCK_THRESHOLD:
            logger.info(
                f"RESTOCK ALERT: Product '{product.name}' (ID: {product_id}) "
                f"stock is low: {product.stock_quantity} units left. Restock needed!"
            )
    except SQLAlchemyError as e:
        db.rollback() # Rollback changes in case of a database error
        logger.error(f"Database error while updating stock for product {product_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while updating stock."
        )
    return product
