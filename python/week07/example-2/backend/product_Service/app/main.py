# week07/example-2/backend/product_service/app/main.py

import logging
import os
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from urllib.parse import urlparse

# Azure Storage Imports
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
)
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
    Request, # Import Request for middleware
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# --- Prometheus client imports ---
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client.core import CollectorRegistry
from starlette.responses import PlainTextResponse

from .db import Base, engine, get_db
from .models import Product
from .schemas import ProductCreate, ProductResponse, ProductUpdate, StockDeductRequest

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


RESTOCK_THRESHOLD = 5  # Threshold for restock notification

# --- Prometheus Metrics Initialization ---
# Create a custom registry specific to this application instance
registry = CollectorRegistry()
APP_NAME = "product_service" # Unique identifier for this service in metrics

# Define Prometheus metrics
# Counter: Total HTTP requests
REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP requests processed by the application',
    ['app_name', 'method', 'endpoint', 'status_code'], registry=registry
)
# Histogram: Measures duration of HTTP requests (latency)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds', 'HTTP request duration in seconds',
    ['app_name', 'method', 'endpoint', 'status_code'], registry=registry
)
# Gauge: Number of concurrent HTTP requests currently in progress
REQUESTS_IN_PROGRESS = Gauge(
    'http_requests_in_progress', 'Number of HTTP requests in progress',
    ['app_name', 'method', 'endpoint'], registry=registry
)

# Custom Metrics specific to Product Service business logic
PRODUCT_CREATION_TOTAL = Counter(
    'product_creation_total', 'Total number of products created',
    ['app_name', 'status'], registry=registry
)
PRODUCT_UPDATE_TOTAL = Counter(
    'product_update_total', 'Total number of products updated',
    ['app_name', 'status'], registry=registry
)
PRODUCT_DELETION_TOTAL = Counter(
    'product_deletion_total', 'Total number of products deleted',
    ['app_name', 'status'], registry=registry
)
STOCK_DEDUCTION_TOTAL = Counter(
    'stock_deduction_total', 'Total stock deduction attempts',
    ['app_name', 'product_id', 'status'], registry=registry
)
STOCK_LEVEL_GAUGE = Gauge(
    'product_stock_quantity', 'Current stock quantity of a product',
    ['app_name', 'product_id', 'product_name'], registry=registry
)
IMAGE_UPLOAD_TOTAL = Counter(
    'product_image_upload_total', 'Total product image upload attempts',
    ['app_name', 'product_id', 'status'], registry=registry
)
LOW_STOCK_ALERTS_TOTAL = Counter(
    'low_stock_alerts_total', 'Total alerts triggered for low stock',
    ['app_name', 'product_id', 'product_name'], registry=registry
)


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

# --- Middleware for Prometheus Metrics ---
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # Exclude the /metrics endpoint itself from being tracked
    if request.url.path == "/metrics":
        response = await call_next(request)
        return response

    method = request.method
    endpoint = request.url.path

    # Increment requests in progress
    REQUESTS_IN_PROGRESS.labels(app_name=APP_NAME, method=method, endpoint=endpoint).inc()
    start_time = time.time()

    response = await call_next(request) # Process the actual request

    process_time = time.time() - start_time
    status_code = response.status_code

    # Decrement requests in progress
    REQUESTS_IN_PROGRESS.labels(app_name=APP_NAME, method=method, endpoint=endpoint).dec()
    # Increment total requests
    REQUEST_COUNT.labels(app_name=APP_NAME, method=method, endpoint=endpoint, status_code=status_code).inc()
    # Observe duration for request latency
    REQUEST_DURATION.labels(app_name=APP_NAME, method=method, endpoint=endpoint, status_code=status_code).observe(process_time)

    return response

# --- Prometheus Metrics Endpoint ---
# This is the endpoint Prometheus will scrape to collect metrics.
@app.get("/metrics", response_class=PlainTextResponse, summary="Prometheus metrics endpoint")
async def metrics():
    # generate_latest collects all metrics from the registry and formats them for Prometheus
    return PlainTextResponse(generate_latest(registry))


# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
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
            
            # Initial population of stock levels into Prometheus Gauge
            db = next(get_db()) # Get a session for initial load
            products = db.query(Product).all()
            for product in products:
                STOCK_LEVEL_GAUGE.labels(app_name=APP_NAME, product_id=product.product_id, product_name=product.name).set(product.stock_quantity)
            db.close() # Close the session
            logger.info("Product Service: Initial product stock levels loaded into Prometheus.")

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
    return {"message": "Welcome to the Product Service!"}


