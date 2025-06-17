# week03/example-2/backend/order_service/app/main.py

import logging
import os
import sys
import time
from decimal import Decimal
from typing import List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Order, OrderItem
from .schemas import OrderCreate, OrderItemResponse, OrderResponse, OrderUpdate

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

# --- Configuration for Product Service URL ---
# This will be set via environment variable in Docker Compose
# Default to localhost for local development without Docker Compose
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8000")
logger.info(
    f"Order Service: Configured to communicate with Product Service at: {PRODUCT_SERVICE_URL}"
)

# --- FastAPI Application Setup ---
app = FastAPI(
    title="Order Service API",
    description="Manages orders for mini-ecommerce app, with synchronous stock deduction.",
    version="1.0.0",
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
    max_retries = 10
    retry_delay_seconds = 5
    for i in range(max_retries):
        try:
            logger.info(
                f"Order Service: Attempting to connect to PostgreSQL and create tables (attempt {i+1}/{max_retries})..."
            )
            Base.metadata.create_all(bind=engine)
            logger.info(
                "Order Service: Successfully connected to PostgreSQL and ensured tables exist."
            )
            break  # Exit loop if successful
        except OperationalError as e:
            logger.warning(f"Order Service: Failed to connect to PostgreSQL: {e}")
            if i < max_retries - 1:
                logger.info(
                    f"Order Service: Retrying in {retry_delay_seconds} seconds..."
                )
                time.sleep(retry_delay_seconds)
            else:
                logger.critical(
                    f"Order Service: Failed to connect to PostgreSQL after {max_retries} attempts. Exiting application."
                )
                sys.exit(1)  # Critical failure: exit if DB connection is unavailable
        except Exception as e:
            logger.critical(
                f"Order Service: An unexpected error occurred during database startup: {e}",
                exc_info=True,
            )
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
    summary="Create a new order",
)
async def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """
    Creates a new order in the database.
    Performs synchronous stock deduction by calling the Product Service for each item.
    If stock deduction fails for any item, the entire order creation is aborted.
    """
    if not order.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item.",
        )

    # List to store successfully deducted items in case of partial failures
    successfully_deducted_items = []
    logger.info(f"Order Service: Creating new order for user_id: {order.user_id}")

    # Use an httpx client for synchronous calls to the Product Service
    async with httpx.AsyncClient() as client:
        for item in order.items:
            product_id = item.product_id
            quantity = item.quantity

            deduct_stock_url = (
                f"{PRODUCT_SERVICE_URL}/products/{product_id}/deduct-stock"
            )
            logger.info(
                f"Order Service: Attempting to deduct stock for product {product_id} (qty: {quantity}) via Product Service at {deduct_stock_url}"
            )

            try:
                # Synchronous call to Product Service to deduct stock
                response = await client.patch(
                    deduct_stock_url,
                    json={"quantity_to_deduct": quantity},
                    timeout=5,  # Set a timeout for the external API call
                )
                response.raise_for_status()  # Raise an exception for 4xx/5xx responses

                logger.info(
                    f"Order Service: Stock deduction successful for product {product_id}."
                )
                successfully_deducted_items.append(item)

            except httpx.HTTPStatusError as e:
                # Handle specific HTTP errors from Product Service
                error_detail = "Unknown error during stock deduction."
                if e.response.status_code == status.HTTP_404_NOT_FOUND:
                    error_detail = f"Product {product_id} not found."
                elif e.response.status_code == status.HTTP_400_BAD_REQUEST:
                    response_json = e.response.json()
                    error_detail = response_json.get(
                        "detail", "Insufficient stock or invalid request."
                    )

                logger.error(
                    f"Order Service: Stock deduction failed for product {product_id}: {error_detail}. Status: {e.response.status_code}"
                )
                # Rollback any previously successful deductions in case of failure
                await _rollback_stock_deductions(client, successfully_deducted_items)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,  # Or appropriate status
                    detail=f"Failed to deduct stock for product {product_id}: {error_detail}",
                )
            except httpx.RequestError as e:
                # Handle network errors (e.g., Product Service is down)
                logger.critical(
                    f"Order Service: Network error communicating with Product Service for product {product_id}: {e}"
                )
                await _rollback_stock_deductions(client, successfully_deducted_items)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Product Service is currently unavailable. Please try again later. Error: {e}",
                )
            except Exception as e:
                # Catch any other unexpected errors during deduction
                logger.error(
                    f"Order Service: An unexpected error occurred during stock deduction for product {product_id}: {e}",
                    exc_info=True,
                )
                await _rollback_stock_deductions(client, successfully_deducted_items)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred during order creation: {e}",
                )

    # If all stock deductions are successful, proceed with order creation
    logger.info(
        "Order Service: All product stock deductions successful. Proceeding to create order."
    )

    total_amount = sum(
        Decimal(str(item.quantity)) * Decimal(str(item.price_at_purchase))
        for item in order.items
    )

    db_order = Order(
        user_id=order.user_id,
        shipping_address=order.shipping_address,
        total_amount=total_amount,
        status="pending",  # Initial status
    )

    db.add(db_order)
    db.flush()  # Use flush to get order_id before committing, needed for order items

    for item in order.items:
        db_order_item = OrderItem(
            order_id=db_order.order_id,
            product_id=item.product_id,
            quantity=item.quantity,
            price_at_purchase=item.price_at_purchase,
            item_total=Decimal(str(item.quantity))
            * Decimal(str(item.price_at_purchase)),
        )
        db.add(db_order_item)

    try:
        # After successful stock deductions and before final commit, update status to 'confirmed'
        db_order.status = "confirmed"  # Set status to confirmed here
        db.commit()
        db.refresh(db_order)
        # Ensure order items are loaded for the response model
        db.add(db_order)  # Re-add to session if detached by refresh or commit
        db.refresh(db_order, attribute_names=["items"])
        logger.info(
            f"Order Service: Order {db_order.order_id} created and confirmed successfully for user {db_order.user_id}."
        )
        return db_order
    except Exception as e:
        db.rollback()
        logger.error(
            f"Order Service: Error creating order after successful stock deductions: {e}",
            exc_info=True,
        )
        # CRITICAL: If DB commit fails here, you have a mismatch.
        # In a real system, you'd likely need a compensation transaction or alerting.
        # For this example, we log the severe error.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Order created but failed to save to database. Manual intervention required.",
        )


