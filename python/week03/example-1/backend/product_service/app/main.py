# week03/example-1/backend/product_service/app/main.py

import logging
import os
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

# Azure Storage Imports
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
)
from dotenv import load_dotenv  # For loading credentials from .env file
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Product
from .schemas import ProductCreate, ProductResponse, ProductUpdate

# --- Standard Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Suppress noisy logs from third-party libraries for cleaner output
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)


# --- Azure Blob Storage Configuration ---
# Load environment variables from .env file (for local development)
load_dotenv()

AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_STORAGE_CONTAINER_NAME = os.getenv(
    "AZURE_STORAGE_CONTAINER_NAME", "product-images"
)
AZURE_SAS_TOKEN_EXPIRY_HOURS = int(os.getenv("AZURE_SAS_TOKEN_EXPIRY_HOURS", "24"))

# Initialize BlobServiceClient
if AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY:
    try:
        blob_service_client = BlobServiceClient(
            account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=AZURE_STORAGE_ACCOUNT_KEY,
        )
        logger.info("Product Service: Azure BlobServiceClient initialized.")
        # Ensure the container exists
        try:
            container_client = blob_service_client.get_container_client(
                AZURE_STORAGE_CONTAINER_NAME
            )
            container_client.create_container()
            logger.info(
                f"Product Service: Azure container '{AZURE_STORAGE_CONTAINER_NAME}' ensured to exist."
            )
        except Exception as e:
            logger.warning(
                f"Product Service: Could not create or verify Azure container '{AZURE_STORAGE_CONTAINER_NAME}'. It might already exist. Error: {e}"
            )
    except Exception as e:
        logger.critical(
            f"Product Service: Failed to initialize Azure BlobServiceClient. Check credentials and account name. Error: {e}",
            exc_info=True,
        )
        blob_service_client = None  # Set to None if initialization fails
else:
    logger.warning(
        "Product Service: Azure Storage credentials not found. Image upload functionality will be disabled."
    )
    blob_service_client = None

# Threshold for restock notification
RESTOCK_THRESHOLD = 5

# --- FastAPI Application Setup ---
app = FastAPI(
    title="Product Service API",
    description="Manages products and stock for mini-ecommerce app, with Azure Storage integration.",
    version="1.0.0",
)

# Enable CORS (for frontend dev/testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    """
    Handles application startup events.
    Ensures database tables are created (if not exist) for the Product Service.
    Includes a retry mechanism for database connection robustness.
    """
    max_retries = 10
    retry_delay_seconds = 5
    for i in range(max_retries):
        try:
            logger.info(
                f"Product Service: Attempting to connect to PostgreSQL and create tables (attempt {i+1}/{max_retries})..."
            )
            Base.metadata.create_all(bind=engine)
            logger.info(
                "Product Service: Successfully connected to PostgreSQL and ensured tables exist."
            )
            break  # Exit loop if successful
        except OperationalError as e:
            logger.warning(f"Product Service: Failed to connect to PostgreSQL: {e}")
            if i < max_retries - 1:
                logger.info(
                    f"Product Service: Retrying in {retry_delay_seconds} seconds..."
                )
                time.sleep(retry_delay_seconds)
            else:
                logger.critical(
                    f"Product Service: Failed to connect to PostgreSQL after {max_retries} attempts. Exiting application."
                )
                sys.exit(1)  # Critical failure: exit if DB connection is unavailable
        except Exception as e:
            logger.critical(
                f"Product Service: An unexpected error occurred during database startup: {e}",
                exc_info=True,
            )
            sys.exit(1)


# --- Root Endpoint ---
@app.get("/", status_code=status.HTTP_200_OK, summary="Root endpoint")
async def read_root():
    """
    Returns a welcome message for the Product Service.
    """
    return {"message": "Welcome to the Product Service!"}


# --- Health Check Endpoint ---
@app.get("/health", status_code=status.HTTP_200_OK, summary="Health check endpoint")
async def health_check():
    """
    A simple health check endpoint to verify the service is running.
    Returns 200 OK if the service is alive.
    """
    return {"status": "ok", "service": "product-service"}


# --- CRUD Endpoints ---


@app.post(
    "/products/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Creates a new product in the database.
    """
    logger.info(f"Product Service: Creating product: {product.name}")
    try:
        db_product = Product(**product.model_dump())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        logger.info(
            f"Product Service: Product '{db_product.name}' (ID: {db_product.product_id}) created successfully."
        )
        return db_product
    except Exception as e:
        db.rollback()
        logger.error(f"Product Service: Error creating product: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create product.",
        )


@app.get(
    "/products/",
    response_model=List[ProductResponse],
    summary="Retrieve a list of all products",
)
def list_products(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=255),
):
    """
    Lists products with optional pagination and search by name/description.
    """
    logger.info(
        f"Product Service: Listing products with skip={skip}, limit={limit}, search='{search}'"
    )
    query = db.query(Product)
    if search:
        search_pattern = f"%{search}%"
        logger.info(f"Product Service: Applying search filter for term: {search}")
        query = query.filter(
            (Product.name.ilike(search_pattern))
            | (Product.description.ilike(search_pattern))
        )
    products = query.offset(skip).limit(limit).all()

    logger.info(
        f"Product Service: Retrieved {len(products)} products (skip={skip}, limit={limit})."
    )
    return products