# --- Health Check Endpoint ---
@app.get("/health", status_code=status.HTTP_200_OK, summary="Health check endpoint")
async def health_check():
    return {"status": "ok", "service": "product-service"}


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
        PRODUCT_CREATION_TOTAL.labels(app_name=APP_NAME, status="success").inc()
        # Update stock gauge for newly created product
        STOCK_LEVEL_GAUGE.labels(app_name=APP_NAME, product_id=db_product.product_id, product_name=db_product.name).set(db_product.stock_quantity)
        return db_product
    except Exception as e:
        db.rollback()
        logger.error(f"Product Service: Error creating product: {e}", exc_info=True)
        PRODUCT_CREATION_TOTAL.labels(app_name=APP_NAME, status="failure").inc()
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

    # Update stock gauge for all products (could be heavy on large datasets, consider only updating on change)
    # For now, we'll update all for consistency after a list request
    for product in products:
        STOCK_LEVEL_GAUGE.labels(app_name=APP_NAME, product_id=product.product_id, product_name=product.name).set(product.stock_quantity)

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
    logger.info(f"Product Service: Fetching product with ID: {product_id}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(f"Product Service: Product with ID {product_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    logger.info(
        f"Product Service: Retrieved product with ID {product_id}. Name: {product.name}"
    )
    # Update stock gauge for the retrieved product
    STOCK_LEVEL_GAUGE.labels(app_name=APP_NAME, product_id=product.product_id, product_name=product.name).set(product.stock_quantity)
    return product


@app.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update an existing product by ID",
)
async def update_product(
    product_id: int, product: ProductUpdate, db: Session = Depends(get_db)
):
    logger.info(
        f"Product Service: Updating product with ID: {product_id} with data: {product.model_dump(exclude_unset=True)}"
    )
    db_product = db.query(Product).filter(Product.product_id == product_id).first()
    if not db_product:
        logger.warning(
            f"Product Service: Attempted to update non-existent product with ID {product_id}."
        )
        PRODUCT_UPDATE_TOTAL.labels(app_name=APP_NAME, status="not_found").inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Check if stock_quantity is being updated and needs special handling for gauge
    old_stock_quantity = db_product.stock_quantity
    
    update_data = product.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)

    try:
        db.add(db_product)  # Mark for update
        db.commit()
        db.refresh(db_product)
        logger.info(f"Product Service: Product {product_id} updated successfully.")
        PRODUCT_UPDATE_TOTAL.labels(app_name=APP_NAME, status="success").inc()
        
        # Update stock gauge if stock quantity changed
        if db_product.stock_quantity != old_stock_quantity:
            STOCK_LEVEL_GAUGE.labels(app_name=APP_NAME, product_id=db_product.product_id, product_name=db_product.name).set(db_product.stock_quantity)
            logger.info(f"Product Service: Stock level for {db_product.name} (ID: {db_product.product_id}) updated to {db_product.stock_quantity}.")
            # Check for low stock after update
            if db_product.stock_quantity < RESTOCK_THRESHOLD:
                logger.warning(
                    f"Product Service: ALERT! Stock for product '{db_product.name}' (ID: {db_product.product_id}) is low: {db_product.stock_quantity}."
                )
                LOW_STOCK_ALERTS_TOTAL.labels(app_name=APP_NAME, product_id=db_product.product_id, product_name=db_product.name).inc()
        
        return db_product
    except Exception as e:
        db.rollback()
        logger.error(
            f"Product Service: Error updating product {product_id}: {e}", exc_info=True
        )
        PRODUCT_UPDATE_TOTAL.labels(app_name=APP_NAME, status="failure").inc()
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
        PRODUCT_DELETION_TOTAL.labels(app_name=APP_NAME, status="not_found").inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    try:
        db.delete(product)
        db.commit()
        logger.info(
            f"Product Service: Product {product_id} deleted successfully. Name: {product.name}"
        )
        PRODUCT_DELETION_TOTAL.labels(app_name=APP_NAME, status="success").inc()
        # Remove product from stock gauge (set to 0 or remove if product_id is dynamic)
        # Setting to 0 might be better to see it in Grafana
        STOCK_LEVEL_GAUGE.labels(app_name=APP_NAME, product_id=product.product_id, product_name=product.name).set(0) # Or remove using registry.unregister if product_id is removed from system forever.
    except Exception as e:
        db.rollback()
        logger.error(
            f"Product Service: Error deleting product {product_id}: {e}", exc_info=True
        )
        PRODUCT_DELETION_TOTAL.labels(app_name=APP_NAME, status="failure").inc()
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
        IMAGE_UPLOAD_TOTAL.labels(app_name=APP_NAME, product_id=product_id, status="storage_not_configured").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure Blob Storage is not configured or available.",
        )

    db_product = db.query(Product).filter(Product.product_id == product_id).first()
    if not db_product:
        logger.warning(
            f"Product Service: Product with ID {product_id} not found for image upload."
        )
        IMAGE_UPLOAD_TOTAL.labels(app_name=APP_NAME, product_id=product_id, status="product_not_found").inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Basic file type validation
    allowed_content_types = ["image/jpeg", "image/png", "image/gif"]
    if file.content_type not in allowed_content_types:
        IMAGE_UPLOAD_TOTAL.labels(app_name=APP_NAME, product_id=product_id, status="invalid_file_type").inc()
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
        blob_name = f"product-{product_id}-{timestamp}{file_extension}" # Ensure blob name is unique and tied to product

        blob_client = blob_service_client.get_blob_client(
            container=AZURE_STORAGE_CONTAINER_NAME, blob=blob_name
        )

        logger.info(
            f"Product Service: Uploading image '{file.filename}' for product {product_id} as '{blob_name}' to Azure."
        )

        # Upload the file content directly
        file_content = await file.read() # Read file content once
        blob_client.upload_blob(
            file_content, # Pass bytes directly
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type),
        )

        # Generate Shared Access Signature (SAS) for public read access
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
        IMAGE_UPLOAD_TOTAL.labels(app_name=APP_NAME, product_id=product_id, status="success").inc()
        return db_product

    except Exception as e:
        db.rollback()
        logger.error(
            f"Product Service: Error uploading image for product {product_id}: {e}",
            exc_info=True,
        )
        IMAGE_UPLOAD_TOTAL.labels(app_name=APP_NAME, product_id=product_id, status="failure").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not upload image or update product: {e}",
        )


