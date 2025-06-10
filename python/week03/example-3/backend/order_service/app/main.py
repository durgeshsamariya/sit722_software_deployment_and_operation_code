# week03/example-3/backend/order_service/app/main.py

"""
FastAPI Order Service API.
Manages customer orders and their items.
Now fully integrated with RabbitMQ for asynchronous stock deduction.
Also integrates with the new Customer Service.
"""

import sys
import logging
import time
import os
import json
import asyncio
from typing import Optional, List
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Depends, status, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import OperationalError

import httpx
import aio_pika

from .db import engine, Base, get_db, SessionLocal
from .models import Order, OrderItem
from .schemas import OrderCreate, OrderUpdate, OrderResponse, OrderItemResponse, OrderStatusUpdate


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

# --- Configuration for Product Service URL ---
# This will be set via environment variable in Docker Compose
# Default to localhost for local development without Docker Compose
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8000")
logger.info(f"Order Service: Configured to communicate with Product Service at: {PRODUCT_SERVICE_URL}")

# --- Service URLs Configuration ---
CUSTOMER_SERVICE_URL = os.getenv("CUSTOMER_SERVICE_URL", "http://localhost:8002") # New Customer Service URL
logger.info(f"Order Service: Configured to communicate with Customer Service at: {CUSTOMER_SERVICE_URL}")


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
    title="Order Service API",
    description="Manages orders for mini-ecommerce app, with synchronous stock deduction.",
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

# --- RabbitMQ Helper Functions ---

async def connect_to_rabbitmq():
    """Establishes an asynchronous connection to RabbitMQ."""
    global rabbitmq_connection, rabbitmq_channel, rabbitmq_exchange
    
    rabbitmq_url = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"
    max_retries = 10
    retry_delay_seconds = 5

    for i in range(max_retries):
        try:
            logger.info(f"Order Service: Attempting to connect to RabbitMQ (attempt {i+1}/{max_retries})...")
            rabbitmq_connection = await aio_pika.connect_robust(rabbitmq_url)
            rabbitmq_channel = await rabbitmq_connection.channel()
            # Declare a direct exchange for events
            rabbitmq_exchange = await rabbitmq_channel.declare_exchange('ecomm_events', aio_pika.ExchangeType.DIRECT, durable=True)
            logger.info("Order Service: Connected to RabbitMQ and declared 'ecomm_events' exchange.")
            return True
        except Exception as e:
            logger.warning(f"Order Service: Failed to connect to RabbitMQ: {e}")
            if i < max_retries - 1:
                await asyncio.sleep(retry_delay_seconds)
            else:
                logger.critical(f"Order Service: Failed to connect to RabbitMQ after {max_retries} attempts. RabbitMQ functionality will be limited.")
                return False
    return False

async def close_rabbitmq_connection():
    """Closes the RabbitMQ connection."""
    if rabbitmq_connection:
        logger.info("Order Service: Closing RabbitMQ connection.")
        await rabbitmq_connection.close()

async def publish_event(routing_key: str, message_data: dict):
    """Publishes a message to the RabbitMQ exchange."""
    if not rabbitmq_exchange:
        logger.error(f"Order Service: RabbitMQ exchange not available. Cannot publish event '{routing_key}'.")
        return
    try:
        message_body = json.dumps(message_data).encode('utf-8')
        message = aio_pika.Message(
            body=message_body,
            content_type='application/json',
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT # Make message persistent
        )
        await rabbitmq_exchange.publish(message, routing_key=routing_key)
        logger.info(f"Order Service: Published event '{routing_key}' with data: {message_data}")
    except Exception as e:
        logger.error(f"Order Service: Failed to publish event '{routing_key}': {e}", exc_info=True)

