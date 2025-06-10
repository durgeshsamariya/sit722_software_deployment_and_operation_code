# week03/example-3/backend/product_service/app/main.py

"""
FastAPI Product Service API.
Manages product information including creation, retrieval, updates, deletion,
and stock management. Now includes support for photo uploads to Azure Blob Storage
with Shared Access Signatures (SAS) for secure access, and a new endpoint for stock deduction.
"""

import sys
import logging
import time
import os
import json
from typing import List, Optional
from decimal import Decimal
from urllib.parse import urlparse
import asyncio

from fastapi import (
    FastAPI, Depends, HTTPException, Query, File, UploadFile, Form, status, Response
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

# Azure Storage Imports
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas, ContentSettings
from datetime import datetime, timedelta
from dotenv import load_dotenv # For loading Azure credentials from .env file

from .db import Base, engine, get_db
from .models import Product
from .schemas import ProductCreate, ProductUpdate, ProductResponse, StockDeductRequest

import aio_pika

# --- Standard Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
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
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "product-images")
AZURE_SAS_TOKEN_EXPIRY_HOURS = int(os.getenv("AZURE_SAS_TOKEN_EXPIRY_HOURS", "24"))

blob_service_client: Optional[BlobServiceClient] = None

# Initialize BlobServiceClient
if AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY:
    try:
        blob_service_client = BlobServiceClient(
            account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=AZURE_STORAGE_ACCOUNT_KEY
        )
        logger.info("Product Service: Azure BlobServiceClient initialized.")
        # Ensure the container exists
        try:
            container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
            container_client.create_container()
            logger.info(f"Product Service: Azure container '{AZURE_STORAGE_CONTAINER_NAME}' ensured to exist.")
        except Exception as e:
            logger.warning(f"Product Service: Could not create or verify Azure container '{AZURE_STORAGE_CONTAINER_NAME}'. It might already exist. Error: {e}")
    except Exception as e:
        logger.critical(f"Product Service: Failed to initialize Azure BlobServiceClient. Check credentials and account name. Error: {e}", exc_info=True)
        blob_service_client = None # Set to None if initialization fails
else:
    logger.warning("Product Service: Azure Storage credentials not found. Image upload functionality will be disabled.")
    blob_service_client = None


RESTOCK_THRESHOLD = 5  # Threshold for restock notification

# --- RabbitMQ Configuration ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

# Global RabbitMQ connection and channel objects
rabbitmq_connection: Optional[aio_pika.Connection] = None
rabbitmq_channel: Optional[aio_pika.Channel] = None
rabbitmq_exchange: Optional[aio_pika.Exchange] = None

