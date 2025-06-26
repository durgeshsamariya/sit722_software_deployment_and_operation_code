# week07/example-2/backend/order_service/app/main.py

import logging
import os
import sys
import time
from decimal import Decimal
from typing import List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# --- Prometheus client imports ---
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client.core import CollectorRegistry
from starlette.responses import PlainTextResponse # Required for /metrics endpoint

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

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8000")
logger.info(
    f"Order Service: Configured to communicate with Product Service at: {PRODUCT_SERVICE_URL}"
)

# --- Prometheus Metrics Initialization ---
# Create a custom registry specific to this application instance
registry = CollectorRegistry()
APP_NAME = "order_service" # Unique identifier for this service in metrics

# Define Prometheus metrics (Basic HTTP Metrics)
REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP requests processed by the application',
    ['app_name', 'method', 'endpoint', 'status_code'], registry=registry
)
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds', 'HTTP request duration in seconds',
    ['app_name', 'method', 'endpoint', 'status_code'], registry=registry
)
REQUESTS_IN_PROGRESS = Gauge(
    'http_requests_in_progress', 'Number of HTTP requests in progress',
    ['app_name', 'method', 'endpoint'], registry=registry
)

# Custom Metrics specific to Order Service business logic
ORDER_CREATION_TOTAL = Counter(
    'order_creation_total', 'Total number of orders created',
    ['app_name', 'status'], registry=registry # status: success, failed_items, db_error
)
ORDER_ITEM_COUNT = Counter(
    'order_item_count', 'Total number of individual items processed in orders',
    ['app_name', 'product_id'], registry=registry
)
ORDER_TOTAL_AMOUNT = Histogram(
    'order_total_amount_dollars', 'Total amount of orders in dollars',
    ['app_name'], registry=registry # This will provide buckets for order value distribution
)
ORDER_STATUS_UPDATE_TOTAL = Counter(
    'order_status_update_total', 'Total order status updates',
    ['app_name', 'status'], registry=registry # status: success, not_found, db_error
)
# Metrics for inter-service communication (calls from Order Service to Product Service)
PRODUCT_SERVICE_CALL_TOTAL = Counter(
    'product_service_call_total', 'Total calls made from Order Service to Product Service',
    ['app_name', 'target_endpoint', 'method', 'status_code'], registry=registry
)
PRODUCT_SERVICE_CALL_DURATION = Histogram(
    'product_service_call_duration_seconds', 'Duration of calls from Order Service to Product Service',
    ['app_name', 'target_endpoint', 'method', 'status_code'], registry=registry
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
    return {"message": "Welcome to the Order Service!"}


# --- Health Check Endpoint ---
@app.get("/health", status_code=status.HTTP_200_OK, summary="Health check endpoint")
async def health_check():
    return {"status": "ok", "service": "order-service"}


@app.post(
    "/orders/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
)
async def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    if not order.items:
        ORDER_CREATION_TOTAL.labels(app_name=APP_NAME, status="no_items").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item.",
        )

    # List to store successfully deducted items in case of partial failures
    successfully_deducted_items = []
    logger.info(f"Order Service: Creating new order for user_id: {order.user_id}")

    order_overall_success = True # Flag to track if all items processed successfully

    # Use an httpx client for synchronous calls to the Product Service
    async with httpx.AsyncClient() as client:
        for item in order.items:
            product_id = item.product_id
            quantity = item.quantity

            # --- Metrics for Product Service Calls (GET product details) ---
            product_detail_url = f"{PRODUCT_SERVICE_URL}/products/{product_id}"
            product_detail_call_start = time.time()
            product_detail_call_status = "unknown"

            try:
                # Get product details (needed for product_name and initial stock check)
                product_response = await client.get(product_detail_url, timeout=5)
                product_response.raise_for_status()
                product_data = product_response.json()
                product_detail_call_status = str(product_response.status_code)
                logger.info(f"Order Service: Fetched product details for {product_id}.")

            except httpx.RequestError as e:
                logger.critical(f"Order Service: Network error getting product details from Product Service for product {product_id}: {e}")
                order_overall_success = False
                product_detail_call_status = "network_error"
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Product Service is currently unavailable for details lookup. Error: {e}",
                )
            except httpx.HTTPStatusError as e:
                logger.error(f"Order Service: Product Service returned error for product details {product_id}: {e.response.status_code} - {e.response.text}")
                order_overall_success = False
                product_detail_call_status = str(e.response.status_code)
                if e.response.status_code == status.HTTP_404_NOT_FOUND:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product {product_id} not found.")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching product details: {e.response.text}")
            finally:
                product_detail_call_duration = time.time() - product_detail_call_start
                PRODUCT_SERVICE_CALL_TOTAL.labels(app_name=APP_NAME, target_endpoint=product_detail_url, method="GET", status_code=product_detail_call_status).inc()
                PRODUCT_SERVICE_CALL_DURATION.labels(app_name=APP_NAME, target_endpoint=product_detail_url, method="GET", status_code=product_detail_call_status).observe(product_detail_call_duration)
            
            # --- Check stock and deduct (PATCH stock) ---
            deduct_stock_url = f"{PRODUCT_SERVICE_URL}/products/{product_id}/deduct-stock"
            deduct_stock_call_start = time.time()
            deduct_stock_call_status = "unknown"

            try:
                # Check for insufficient stock before attempting to deduct
                if product_data["stock_quantity"] < quantity:
                    logger.warning(
                        f"Order Service: Insufficient stock for product {product_data['name']} (ID: {product_id}). Requested {quantity}, available {product_data['stock_quantity']}."
                    )
                    order_overall_success = False # Mark order as failed due to stock
                    deduct_stock_call_status = "insufficient_stock"
                    # We still record the failed deduction attempt if an explicit error is raised below
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock for product '{product_data['name']}'. Only {product_data['stock_quantity']} available.",
                    )

                # Synchronous PATCH call to Product Service to deduct stock
                response = await client.patch(
                    deduct_stock_url,
                    json={"quantity_to_deduct": quantity}, # Ensure this matches Product Service schema
                    timeout=5,  # Set a timeout for the external API call
                )
                response.raise_for_status()  # Raise an exception for 4xx/5xx responses
                deduct_stock_call_status = str(response.status_code)

                logger.info(
                    f"Order Service: Stock deduction successful for product {product_id}."
                )
                successfully_deducted_items.append(item)
                ORDER_ITEM_COUNT.labels(app_name=APP_NAME, product_id=product_id).inc(quantity)

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
                order_overall_success = False
                deduct_stock_call_status = str(e.response.status_code)
                # Rollback any previously successful deductions in case of failure
                await _rollback_stock_deductions(client, successfully_deducted_items)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,  # Or appropriate status
                    detail=f"Failed to deduct stock for product {product_id}: {error_detail}",
                )
            except httpx.RequestError as e:
                # Handle network errors (e.g., Product Service is down)
                logger.critical(
                    f"Order Service: Network error communicating with Product Service for product {product_id} during deduction: {e}"
                )
                order_overall_success = False
                deduct_stock_call_status = "network_error"
                await _rollback_stock_deductions(client, successfully_deducted_items)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Product Service is currently unavailable for stock deduction. Please try again later. Error: {e}",
                )
            except Exception as e:
                # Catch any other unexpected errors during deduction
                logger.error(
                    f"Order Service: An unexpected error occurred during stock deduction for product {product_id}: {e}",
                    exc_info=True,
                )
                order_overall_success = False
                deduct_stock_call_status = "internal_error"
                await _rollback_stock_deductions(client, successfully_deducted_items)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred during order creation: {e}",
                )
            finally:
                # Record metrics for the stock deduction call
                deduct_stock_call_duration = time.time() - deduct_stock_call_start
                PRODUCT_SERVICE_CALL_TOTAL.labels(app_name=APP_NAME, target_endpoint=deduct_stock_url, method="PATCH", status_code=deduct_stock_call_status).inc()
                PRODUCT_SERVICE_CALL_DURATION.labels(app_name=APP_NAME, target_endpoint=deduct_stock_url, method="PATCH", status_code=deduct_stock_call_status).observe(deduct_stock_call_duration)


    # If all stock deductions are successful, proceed with order creation in DB
    logger.info(
        "Order Service: All product stock deductions successful. Proceeding to create order."
    )

    total_amount = sum(
        Decimal(str(item.quantity)) * Decimal(str(item.price_at_purchase))
        for item in successfully_deducted_items # Use successfully deducted items for total amount
    )

    db_order = Order(
        user_id=order.user_id,
        shipping_address=order.shipping_address,
        total_amount=total_amount,
        status="pending",  # Initial status
    )

    db.add(db_order)
    db.flush()  # Use flush to get order_id before committing, needed for order items

    for item in successfully_deducted_items: # Use successfully deducted items
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
        ORDER_CREATION_TOTAL.labels(app_name=APP_NAME, status="success").inc()
        ORDER_TOTAL_AMOUNT.labels(app_name=APP_NAME).observe(float(total_amount)) # Record order total amount
        return db_order
    except Exception as e:
        db.rollback()
        logger.error(
            f"Order Service: Error creating order after successful stock deductions: {e}",
            exc_info=True,
        )
        ORDER_CREATION_TOTAL.labels(app_name=APP_NAME, status="db_error").inc()
        # CRITICAL: If DB commit fails here, you have a mismatch.
        # In a real system, you'd likely need a compensation transaction or alerting.
        # For this example, we log the severe error.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Order created but failed to save to database. Manual intervention required.",
        )