# --- Endpoint for Stock Deduction ---
@app.patch(
    "/products/{product_id}/deduct-stock",
    response_model=ProductResponse,
    summary="Deduct stock quantity for a product",
)
async def deduct_product_stock(
    product_id: int, request: StockDeductRequest, db: Session = Depends(get_db)
):
    """
    Deducts a specified quantity from a product's stock.
    Returns 404 if product not found, 400 if insufficient stock.
    """
    logger.info(
        f"Product Service: Attempting to deduct {request.quantity_to_deduct} from stock for product ID: {product_id}"
    )
    db_product = db.query(Product).filter(Product.product_id == product_id).first()

    if not db_product:
        logger.warning(
            f"Product Service: Stock deduction failed: Product with ID {product_id} not found."
        )
        STOCK_DEDUCTION_TOTAL.labels(app_name=APP_NAME, product_id=product_id, status="product_not_found").inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    if db_product.stock_quantity < request.quantity_to_deduct:
        logger.warning(
            f"Product Service: Stock deduction failed for product {product_id}. Insufficient stock: {db_product.stock_quantity} available, {request.quantity_to_deduct} requested."
        )
        STOCK_DEDUCTION_TOTAL.labels(app_name=APP_NAME, product_id=product_id, status="insufficient_stock").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock for product '{db_product.name}'. Only {db_product.stock_quantity} available.",
        )

    # Perform deduction
    db_product.stock_quantity -= request.quantity_to_deduct

    try:
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        logger.info(
            f"Product Service: Stock for product {product_id} updated to {db_product.stock_quantity}. Deducted {request.quantity_to_deduct}."
        )
        STOCK_DEDUCTION_TOTAL.labels(app_name=APP_NAME, product_id=product_id, status="success").inc()
        # Update stock gauge
        STOCK_LEVEL_GAUGE.labels(app_name=APP_NAME, product_id=db_product.product_id, product_name=db_product.name).set(db_product.stock_quantity)

        # Optional: Log or trigger alert if stock falls below threshold
        if db_product.stock_quantity < RESTOCK_THRESHOLD:
            logger.warning(
                f"Product Service: ALERT! Stock for product '{db_product.name}' (ID: {db_product.product_id}) is low: {db_product.stock_quantity}."
            )
            LOW_STOCK_ALERTS_TOTAL.labels(app_name=APP_NAME, product_id=db_product.product_id, product_name=db_product.name).inc()

        return db_product
    except Exception as e:
        db.rollback()
        logger.error(
            f"Product Service: Error deducting stock for product {product_id}: {e}",
            exc_info=True,
        )
        STOCK_DEDUCTION_TOTAL.labels(app_name=APP_NAME, product_id=product_id, status="failure").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not deduct stock.",
        )


# --- Endpoint for Adding Stock ---
@app.patch(
    "/products/{product_id}/add-stock",
    response_model=ProductResponse,
    summary="Add stock quantity for a product",
)
async def add_product_stock(
    product_id: int, request: StockDeductRequest, db: Session = Depends(get_db) # Reusing StockDeductRequest for quantity
):
    """
    Adds a specified quantity to a product's stock.
    Returns 404 if product not found.
    """
    logger.info(
        f"Product Service: Attempting to add {request.quantity_to_deduct} to stock for product ID: {product_id}"
    )
    db_product = db.query(Product).filter(Product.product_id == product_id).first()

    if not db_product:
        logger.warning(
            f"Product Service: Add stock failed: Product with ID {product_id} not found."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Perform addition
    db_product.stock_quantity += request.quantity_to_deduct

    try:
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        logger.info(
            f"Product Service: Stock for product {product_id} updated to {db_product.stock_quantity}. Added {request.quantity_to_deduct}."
        )
        # Update stock gauge
        STOCK_LEVEL_GAUGE.labels(app_name=APP_NAME, product_id=db_product.product_id, product_name=db_product.name).set(db_product.stock_quantity)

        return db_product
    except Exception as e:
        db.rollback()
        logger.error(
            f"Product Service: Error adding stock for product {product_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add stock.",
        )