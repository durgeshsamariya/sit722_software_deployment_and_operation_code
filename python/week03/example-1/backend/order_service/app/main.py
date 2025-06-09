# week03/example-1/backend/order_service/app/main.py

"""
Order Service - Core API Endpoints

This service manages customer orders, handling their creation, retrieval,
updates, and deletion. A key feature is its synchronous interaction with
the Product Service to perform stock checks and updates, ensuring inventory
accuracy for products involved in orders.
"""

import sys
import logging
import time
from typing import Optional, List
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Depends, status, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from .db import engine, Base, get_db
from .models import Order, OrderItem
from .schemas import OrderCreate, OrderUpdate, OrderResponse, OrderItemResponse




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

app = FastAPI(
    title="Order Service API",
    description="""
    Handles customer orders and synchronizes stock levels with the Product Service.
    Provides CRUD operations for orders and ensures stock consistency.
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
    summary="Create a new order"
)
async def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db)
):
    """
    Creates a new order in the database, including its associated order items.
    The total_amount for the order and item_total for each item are calculated server-side.
    """
    logger.info(f"Order Service: Creating new order for user_id: {order_data.user_id}")
    
    total_amount = Decimal('0.00')
    db_order_items = []

    for item_data in order_data.items:
        # Calculate item_total precisely using Decimal for currency
        item_total = Decimal(str(item_data.quantity)) * Decimal(str(item_data.price_at_purchase))
        total_amount += item_total

        db_order_item = OrderItem(
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            price_at_purchase=Decimal(str(item_data.price_at_purchase)), # Store as Decimal
            item_total=item_total
        )
        db_order_items.append(db_order_item)

    # Create the Order object
    db_order = Order(
        user_id=order_data.user_id,
        shipping_address=order_data.shipping_address,
        status=order_data.status,
        total_amount=total_amount, # Set the calculated total
        items=db_order_items # Assign the created order items
    )

    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order) # Refresh to get auto-generated IDs and timestamps for order and items

        logger.info(f"Order Service: Order {db_order.order_id} created successfully for user {db_order.user_id}.")
        return db_order
    except Exception as e:
        db.rollback()
        logger.error(f"Order Service: Error creating order: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create order.")

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
    status: Optional[str] = Query(None, max_length=50, description="Filter orders by status (e.g., pending, shipped).")
):
    """
    Lists orders with optional pagination and filtering by user ID or status.
    Includes nested order items in the response.
    """
    logger.info(f"Order Service: Listing orders (skip={skip}, limit={limit}, user_id={user_id}, status='{status}')")
    query = db.query(Order)

    if user_id:
        query = query.filter(Order.user_id == user_id)
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.offset(skip).limit(limit).all()
    logger.info(f"Order Service: Retrieved {len(orders)} orders.")
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
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        logger.warning(f"Order Service: Order with ID {order_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    logger.info(f"Order Service: Retrieved order with ID {order_id}. Status: {order.status}")
    return order

@app.patch( # Use PATCH for partial updates, especially for status
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="Update the status of an order"
)
async def update_order_status(
    order_id: int,
    new_status: str = Query(..., min_length=1, max_length=50, description="New status for the order."),
    db: Session = Depends(get_db)
):
    """
    Updates only the 'status' of an existing order.
    """
    logger.info(f"Order Service: Updating status for order {order_id} to '{new_status}'")
    db_order = db.query(Order).filter(Order.order_id == order_id).first()
    if not db_order:
        logger.warning(f"Order Service: Order with ID {order_id} not found for status update.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    db_order.status = new_status
    
    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        logger.info(f"Order Service: Order {order_id} status updated to '{new_status}'.")
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