async def _rollback_stock_deductions(client: httpx.AsyncClient, items: List[OrderItem]):
    if not items:
        return

    logger.warning(
        "Order Service: Attempting to rollback stock deductions due to order creation failure or upstream error."
    )
    for item in items:
        product_id = item.product_id
        quantity = item.quantity
        add_stock_url = f"{PRODUCT_SERVICE_URL}/products/{product_id}/add-stock" # Product Service has an explicit add-stock endpoint now

        add_stock_call_start = time.time()
        add_stock_call_status = "unknown"
        try:
            # Call Product Service to add stock back
            response = await client.patch(
                add_stock_url,
                json={"quantity_to_deduct": quantity}, # Use quantity_to_deduct as schema expects
                timeout=5,
            )
            response.raise_for_status()
            logger.info(f"Order Service: Successfully rolled back {quantity} stock for product {product_id}.")
            add_stock_call_status = str(response.status_code)
        except httpx.RequestError as e:
            logger.critical(
                f"Order Service: CRITICAL: Failed to connect to Product Service for stock rollback for product {product_id}: {e}. Manual intervention required!"
            )
            add_stock_call_status = "network_error"
        except httpx.HTTPStatusError as e:
            logger.critical(
                f"Order Service: CRITICAL: Product Service returned error {e.response.status_code} for stock rollback for product {product_id}: {e.response.text}. Manual intervention required!"
            )
            add_stock_call_status = str(e.response.status_code)
        except Exception as e:
            logger.critical(
                f"Order Service: CRITICAL: Unexpected error during stock rollback for product {product_id}: {e}. Manual intervention required!",
                exc_info=True,
            )
            add_stock_call_status = "internal_error"
        finally:
            add_stock_call_duration = time.time() - add_stock_call_start
            PRODUCT_SERVICE_CALL_TOTAL.labels(app_name=APP_NAME, target_endpoint=add_stock_url, method="PATCH", status_code=add_stock_call_status).inc()
            PRODUCT_SERVICE_CALL_DURATION.labels(app_name=APP_NAME, target_endpoint=add_stock_url, method="PATCH", status_code=add_stock_call_status).observe(add_stock_call_duration)


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