async def _rollback_stock_deductions(client: httpx.AsyncClient, items: List[OrderItem]):
    """
    Helper function to attempt to rollback stock deductions if the order fails.
    This is a "best-effort" rollback for synchronous communication.
    """
    if not items:
        return

    logger.warning(
        "Order Service: Attempting to rollback stock deductions due to order creation failure."
    )
    for item in items:
        product_id = item.product_id
        quantity = item.quantity
        add_stock_url = f"{PRODUCT_SERVICE_URL}/products/{product_id}/deduct-stock"  # Assuming -ve quantity adds stock

        logger.warning(
            f"Order Service: Cannot automatically rollback stock for product {product_id} quantity {quantity}. Manual stock adjustment may be required in Product Service."
        )


@app.get(
    "/orders/",
    response_model=List[OrderResponse],
    summary="Retrieve a list of all orders",
)
def list_orders(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user_id: Optional[int] = Query(None, ge=1, description="Filter orders by user ID."),
    status: Optional[str] = Query(
        None,
        max_length=50,
        description="Filter orders by status (e.g., pending, shipped).",
    ),
):
    """
    Lists orders with optional pagination and filtering by user ID or status.
    Includes nested order items in the response.
    """
    logger.info(
        f"Order Service: Listing orders (skip={skip}, limit={limit}, user_id={user_id}, status='{status}')"
    )
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
    summary="Retrieve a single order by ID",
)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """
    Retrieves details for a specific order using its unique ID.
    Includes nested order items in the response.
    """
    logger.info(f"Order Service: Fetching order with ID: {order_id}")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        logger.warning(f"Order Service: Order with ID {order_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    logger.info(
        f"Order Service: Retrieved order with ID {order_id}. Status: {order.status}"
    )
    return order


@app.patch(  # Use PATCH for partial updates, especially for status
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="Update the status of an order",
)
async def update_order_status(
    order_id: int,
    new_status: str = Query(
        ..., min_length=1, max_length=50, description="New status for the order."
    ),
    db: Session = Depends(get_db),
):
    """
    Updates only the 'status' of an existing order.
    """
    logger.info(
        f"Order Service: Updating status for order {order_id} to '{new_status}'"
    )
    db_order = db.query(Order).filter(Order.order_id == order_id).first()
    if not db_order:
        logger.warning(
            f"Order Service: Order with ID {order_id} not found for status update."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    db_order.status = new_status

    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        logger.info(
            f"Order Service: Order {order_id} status updated to '{new_status}'."
        )
        return db_order
    except Exception as e:
        db.rollback()
        logger.error(
            f"Order Service: Error updating status for order {order_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update order status.",
        )


@app.delete(
    "/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an order by ID",
)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """
    Deletes an order record from the database, including all associated order items.
    """
    logger.info(f"Order Service: Attempting to delete order with ID: {order_id}")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        logger.warning(
            f"Order Service: Order with ID: {order_id} not found for deletion."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    try:
        # SQLAlchemy cascade="all, delete-orphan" on relationship handles deleting order_items
        db.delete(order)
        db.commit()
        logger.info(f"Order Service: Order (ID: {order_id}) deleted successfully.")
    except Exception as e:
        db.rollback()
        logger.error(
            f"Order Service: Error deleting order {order_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the order.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
