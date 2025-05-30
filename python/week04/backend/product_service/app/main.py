# app/main.py

"""
FastAPI Product Service with image upload, CRUD, validation, and stock management.
Includes RabbitMQ integration for asynchronous stock deduction.
"""


from fastapi import (
    FastAPI, Depends, HTTPException, Query, File, UploadFile, Form
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
import os
import json
import asyncio

import aio_pika

from db import Base, engine, get_db
from models import Product
from schemas import ProductCreate, ProductUpdate, ProductResponse
from azure_utils import upload_to_azure_blob

from typing import Optional
from datetime import datetime # Add this import

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Use a logger instance

RESTOCK_THRESHOLD = 5

# --- RabbitMQ Configuration ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")

RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"

rabbitmq_connection = None
rabbitmq_channel = None


# --- RabbitMQ Connection and Consumer Setup ---
async def connect_rabbitmq():
    global rabbitmq_connection, rabbitmq_channel
    retries = 10 # Increase retries for robustness in Docker Compose setup
    for i in range(retries):
        try:
            logger.info(f"Attempting to connect to RabbitMQ at {RABBITMQ_URL} (Attempt {i+1}/{retries})...")
            rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            rabbitmq_channel = await rabbitmq_connection.channel()
            logger.info("Connected to RabbitMQ successfully!")

            # Declare exchanges
            # 'order_events' exchange: used by Order service to publish, Product service to consume
            await rabbitmq_channel.declare_exchange('order_events', aio_pika.ExchangeType.TOPIC, durable=True)
            # 'stock_events' exchange: used by Product service to publish stock status updates
            await rabbitmq_channel.declare_exchange('stock_events', aio_pika.ExchangeType.TOPIC, durable=True)


            # Declare queue for 'order_created' events and bind it
            # This queue will hold messages for stock deduction
            queue = await rabbitmq_channel.declare_queue('order_created_queue', durable=True)
            await queue.bind('order_events', routing_key='order.created') # Bind to 'order_events' exchange for 'order.created' topic

            # Start consuming messages from this queue
            await queue.consume(on_order_created)
            logger.info("Started consuming 'order.created' events from RabbitMQ.")
            return
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            await asyncio.sleep(5) # Wait before retrying
    raise Exception("Could not connect to RabbitMQ after multiple retries.")


# --- RabbitMQ Consumer for 'order.created' events ---
async def on_order_created(message: aio_pika.IncomingMessage):
    """
    Handles incoming 'order.created' messages from RabbitMQ to deduct stock.
    """
    async with message.process(): # Acknowledge message upon successful processing or Nack on failure
        try:
            order_data = json.loads(message.body.decode())
            order_id = order_data.get("order_id")
            items = order_data.get("items")
            logger.info(f"Received order.created event for Order ID: {order_id}")

            db: Session = next(get_db()) # Get a new DB session for this message processing
            stock_updated_successfully = True
            messages = [] # To collect individual item statuses

            for item in items:
                product_id = item["product_id"]
                quantity = item["quantity"]
                
                product = db.query(Product).filter(Product.product_id == product_id).first()
                if not product:
                    logger.warning(f"Product {product_id} not found for Order ID: {order_id}. Skipping stock deduction.")
                    stock_updated_successfully = False
                    messages.append(f"Product {product_id} not found.")
                    continue

                if product.stock_quantity >= quantity:
                    product.stock_quantity -= quantity
                    db.add(product) # Mark for update
                    logger.info(f"Deducted {quantity} of product_id {product_id}. New stock: {product.stock_quantity}")
                    messages.append(f"Stock for {product_id} deducted successfully.")
                else:
                    logger.warning(
                        f"Insufficient stock for product {product_id}. "
                        f"Requested: {quantity}, Available: {product.stock_quantity}. "
                        f"Order ID: {order_id}"
                    )
                    stock_updated_successfully = False
                    messages.append(f"Insufficient stock for {product_id}. Available: {product.stock_quantity}.")
            
            db.commit() # Commit all changes for the order's items
            # db.refresh(product) # If needed to reflect latest state after commit, but not strictly needed for this flow

            # Publish a 'stock_deducted' or 'stock_failed' event back
            status = "success" if stock_updated_successfully else "failure"
            await publish_stock_event(
                order_id, 
                items, 
                status, 
                "Stock update status for order." if stock_updated_successfully else "Stock update failed for some items."
            )
            logger.info(f"Published stock event for Order ID: {order_id} with status: {status}")

            # Check for restock threshold after processing
            for item in items:
                product_id = item["product_id"]
                product = db.query(Product).filter(Product.product_id == product_id).first() # Re-fetch to get latest stock
                if product and product.stock_quantity < RESTOCK_THRESHOLD:
                    logger.info(
                        f"Restock needed for product {product.name} (ID: {product.product_id}): "
                        f"only {product.stock_quantity} left"
                    )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message body as JSON: {e}. Message: {message.body.decode()}")
            # Nack the message if it's malformed JSON and we don't want to requeue it
            # await message.reject(requeue=False)
        except Exception as e:
            logger.error(f"Error processing order.created message for Order ID {order_id}: {e}", exc_info=True)
            # In a real scenario, you might Nack the message here or move to a dead-letter queue
            # await message.reject(requeue=False) # Example: reject without requeue
        finally:
            db.close() # Always close the session

# --- RabbitMQ Producer for Stock Events ---
async def publish_stock_event(order_id: str, items: list, status: str, message: str):
    """
    Publishes a stock event (e.g., stock.deducted, stock.failed) to RabbitMQ.
    """
    if not rabbitmq_channel:
        logger.error("RabbitMQ channel not available for publishing stock events.")
        return

    event_data = {
        "order_id": order_id,
        "items": items,
        "status": status, # "success" or "failure"
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        # Get the exchange object first
        exchange = await rabbitmq_channel.get_exchange('stock_events', ensure=True)
        
        # Publish the message on the exchange object
        await exchange.publish(
            message=aio_pika.Message(
                body=json.dumps(event_data).encode(),
                content_type='application/json',
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT # Make message persistent
            ),
            routing_key='stock.deducted' if status == 'success' else 'stock.failed' # Routing key is passed to the exchange's publish method
        )
        logger.info(f"Published stock event for Order ID: {order_id}, Status: {status}")
    except Exception as e:
        logger.error(f"Failed to publish stock event for Order ID {order_id}: {e}", exc_info=True)



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

# --- FastAPI Event Handlers for RabbitMQ Lifecycle ---
@app.on_event("startup")
async def startup_event():
    # Create tables if they don't exist (ensure this runs before any DB operations)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")
    await connect_rabbitmq()

@app.on_event("shutdown")
async def shutdown_event():
    if rabbitmq_connection:
        logger.info("Closing RabbitMQ connection...")
        await rabbitmq_connection.close()
        logger.info("RabbitMQ connection closed.")


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
    """
    Update product stock directly.
    NOTE: For order-related stock deductions, use the asynchronous messaging flow
    via RabbitMQ (order_created event) for better decoupling and resilience.
    This endpoint is intended for administrative or manual stock adjustments.
    """
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