@app.patch( # Changed to PATCH as is common for partial updates
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
    logger.info(
        f"Order Service: Updating status for order {order_id} to '{new_status}'"
    )
    db_order = db.query(Order).filter(Order.order_id == order_id).first()
    if not db_order:
        logger.warning(
            f"Order Service: Order with ID {order_id} not found for status update."
        )
        ORDER_STATUS_UPDATE_TOTAL.labels(app_name=APP_NAME, status="not_found").inc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    old_status = db_order.status
    db_order.status = new_status # Assign the new status

    try:
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        logger.info(
            f"Order Service: Order {order_id} status updated to '{new_status}' from '{old_status}'."
        )
        ORDER_STATUS_UPDATE_TOTAL.labels(app_name=APP_NAME, status="success").inc()
        return db_order
    except Exception as e:
        db.rollback()
        logger.error(
            f"Order Service: Error updating status for order {order_id}: {e}",
            exc_info=True,
        )
        ORDER_STATUS_UPDATE_TOTAL.labels(app_name=APP_NAME, status="db_error").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update order status.",
        )


@app.delete(
    "/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an order by ID",
)
async def delete_order(order_id: int, db: Session = Depends(get_db)): # Made async for rollback call
    logger.info(f"Order Service: Attempting to delete order with ID: {order_id}")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # Prepare items for rollback before deleting the order from DB
    items_to_restock = [
        {"product_id": item.product_id, "quantity": item.quantity}
        for item in order.items
    ]

    try:
        db.delete(order)
        db.commit()
        logger.info(f"Order Service: Order (ID: {order_id}) deleted successfully from database.")
    except Exception as e:
        db.rollback()
        logger.error(
            f"Order Service: Error deleting order {order_id} from database: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the order from database.",
        )
    
    # Attempt to restock products after order is deleted from DB
    if items_to_restock:
        logger.info(f"Order Service: Attempting to restock products for deleted order {order_id}.")
        async with httpx.AsyncClient() as client:
            for item_data in items_to_restock:
                product_id = item_data["product_id"]
                quantity = item_data["quantity"]
                add_stock_url = f"{PRODUCT_SERVICE_URL}/products/{product_id}/add-stock"
                
                add_stock_call_start = time.time()
                add_stock_call_status = "unknown"
                try:
                    response = await client.patch(add_stock_url, json={"quantity_to_deduct": quantity}, timeout=5)
                    response.raise_for_status()
                    logger.info(f"Order Service: Successfully restocked {quantity} units for product {product_id}.")
                    add_stock_call_status = str(response.status_code)
                except httpx.RequestError as e:
                    logger.critical(f"Order Service: CRITICAL: Network error during restock for product {product_id}: {e}. Manual intervention required!")
                    add_stock_call_status = "network_error"
                except httpx.HTTPStatusError as e:
                    logger.critical(f"Order Service: CRITICAL: Product Service returned error {e.response.status_code} during restock for product {product_id}: {e.response.text}. Manual intervention required!")
                    add_stock_call_status = str(e.response.status_code)
                except Exception as e:
                    logger.critical(f"Order Service: CRITICAL: Unexpected error during restock for product {product_id}: {e}. Manual intervention required!", exc_info=True)
                    add_stock_call_status = "internal_error"
                finally:
                    add_stock_call_duration = time.time() - add_stock_call_start
                    PRODUCT_SERVICE_CALL_TOTAL.labels(app_name=APP_NAME, target_endpoint=add_stock_url, method="PATCH", status_code=add_stock_call_status).inc()
                    PRODUCT_SERVICE_CALL_DURATION.labels(app_name=APP_NAME, target_endpoint=add_stock_url, method="PATCH", status_code=add_stock_call_status).observe(add_stock_call_duration)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(
    "/orders/{order_id}/items",
    response_model=List[OrderItemResponse],
    summary="Retrieve all items for a specific order",
)
def get_order_items(order_id: int, db: Session = Depends(get_db)):
    logger.info(f"Order Service: Fetching items for order ID: {order_id}")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        logger.warning(
            f"Order Service: Order with ID {order_id} not found when fetching items."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    logger.info(
        f"Order Service: Retrieved {len(order.items)} items for order {order_id}."
    )
    return order.items