async def consume_stock_events(db_session_factory: Session):
    """
    Consumes messages from 'product.stock.deducted' and 'product.stock.deduction.failed' queues
    and updates order status accordingly.
    This function runs in a separate background task.
    """
    if not rabbitmq_channel or not rabbitmq_exchange:
        logger.error("Order Service: RabbitMQ channel or exchange not available for consuming stock events.")
        return

    stock_deducted_queue_name = 'order_service_stock_deducted_queue'
    stock_deduction_failed_queue_name = 'order_service_stock_deduction_failed_queue'

    try:
        # Declare and bind queue for successful stock deductions
        stock_deducted_queue = await rabbitmq_channel.declare_queue(stock_deducted_queue_name, durable=True)
        await stock_deducted_queue.bind(rabbitmq_exchange, routing_key='product.stock.deducted')
        logger.info(f"Order Service: Listening for 'product.stock.deducted' messages on queue '{stock_deducted_queue_name}'.")

        # Declare and bind queue for failed stock deductions
        stock_deduction_failed_queue = await rabbitmq_channel.declare_queue(stock_deduction_failed_queue_name, durable=True)
        await stock_deduction_failed_queue.bind(rabbitmq_exchange, routing_key='product.stock.deduction.failed')
        logger.info(f"Order Service: Listening for 'product.stock.deduction.failed' messages on queue '{stock_deduction_failed_queue_name}'.")

        # Create a combined consumer for both queues
        async def process_message(message: aio_pika.abc.AbstractIncomingMessage):
            async with message.process():
                try:
                    message_data = json.loads(message.body.decode('utf-8'))
                    routing_key = message.routing_key
                    order_id = message_data.get('order_id')
                    
                    if not order_id:
                        logger.error(f"Order Service: Received message with no order_id: {message_data}")
                        return

                    # Create a new session for this background task
                    local_db_session = db_session_factory()
                    try:
                        db_order = local_db_session.query(Order).filter(Order.order_id == order_id).first()

                        if not db_order:
                            logger.warning(f"Order Service: Received event for non-existent order ID: {order_id}. Routing key: {routing_key}. Skipping update.")
                            return

                        if routing_key == 'product.stock.deducted':
                            db_order.status = "confirmed"
                            logger.info(f"Order Service: Order {order_id} status updated to 'confirmed' based on stock deduction success.")
                        elif routing_key == 'product.stock.deduction.failed':
                            db_order.status = "failed" # New status for failed orders
                            logger.warning(f"Order Service: Order {order_id} status updated to 'failed' based on stock deduction failure. Details: {message_data.get('details')}")
                            # In a real app, you might publish a compensation event here or trigger alerts.
                        else:
                            logger.warning(f"Order Service: Received unknown routing key '{routing_key}' for order {order_id}.")
                            return

                        local_db_session.add(db_order)
                        local_db_session.commit()
                        local_db_session.refresh(db_order)
                        logger.info(f"Order Service: Order {order_id} status successfully updated to {db_order.status}.")

                    except Exception as db_e:
                        local_db_session.rollback()
                        logger.critical(f"Order Service: Database error updating order {order_id} status: {db_e}", exc_info=True)
                    finally:
                        local_db_session.close()

                except json.JSONDecodeError as e:
                    logger.error(f"Order Service: Failed to decode RabbitMQ message body: {e}. Message: {message.body}")
                except Exception as e:
                    logger.error(f"Order Service: Unhandled error processing stock event message: {e}", exc_info=True)

        # Start consuming from both queues concurrently
        await asyncio.gather(
            stock_deducted_queue.consume(process_message),
            stock_deduction_failed_queue.consume(process_message)
        )

    except Exception as e:
        logger.critical(f"Order Service: Error in RabbitMQ consumer for stock events: {e}", exc_info=True)



# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    """
    Handles application startup events.
    Ensures database tables are created (if not exist) for the Order Service.
    Includes a retry mechanism for database connection robustness.
    """
    max_retries = 10
    retry_delay_seconds = 5
    for i in range(max_retries):
        try:
            logger.info(f"Order Service: Attempting to connect to PostgreSQL and create tables (attempt {i+1}/{max_retries})...")
            Base.metadata.create_all(bind=engine)
            logger.info("Order Service: Successfully connected to PostgreSQL and ensured tables exist.")
            break # Exit loop if successful
        except OperationalError as e:
            logger.warning(f"Order Service: Failed to connect to PostgreSQL: {e}")
            if i < max_retries - 1:
                logger.info(f"Order Service: Retrying in {retry_delay_seconds} seconds...")
                time.sleep(retry_delay_seconds)
            else:
                logger.critical(f"Order Service: Failed to connect to PostgreSQL after {max_retries} attempts. Exiting application.")
                sys.exit(1) # Critical failure: exit if DB connection is unavailable
        except Exception as e:
            logger.critical(f"Order Service: An unexpected error occurred during database startup: {e}", exc_info=True)
            sys.exit(1)
            
    # Connect to RabbitMQ and start consumer
    if await connect_to_rabbitmq():
        # Pass SessionLocal directly to the consumer to create new sessions per message
        asyncio.create_task(consume_stock_events(SessionLocal))
    else:
        logger.error("Order Service: RabbitMQ connection failed at startup. Async order processing will not work.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Handles application shutdown events.
    Closes the RabbitMQ connection.
    """
    await close_rabbitmq_connection()

