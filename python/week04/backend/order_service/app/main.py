# backend/order_service/app/main.py

"""
Order Service — Week 4
Handles order creation asynchronously using RabbitMQ.
Consumes stock events from Product Service.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from db import engine, Base, get_db
from models import Order, OrderStatus
from schemas import OrderCreate, OrderUpdate, OrderResponse, OrderItem

import os
import json
import asyncio
import logging

import aio_pika
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv()


# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- RabbitMQ Configuration ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")

RABBITMQ_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/"

rabbitmq_connection = None
rabbitmq_channel = None

# --- RabbitMQ Connection and Producer/Consumer Setup ---
async def connect_rabbitmq():
    global rabbitmq_connection, rabbitmq_channel
    retries = 10 # Robust retries for Docker Compose readiness
    for i in range(retries):
        try:
            logger.info(f"Attempting to connect to RabbitMQ at {RABBITMQ_URL} (Attempt {i+1}/{retries})...")
            rabbitmq_connection = await aio_pika.connect_robust(RABBITMQ_URL)
            rabbitmq_channel = await rabbitmq_connection.channel()
            logger.info("Connected to RabbitMQ successfully!")

            # Declare exchanges
            # 'order_events' exchange: used by Order service to publish
            await rabbitmq_channel.declare_exchange('order_events', aio_pika.ExchangeType.TOPIC, durable=True)
            # 'stock_events' exchange: used by Product service to publish, Order service to consume
            await rabbitmq_channel.declare_exchange('stock_events', aio_pika.ExchangeType.TOPIC, durable=True)

            # Declare queue for 'stock_deducted' and 'stock_failed' events and bind it
            # This queue will hold messages from the Product service about stock operations
            queue = await rabbitmq_channel.declare_queue('order_stock_status_queue', durable=True)
            await queue.bind('stock_events', routing_key='stock.deducted') # Bind to success events
            await queue.bind('stock_events', routing_key='stock.failed') # Bind to failure events

            # Start consuming messages from this queue
            await queue.consume(on_stock_event)
            logger.info("Started consuming 'stock.deducted' and 'stock.failed' events from RabbitMQ.")
            return
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            await asyncio.sleep(5) # Wait before retrying
    raise Exception("Could not connect to RabbitMQ after multiple retries.")

# --- RabbitMQ Producer for 'order.created' event ---
async def publish_order_created_event(order_data: dict):
    """
    Publishes an 'order.created' event to RabbitMQ.
    """
    if not rabbitmq_channel:
        logger.error("RabbitMQ channel not available for publishing order events.")
        return

    try:
        message_body = json.dumps(order_data).encode('utf-8')
        exchange = await rabbitmq_channel.get_exchange('order_events', ensure=True)
        # Publish the message on the exchange object
        await exchange.publish(
            message=aio_pika.Message(
                body=message_body,
                content_type='application/json',
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT # Make message persistent
            ),
            routing_key='order.created' # Routing key is passed to the exchange's publish method
        )
        logger.info(f"Published order.created event for Order ID: {order_data.get('order_id')}")
    except Exception as e:
        logger.error(f"Failed to publish order.created event for Order ID {order_data.get('order_id')}: {e}", exc_info=True)


# --- RabbitMQ Consumer for Stock Events ---
async def on_stock_event(message: aio_pika.IncomingMessage):
    """
    Handles incoming 'stock.deducted' or 'stock.failed' messages from Product Service
    to update order status.
    """
    async with message.process(): # Acknowledge message upon successful processing
        try:
            stock_data = json.loads(message.body.decode())
            order_id = stock_data.get("order_id")
            status = stock_data.get("status") # "success" or "failure"
            logger.info(f"Received stock event for Order ID: {order_id}, Status: {status}")

            db: Session = next(get_db()) # Get a new DB session for this message processing
            order = db.query(Order).filter(Order.order_id == order_id).first()

            if not order:
                logger.warning(f"Order {order_id} not found when processing stock event. Maybe already handled/deleted?")
                return

            # Update order status based on the stock event
            if status == "success":
                order.status = OrderStatus.CONFIRMED
                logger.info(f"Order {order_id} status updated to CONFIRMED.")
            elif status == "failure":
                order.status = OrderStatus.FAILED # Or another appropriate status like PARTIALLY_FAILED
                logger.warning(f"Order {order_id} status updated to FAILED due to stock issues.")
            
            db.add(order)
            db.commit()
            db.refresh(order)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message body as JSON: {e}. Message: {message.body.decode()}")
        except Exception as e:
            logger.error(f"Error processing stock event message for Order ID {order_id}: {e}", exc_info=True)
        finally:
            db.close() # Always close the session

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8000")

#Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Order Service API",
    description="Handles orders and syncs stock with Product Service.",
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

# --- FastAPI Event Handlers for Database and RabbitMQ Lifecycle ---
@app.on_event("startup")
async def startup_event():
    # Ensure database tables are created (important for migrations later)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")
    await connect_rabbitmq()

@app.on_event("shutdown")
async def shutdown_event():
    if rabbitmq_connection:
        logger.info("Closing RabbitMQ connection...")
        await rabbitmq_connection.close()
        logger.info("RabbitMQ connection closed.")

@app.post("/orders/", response_model=OrderResponse, status_code=202)
async def create_order(order_create_data: OrderCreate, db: Session = Depends(get_db)):
    """
    Create a new order. Stock check and deduction are handled asynchronously
    by the Product Service via RabbitMQ.
    """
    
    # Store the order with an initial PENDING_STOCK_CHECK status
    db_order = Order(
        customer_id=order_create_data.customer_id,
        items_json=json.dumps([item.dict() for item in order_create_data.items]), # Store items as JSON
        status=OrderStatus.PENDING_STOCK_CHECK
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order) # Get the autoincremented order_id
    
    # Prepare order data for RabbitMQ event
    order_event_data = {
        "order_id": db_order.order_id,
        "customer_id": db_order.customer_id,
        "items": [item.dict() for item in order_create_data.items],
        "timestamp": db_order.created_at.isoformat()
    }
    
    # Publish the order.created event to RabbitMQ
    await publish_order_created_event(order_event_data)

    # Return the order immediately with its initial status
    return OrderResponse(
        order_id=db_order.order_id,
        customer_id=db_order.customer_id,
        items=order_create_data.items, # Return the original items list from request
        status=db_order.status,
        created_at=db_order.created_at,
        updated_at=db_order.updated_at
    )

@app.get("/orders/", response_model=list[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    # When fetching, parse items_json back to list of OrderItem
    orders = db.query(Order).all()
    # Map raw DB orders to OrderResponse schema, parsing items_json
    return [
        OrderResponse(
            order_id=o.order_id,
            customer_id=o.customer_id,
            items=[OrderItem(**item) for item in json.loads(o.items_json)], # Parse JSON string to list of OrderItem
            status=o.status,
            created_at=o.created_at,
            updated_at=o.updated_at
        ) for o in orders
    ]

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse(
        order_id=order.order_id,
        customer_id=order.customer_id,
        items=[OrderItem(**item) for item in json.loads(order.items_json)],
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at
    )

@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, update_data: OrderUpdate, db: Session = Depends(get_db)):
    """
    Update order status directly (e.g., for cancellation by admin).
    Note: Changes to order items/quantities are complex in an async system
    and are not directly supported via this PUT for Week 4.
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    updated = False
    if update_data.status is not None:
        order.status = update_data.status
        updated = True
        logger.info(f"Order {order_id} status updated to {order.status.value} via direct API call.")
        # TODO: If cancelling, you might publish an 'order.cancelled' event for stock restock

    if updated:
        db.commit()
        db.refresh(order)
    
    # Parse items_json before returning
    return OrderResponse(
        order_id=order.order_id,
        customer_id=order.customer_id,
        items=[OrderItem(**item) for item in json.loads(order.items_json)],
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at
    )


@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """
    Deletes an order.
    NOTE: In a real system, deleting an order with a confirmed status might
    require publishing an event to restock products. For simplicity,
    this currently just deletes the record.
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # In a real system, if order.status is CONFIRMED, you would
    # publish an 'order.cancelled' event to restock items
    # For Week 4, we're simplifying this.

    db.delete(order)
    db.commit()
    return {"detail": "Order deleted"}