# --- FastAPI Application Setup ---
app = FastAPI(
    title="Product Service API",
    description="Manages products and stock for mini-ecommerce app, with Azure Storage integration.",
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

# --- RabbitMQ Helper Functions ---

async def connect_to_rabbitmq():
    """Establishes an asynchronous connection to RabbitMQ."""
    global rabbitmq_connection, rabbitmq_channel, rabbitmq_exchange
    
    rabbitmq_url = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
    max_retries = 10
    retry_delay_seconds = 5

    for i in range(max_retries):
        try:
            logger.info(f"Product Service: Attempting to connect to RabbitMQ (attempt {i+1}/{max_retries})...")
            rabbitmq_connection = await aio_pika.connect_robust(rabbitmq_url)
            rabbitmq_channel = await rabbitmq_connection.channel()
            # Declare a direct exchange for events
            rabbitmq_exchange = await rabbitmq_channel.declare_exchange('ecomm_events', aio_pika.ExchangeType.DIRECT, durable=True)
            logger.info("Product Service: Connected to RabbitMQ and declared 'ecomm_events' exchange.")
            return True
        except Exception as e:
            logger.warning(f"Product Service: Failed to connect to RabbitMQ: {e}")
            if i < max_retries - 1:
                await asyncio.sleep(retry_delay_seconds)
            else:
                logger.critical(f"Product Service: Failed to connect to RabbitMQ after {max_retries} attempts. RabbitMQ functionality will be limited.")
                return False
    return False

async def close_rabbitmq_connection():
    """Closes the RabbitMQ connection."""
    if rabbitmq_connection:
        logger.info("Product Service: Closing RabbitMQ connection.")
        await rabbitmq_connection.close()

async def publish_event(routing_key: str, message_data: dict):
    """Publishes a message to the RabbitMQ exchange."""
    if not rabbitmq_exchange:
        logger.error(f"Product Service: RabbitMQ exchange not available. Cannot publish event '{routing_key}'.")
        return
    try:
        message_body = json.dumps(message_data).encode('utf-8')
        message = aio_pika.Message(
            body=message_body,
            content_type='application/json',
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT # Make message persistent
        )
        await rabbitmq_exchange.publish(message, routing_key=routing_key)
        logger.info(f"Product Service: Published event '{routing_key}' with data: {message_data}")
    except Exception as e:
        logger.error(f"Product Service: Failed to publish event '{routing_key}': {e}", exc_info=True)

async def consume_order_placed_events(db_session: Session):
    """
    Consumes messages from the 'order.placed' queue and processes stock deductions.
    This function runs in a separate background task.
    """
    if not rabbitmq_channel or not rabbitmq_exchange:
        logger.error("Product Service: RabbitMQ channel or exchange not available for consuming order events.")
        return

    queue_name = 'product_service_order_placed_queue'
    order_placed_routing_key = 'order.placed'

    try:
        queue = await rabbitmq_channel.declare_queue(queue_name, durable=True)
        await queue.bind(rabbitmq_exchange, routing_key=order_placed_routing_key)
        logger.info(f"Product Service: Listening for '{order_placed_routing_key}' messages on queue '{queue_name}'.")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        message_data = json.loads(message.body.decode('utf-8'))
                        logger.info(f"Product Service: Received order.placed message: {message_data}")

                        order_id = message_data.get('order_id')
                        order_items = message_data.get('items', [])
                        
                        success = True
                        failed_products = []

                        # Create a new session for this background task
                        # (Important: Sessions are not thread-safe and should not be shared across async tasks/threads)
                        local_db_session = Session(bind=engine)
                        try:
                            for item in order_items:
                                product_id = item.get('product_id')
                                quantity = item.get('quantity')
                                if not product_id or not quantity:
                                    logger.error(f"Product Service: Invalid item data in message: {item}")
                                    success = False
                                    break

                                # Deduct stock
                                db_product = local_db_session.query(Product).filter(Product.product_id == product_id).first()

                                if not db_product:
                                    logger.warning(f"Product Service: Stock deduction failed for order {order_id}. Product {product_id} not found.")
                                    success = False
                                    failed_products.append({"product_id": product_id, "reason": "product_not_found"})
                                    break # Fail entire order deduction if a product is not found

                                if db_product.stock_quantity < quantity:
                                    logger.warning(f"Product Service: Stock deduction failed for order {order_id}. Insufficient stock for product {product_id}. Available: {db_product.stock_quantity}, Requested: {quantity}.")
                                    success = False
                                    failed_products.append({"product_id": product_id, "reason": "insufficient_stock", "available_stock": db_product.stock_quantity})
                                    break # Fail entire order deduction if stock is insufficient

                                db_product.stock_quantity -= quantity
                                local_db_session.add(db_product)
                                logger.info(f"Product Service: Deducted {quantity} from product {product_id} for order {order_id}. New stock: {db_product.stock_quantity}.")
                                
                                # Optional: Log or trigger alert if stock falls below threshold
                                if db_product.stock_quantity < RESTOCK_THRESHOLD:
                                    logger.warning(f"Product Service: ALERT! Stock for product '{db_product.name}' (ID: {db_product.product_id}) is low: {db_product.stock_quantity}.")


                            if success:
                                local_db_session.commit()
                                logger.info(f"Product Service: Successfully deducted stock for all items in order {order_id}. Publishing 'product.stock.deducted' event.")
                                await publish_event('product.stock.deducted', {
                                    "order_id": order_id,
                                    "status": "success",
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                            else:
                                local_db_session.rollback() # Rollback all changes if any item fails
                                logger.error(f"Product Service: Failed to deduct stock for order {order_id}. Rolling back. Publishing 'product.stock.deduction.failed' event.")
                                await publish_event('product.stock.deduction.failed', {
                                    "order_id": order_id,
                                    "status": "failed",
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "details": failed_products
                                })
                        except Exception as db_e:
                            local_db_session.rollback()
                            logger.critical(f"Product Service: Database error during stock deduction for order {order_id}: {db_e}", exc_info=True)
                            await publish_event('product.stock.deduction.failed', {
                                "order_id": order_id,
                                "status": "failed",
                                "timestamp": datetime.utcnow().isoformat(),
                                "details": [{"reason": "database_error", "message": str(db_e)}]
                            })
                        finally:
                            local_db_session.close()

                    except json.JSONDecodeError as e:
                        logger.error(f"Product Service: Failed to decode RabbitMQ message body: {e}. Message: {message.body}")
                    except Exception as e:
                        logger.error(f"Product Service: Unhandled error processing order.placed message: {e}", exc_info=True)
    except Exception as e:
        logger.critical(f"Product Service: Error in RabbitMQ consumer for order.placed events: {e}", exc_info=True)


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
            logger.info(f"Product Service: Attempting to connect to PostgreSQL and create tables (attempt {i+1}/{max_retries})...")
            Base.metadata.create_all(bind=engine)
            logger.info("Product Service: Successfully connected to PostgreSQL and ensured tables exist.")
            break # Exit loop if successful
        except OperationalError as e:
            logger.warning(f"Product Service: Failed to connect to PostgreSQL: {e}")
            if i < max_retries - 1:
                logger.info(f"Product Service: Retrying in {retry_delay_seconds} seconds...")
                time.sleep(retry_delay_seconds)
            else:
                logger.critical(f"Product Service: Failed to connect to PostgreSQL after {max_retries} attempts. Exiting application.")
                sys.exit(1) # Critical failure: exit if DB connection is unavailable
        except Exception as e:
            logger.critical(f"Product Service: An unexpected error occurred during database startup: {e}", exc_info=True)
            sys.exit(1)
    
    # Connect to RabbitMQ and start consumer
    if await connect_to_rabbitmq():
        # Start the consumer in a background task
        # We need a dummy db_session here for type hinting, but it's not used directly
        # in the consumer's connection setup
        asyncio.create_task(consume_order_placed_events(next(get_db())))
    else:
        logger.error("Product Service: RabbitMQ connection failed at startup. Async order processing will not work.")


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
    summary="Create a new product"
)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    """
    Creates a new product in the database.
    """
    logger.info(f"Product Service: Creating product: {product.name}")
    try:
        db_product = Product(**product.model_dump())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        logger.info(f"Product Service: Product '{db_product.name}' (ID: {db_product.product_id}) created successfully.")
        return db_product
    except IntegrityError:
        db.rollback()
        logger.warning(f"Product Service: Integrity error creating product: likely duplicate name or ID issue for product: {product.name}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product with this name might already exist or similar data integrity issue.")
    except Exception as e:
        db.rollback()
        logger.error(f"Product Service: Error creating product: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create product.")

@app.get(
    "/products/",
    response_model=List[ProductResponse],
    summary="Retrieve a list of all products"
)
def list_products(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=255)
):
    """
    Lists products with optional pagination and search by name/description.
    """
    logger.info(f"Product Service: Listing products with skip={skip}, limit={limit}, search='{search}'")
    query = db.query(Product)
    if search:
        search_pattern = f"%{search}%"
        logger.info(f"Product Service: Applying search filter for term: {search}")
        query = query.filter(
            (Product.name.ilike(search_pattern)) |
            (Product.description.ilike(search_pattern))
        )
    products = query.offset(skip).limit(limit).all()

    logger.info(f"Product Service: Retrieved {len(products)} products (skip={skip}, limit={limit}).")
    return products


@app.get("/products/{product_id}", response_model=ProductResponse, summary="Retrieve a single product by ID")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Retrieves details for a specific product using its unique ID.
    Generates a SAS token for the image_url if one exists and Azure Storage is configured.
    """
    logger.info(f"Product Service: Fetching product with ID: {product_id}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(f"Product Service: Product with ID {product_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    logger.info(f"Product Service: Retrieved product with ID {product_id}. Name: {product.name}")
    return product


@app.put("/products/{product_id}", response_model=ProductResponse, summary="Update an existing product by ID")
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates an existing product's details. Only provided fields will be updated.
    If image_url is provided, it will be stored directly.
    """
    logger.info(f"Product Service: Updating product with ID: {product_id} with data: {product.model_dump(exclude_unset=True)}")
    db_product = db.query(Product).filter(Product.product_id == product_id).first()
    if not db_product:
        logger.warning(f"Product Service: Attempted to update non-existent product with ID {product_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_data = product.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    try:
        db.add(db_product) # Mark for update
        db.commit()
        db.refresh(db_product)
        logger.info(f"Product Service: Product {product_id} updated successfully.")
        return db_product
    except Exception as e:
        db.rollback()
        logger.error(f"Product Service: Error updating product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update product.")


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a product by ID")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """
    Deletes a product record from the database.
    Does NOT delete the image from Azure Blob Storage.
    """
    logger.info(f"Product Service: Attempting to delete product with ID: {product_id}")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(f"Product Service: Attempted to delete non-existent product with ID {product_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    try:
        db.delete(product)
        db.commit()
        logger.info(f"Product Service: Product {product_id} deleted successfully. Name: {product.name}")
    except Exception as e:
        db.rollback()
        logger.error(f"Product Service: Error deleting product {product_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the product."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/products/{product_id}/upload-image",
    response_model=ProductResponse,
    summary="Upload an image for a product to Azure Blob Storage"
)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Uploads an image file to Azure Blob Storage and updates the product's image_url in the database.
    Generates a SAS token for the image URL with a defined expiry.
    Only supports image file types.
    """
    if not blob_service_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure Blob Storage is not configured or available."
        )

    db_product = db.query(Product).filter(Product.product_id == product_id).first()
    if not db_product:
        logger.warning(f"Product Service: Product with ID {product_id} not found for image upload.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Basic file type validation
    allowed_content_types = ["image/jpeg", "image/png", "image/gif"]
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only {', '.join(allowed_content_types)} are allowed."
        )

    try:
        # Create a unique blob name (e.g., product_id/timestamp_originalfilename.ext)
        file_extension = os.path.splitext(file.filename)[1] if os.path.splitext(file.filename)[1] else ".jpg" # Ensure extension
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        blob_name = f"{timestamp}{file_extension}"

        blob_client = blob_service_client.get_blob_client(
            container=AZURE_STORAGE_CONTAINER_NAME,
            blob=blob_name
        )

        logger.info(f"Product Service: Uploading image '{file.filename}' for product {product_id} as '{blob_name}' to Azure.")
        
        # Upload the file content directly
        # Use stream=True for large files
        blob_client.upload_blob(
            file.file,
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type)
        )
        
        # Generate Shared Access Signature (SAS) for public read access
        # SAS will expire after AZURE_SAS_TOKEN_EXPIRY_HOURS
        sas_token = generate_blob_sas(
            account_name=AZURE_STORAGE_ACCOUNT_NAME,
            account_key=AZURE_STORAGE_ACCOUNT_KEY,
            container_name=AZURE_STORAGE_CONTAINER_NAME,
            blob_name=blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=AZURE_SAS_TOKEN_EXPIRY_HOURS)
        )
        # Construct the full URL with SAS token
        image_url = f"{blob_client.url}?{sas_token}"

        # Update the product in the database with the image URL (including SAS token)
        db_product.image_url = image_url
        db.add(db_product)
        db.commit()
        db.refresh(db_product)

        logger.info(f"Product Service: Image uploaded and product {product_id} updated with SAS URL: {image_url}")
        return db_product

    except Exception as e:
        db.rollback()
        logger.error(f"Product Service: Error uploading image for product {product_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not upload image or update product: {e}"
        )
        