# --- Root Endpoint ---
@app.get("/", status_code=status.HTTP_200_OK, summary="Root endpoint")
async def read_root():
    """
    Returns a welcome message for the Order Service.
    """
    return {"message": "Welcome to the Order Service!"}


# --- Health Check Endpoint ---
@app.get("/health", status_code=status.HTTP_200_OK, summary="Health check endpoint")
async def health_check():
    """
    A simple health check endpoint to verify the service is running.
    Returns 200 OK if the service is alive.
    """
    return {"status": "ok", "service": "order-service"}

@app.post(
    "/orders/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order and publish 'order.placed' event for stock deduction"
)
async def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db)
):
    """
    Creates a new order in the database with 'pending' status.
    It then publishes an 'order.placed' event to RabbitMQ,
    triggering asynchronous stock deduction in the Product Service.
    It also validates the customer_id against the Customer Service.
    """
    if not order.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must contain at least one item.")

    # --- Step 1: Validate customer_id with Customer Service (Synchronous Call) ---
    async with httpx.AsyncClient() as client:
        customer_validation_url = f"{CUSTOMER_SERVICE_URL}/customers/{order.user_id}"
        logger.info(f"Order Service: Validating customer ID {order.user_id} via Customer Service at {customer_validation_url}")
        try:
            response = await client.get(customer_validation_url, timeout=3)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses
            customer_data = response.json()
            logger.info(f"Order Service: Customer ID {order.user_id} validated. Customer email: {customer_data.get('email')}")
            
            # Optional: If the order's shipping address is not provided, use the customer's default
            if not order.shipping_address and customer_data.get('shipping_address'):
                order.shipping_address = customer_data['shipping_address']
                logger.info(f"Order Service: Using customer's default shipping address: {order.shipping_address}")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == status.HTTP_404_NOT_FOUND:
                logger.warning(f"Order Service: Customer validation failed for ID {order.user_id}: Customer not found.")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid user_id: Customer {order.user_id} not found.")
            else:
                logger.error(f"Order Service: Customer service returned an error for ID {order.user_id}: {e.response.status_code} - {e.response.text}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to validate customer with Customer Service.")
        except httpx.RequestError as e:
            logger.critical(f"Order Service: Network error communicating with Customer Service: {e}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Customer Service is currently unavailable. Please try again later.")
        except Exception as e:
            logger.error(f"Order Service: An unexpected error occurred during customer validation: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


    # --- Step 2: Create the Order in the Order Service DB with 'pending' status ---
    total_amount = sum(Decimal(str(item.quantity)) * Decimal(str(item.price_at_purchase)) for item in order.items)
    
    db_order = Order(
        user_id=order.user_id,
        shipping_address=order.shipping_address,
        total_amount=total_amount,
        status="pending" # Always start as pending; status will be updated by RabbitMQ consumer
    )
    
    db.add(db_order)
    db.flush() # Use flush to get order_id before committing, needed for order items

    for item in order.items:
        db_order_item = OrderItem(
            order_id=db_order.order_id,
            product_id=item.product_id,
            quantity=item.quantity,
            price_at_purchase=item.price_at_purchase,
            item_total=Decimal(str(item.quantity)) * Decimal(str(item.price_at_purchase))
        )
        db.add(db_order_item)

    try:
        db.commit()
        db.refresh(db_order)
        db.refresh(db_order, attribute_names=['items']) # Ensure items are loaded for response
        logger.info(f"Order Service: Order {db_order.order_id} created with initial 'pending' status for user {db_order.user_id}.")

        # --- Step 3: Publish 'order.placed' event to RabbitMQ ---
        order_event_data = {
            "order_id": db_order.order_id,
            "user_id": db_order.user_id,
            "total_amount": float(db_order.total_amount), # Convert Decimal for JSON serialization
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price_at_purchase": float(item.price_at_purchase)
                } for item in db_order.items
            ],
            "order_date": db_order.order_date.isoformat(),
            "status": db_order.status # Should be 'pending' at this point
        }
        await publish_event('order.placed', order_event_data)
        logger.info(f"Order Service: 'order.placed' event published for order {db_order.order_id}.")
        
        return db_order
    except Exception as e:
        db.rollback()
        logger.error(f"Order Service: Error creating order or publishing event: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create order or publish event. Please check logs."
        )