@app.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Retrieve a single product by ID",
)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Retrieves details for a specific product using its unique ID.
    Generates a SAS token for the image_url if one exists and Azure Storage is configured.
    """
    logger.info(f"Product Service: Fetching product with ID: {product_id}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(f"Product Service: Product with ID {product_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Generate SAS token for the image URL if it exists
    if product.image_url and AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY:
        try:
            if blob_service_client:  # Check if blob service client is initialized
                parts = product.image_url.split("/")
                blob_name = "/".join(parts[5:]).split("?")[0]

                sas_token = generate_blob_sas(
                    account_name=AZURE_STORAGE_ACCOUNT_NAME,
                    account_key=AZURE_STORAGE_ACCOUNT_KEY,
                    container_name=AZURE_STORAGE_CONTAINER_NAME,
                    blob_name=blob_name,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow()
                    + timedelta(hours=AZURE_SAS_TOKEN_EXPIRY_HOURS),
                )
                product.image_url = f"{blob_service_client.get_blob_client(AZURE_STORAGE_CONTAINER_NAME, blob_name).url}?{sas_token}"
        except Exception as e:
            logger.error(
                f"Product Service: Error generating SAS token for product {product.product_id}: {e}",
                exc_info=True,
            )
            # Optionally, set image_url to None or a placeholder if SAS generation fails

    logger.info(
        f"Product Service: Retrieved product with ID {product_id}. Name: {product.name}"
    )
    return product


@app.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update an existing product by ID",
)
async def update_product(
    product_id: int, product: ProductUpdate, db: Session = Depends(get_db)
):
    """
    Updates an existing product's details. Only provided fields will be updated.
    If image_url is provided, it will be stored directly.
    """
    logger.info(
        f"Product Service: Updating product with ID: {product_id} with data: {product.model_dump(exclude_unset=True)}"
    )
    db_product = db.query(Product).filter(Product.product_id == product_id).first()
    if not db_product:
        logger.warning(
            f"Product Service: Attempted to update non-existent product with ID {product_id}."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    update_data = product.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    try:
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        logger.info(f"Product Service: Product {product_id} updated successfully.")
        return db_product
    except Exception as e:
        db.rollback()
        logger.error(
            f"Product Service: Error updating product {product_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update product.",
        )


@app.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product by ID",
)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Deletes a product record from the database.
    Does NOT delete the image from Azure Blob Storage.
    """
    logger.info(f"Product Service: Attempting to delete product with ID: {product_id}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(
            f"Product Service: Attempted to delete non-existent product with ID {product_id}."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    try:
        db.delete(product)
        db.commit()
        logger.info(
            f"Product Service: Product {product_id} deleted successfully. Name: {product.name}"
        )
    except Exception as e:
        db.rollback()
        logger.error(
            f"Product Service: Error deleting product {product_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the product.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/products/{product_id}/upload-image",
    response_model=ProductResponse,
    summary="Upload an image for a product to Azure Blob Storage",
)
async def upload_product_image(
    product_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """
    Uploads an image file to Azure Blob Storage and updates the product's image_url in the database.
    Generates a SAS token for the image URL with a defined expiry.
    Only supports image file types.
    """
    if not blob_service_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure Blob Storage is not configured or available.",
        )

    db_product = db.query(Product).filter(Product.product_id == product_id).first()
    if not db_product:
        logger.warning(
            f"Product Service: Product with ID {product_id} not found for image upload."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Basic file type validation
    allowed_content_types = ["image/jpeg", "image/png", "image/gif"]
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only {', '.join(allowed_content_types)} are allowed.",
        )

    try:
        # Create a unique blob name (e.g., product_id/timestamp_originalfilename.ext)
        file_extension = (
            os.path.splitext(file.filename)[1]
            if os.path.splitext(file.filename)[1]
            else ".jpg"
        )  # Ensure extension
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        blob_name = f"{timestamp}{file_extension}"

        blob_client = blob_service_client.get_blob_client(
            container=AZURE_STORAGE_CONTAINER_NAME, blob=blob_name
        )

        logger.info(
            f"Product Service: Uploading image '{file.filename}' for product {product_id} as '{blob_name}' to Azure."
        )

        # Upload the file content directly
        # Use stream=True for large files
        blob_client.upload_blob(
            file.file,
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type),
        )

        # Generate Shared Access Signature (SAS) for public read access
        # SAS will expire after AZURE_SAS_TOKEN_EXPIRY_HOURS
        sas_token = generate_blob_sas(
            account_name=AZURE_STORAGE_ACCOUNT_NAME,
            account_key=AZURE_STORAGE_ACCOUNT_KEY,
            container_name=AZURE_STORAGE_CONTAINER_NAME,
            blob_name=blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=AZURE_SAS_TOKEN_EXPIRY_HOURS),
        )
        # Construct the full URL with SAS token
        image_url = f"{blob_client.url}?{sas_token}"

        # Update the product in the database with the image URL (including SAS token)
        db_product.image_url = image_url
        db.add(db_product)
        db.commit()
        db.refresh(db_product)

        logger.info(
            f"Product Service: Image uploaded and product {product_id} updated with SAS URL: {image_url}"
        )
        return db_product

    except Exception as e:
        db.rollback()
        logger.error(
            f"Product Service: Error uploading image for product {product_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not upload image or update product: {e}",
        )