# --- Endpoint for Stock Deduction ---
@app.patch(
    "/products/{product_id}/deduct-stock",
    response_model=ProductResponse,
    summary="[DEPRECATED/FALLBACK] Deduct stock quantity for a product (prefer async events)"
)
async def deduct_product_stock_sync(
    product_id: int,
    request: StockDeductRequest,
    db: Session = Depends(get_db)
):
    """
    Deducts a specified quantity from a product's stock.
    Returns 404 if product not found, 400 if insufficient stock.
    """
    logger.info(f"Product Service: Attempting to deduct {request.quantity_to_deduct} from stock for product ID: {product_id}")
    db_product = db.query(Product).filter(Product.product_id == product_id).first()

    if not db_product:
        logger.warning(f"Product Service: Stock deduction failed: Product with ID {product_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if db_product.stock_quantity < request.quantity_to_deduct:
        logger.warning(f"Product Service: Stock deduction failed for product {product_id}. Insufficient stock: {db_product.stock_quantity} available, {request.quantity_to_deduct} requested.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock for product '{db_product.name}'. Only {db_product.stock_quantity} available."
        )
    
    # Perform deduction
    db_product.stock_quantity -= request.quantity_to_deduct
    
    try:
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        logger.info(f"Product Service: Stock for product {product_id} updated to {db_product.stock_quantity}. Deducted {request.quantity_to_deduct}.")

        # Optional: Log or trigger alert if stock falls below threshold
        if db_product.stock_quantity < RESTOCK_THRESHOLD:
            logger.warning(f"Product Service: ALERT! Stock for product '{db_product.name}' (ID: {db_product.product_id}) is low: {db_product.stock_quantity}.")

        return db_product
    except Exception as e:
        db.rollback()
        logger.error(f"Product Service: Error deducting stock for product {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not deduct stock.")
    