@app.get(
    "/orders/",
    response_model=List[OrderResponse],
    summary="Retrieve a list of all orders"
)
def list_orders(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user_id: Optional[int] = Query(None, ge=1, description="Filter orders by user ID."),
    status: Optional[str] = Query(None, pattern="^(pending|processing|shipped|cancelled|confirmed|completed|failed)$")
):
    """
    Lists orders with optional pagination and filtering by user ID or status.
    Includes nested order items in the response.
    """
    logger.info(f"Order Service: Listing orders (skip={skip}, limit={limit}, user_id={user_id}, status='{status}')")
    query = db.query(Order).options(joinedload(Order.items))

    if user_id:
        query = query.filter(Order.user_id == user_id)
        logger.info(f"Order Service: Filtering orders by user_id: {user_id}")
    if status:
        query = query.filter(Order.status == status)
        logger.info(f"Order Service: Filtering orders by status: {status}")
    
    orders = query.offset(skip).limit(limit).all()
    logger.info(f"Order Service: Retrieved {len(orders)} orders (skip={skip}, limit={limit}).")
    return orders

@app.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Retrieve a single order by ID"
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves details for a specific order using its unique ID.
    Includes nested order items in the response.
    """
    logger.info(f"Order Service: Fetching order with ID: {order_id}")
    order = db.query(Order).options(joinedload(Order.items)).filter(Order.order_id == order_id).first()
    if not order:
        logger.warning(f"Order Service: Order with ID {order_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    logger.info(f"Order Service: Retrieved order with ID {order_id}. Status: {order.status}")
    return order

@app.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="Update the status of an order"
)
async def update_order_status(
    order_id: int,
    new_status: OrderStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates only the 'status' of an existing order.
    """
    logger.info(f"Order Service: Attempting to update status for order {order_id} to '{new_status.status}'.")
    db_order = db.query(Order).filter(Order.order_id == order_id).first()
    if not db_order:
        logger.warning(f"Order Service: Order with ID {order_id} not found for status update.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    db_order.status = new_status
    
    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        db.refresh(db_order, attribute_names=['items'])
        logger.info(f"Order Service: Order {order_id} status updated to '{db_order.status}'.")
        return db_order
    except Exception as e:
        db.rollback()
        logger.error(f"Order Service: Error updating status for order {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update order status.")


@app.delete(
    "/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an order by ID"
)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Deletes an order record from the database, including all associated order items.
    """
    logger.info(f"Order Service: Attempting to delete order with ID: {order_id}")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        logger.warning(f"Order Service: Order with ID: {order_id} not found for deletion.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    try:
        # SQLAlchemy cascade="all, delete-orphan" on relationship handles deleting order_items
        db.delete(order)
        db.commit()
        logger.info(f"Order Service: Order (ID: {order_id}) deleted successfully.")
    except Exception as e:
        db.rollback()
        logger.error(f"Order Service: Error deleting order {order_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the order."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Helper Endpoint for Order Items (Optional, mainly for debugging/direct item access) ---
# This endpoint allows retrieving order items for a specific order.
# The primary way to get items is usually via the get_order endpoint,
# but this could be useful if only items are needed.
@app.get(
    "/orders/{order_id}/items",
    response_model=List[OrderItemResponse],
    summary="Retrieve all items for a specific order"
)
def get_order_items(
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves all order items belonging to a specific order ID.
    """
    logger.info(f"Order Service: Fetching items for order ID: {order_id}")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        logger.warning(f"Order Service: Order with ID {order_id} not found when fetching items.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    # Access items through the relationship
    logger.info(f"Order Service: Retrieved {len(order.items)} items for order {order_id}.")
    return order.items
