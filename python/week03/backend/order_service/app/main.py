# backend/order_service/app/main.py

"""
Order Service - Core API Endpoints

This service manages customer orders, handling their creation, retrieval,
updates, and deletion. A key feature is its synchronous interaction with
the Product Service to perform stock checks and updates, ensuring inventory
accuracy for products involved in orders.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from db import engine, Base, get_db
from models import Order
from schemas import OrderCreate, OrderUpdate, OrderResponse

import requests
import os
import logging

from dotenv import load_dotenv

# --- Environment Variable Loading ---
load_dotenv()

# --- Configuration ---
# Configure logging for the application.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Get a logger instance for this module

# Retrieve the URL for the Product Service from environment variables.
# Default to localhost:8000 for local development.
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8000")


Base.metadata.create_all(bind=engine)

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

# --- Utility Functions ---
async def adjust_product_stock(product_id: int, delta: int):
    """
    Adjusts the stock quantity of a product via the Product Service API.

    This function performs a synchronous HTTP request to the Product Service
    to get the current stock and then update it.

    Args:
        product_id (int): The ID of the product whose stock needs adjustment.
        delta (int): The amount to change the stock by (negative for decrease, positive for increase).

    Raises:
        HTTPException: If the Product Service is unavailable, product not found,
                        or stock update fails/results in insufficient stock.
    """
    logger.info(f"Attempting to adjust stock for product ID {product_id} by {delta}.")
    try:
        product_resp = requests.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}")
        product_resp.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        product_data = product_resp.json()
        current_stock = product_data.get("stock_quantity")
        
        if current_stock is None:
            logger.error(f"Product ID {product_id} found but 'stock_quantity' is missing in Product Service response: {product_data}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Product stock information missing from Product Service response."
            )

        new_stock = current_stock + delta
        
        # Step 2: Validate new stock quantity
        if new_stock < 0:
            logger.warning(f"Not enough stock for product ID {product_id}. Current: {current_stock}, Delta: {delta}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough stock for product ID {product_id}. Available: {current_stock}, Requested change: {delta}."
            )

        # Step 3: Update product stock via Product Service
        update_resp = requests.put(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}/stock",
            params={"stock_quantity": new_stock} # Use params for query parameters
        )
        update_resp.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        logger.info(f"Successfully adjusted stock for product ID {product_id} to {new_stock}.")

    except requests.exceptions.ConnectionError as e:
        logger.critical(f"Product Service is unreachable at {PRODUCT_SERVICE_URL}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Product Service is currently unavailable. Please try again later. Error: {e}"
        )
    except requests.exceptions.Timeout:
        logger.error(f"Product Service request timed out for product ID {product_id}.")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Product Service request timed out."
        )
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = e.response.json().get("detail", str(e)) if e.response and e.response.content else str(e)
        
        logger.error(f"Failed to communicate with Product Service for product ID {product_id}: Status {status_code}, Detail: {detail}", exc_info=True)
        # Pass through specific errors from Product Service if relevant
        if status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found in Product Service.")
        if status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid stock update request for product service: {detail}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update stock in Product Service: {detail}"
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during stock adjustment for product ID {product_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during stock adjustment: {e}"
        )

# --- API Endpoints ---
@app.post(
    "/orders/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
    description="""
    Creates a new order record. This operation synchronously calls the Product Service
    to decrease the stock quantity of the ordered product. If there's insufficient
    stock or if the Product Service is unreachable, the order creation will fail.
    """
)
async def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """
    Handles the creation of a new order.
    """
    logger.info(f"Received request to create order for product_id: {order.product_id}, quantity: {order.quantity}")
    
    try:
        # Step 1: Adjust product stock (decrease quantity)
        await adjust_product_stock(order.product_id, -order.quantity)
        
        # Step 2: Create the order record in the database
        db_order = Order(
            product_id=order.product_id,
            customer_name=order.customer_name,
            quantity=order.quantity
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        logger.info(f"Order {db_order.order_id} created successfully for product ID {order.product_id}.")
        return db_order
    except HTTPException:
        # Re-raise HTTPExceptions raised by adjust_product_stock
        raise
    except SQLAlchemyError as e:
        db.rollback() # Ensure rollback on database error
        logger.error(f"Database error while creating order for product ID {order.product_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while creating the order."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during order creation for product ID {order.product_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@app.get(
    "/orders/",
    response_model=list[OrderResponse],
    summary="List all orders",
    description="Retrieves a list of all orders currently in the system."
)
def list_orders(db: Session = Depends(get_db)):
    """
    Retrieves all orders from the database.
    """
    logger.info("Fetching all orders.")
    orders = db.query(Order).all()
    logger.info(f"Retrieved {len(orders)} orders.")
    return orders

@app.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
    description="Retrieves details of a single order using its unique ID."
)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a specific order by its ID.
    """
    logger.info(f"Fetching order with ID: {order_id}")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        logger.warning(f"Order with ID {order_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    logger.info(f"Successfully retrieved order {order_id}.")
    return order

@app.put(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Update an existing order",
    description="""
    Updates an existing order's details. This operation handles stock adjustments
    with the Product Service based on changes in order quantity.
    If the order quantity decreases, stock is returned; if it increases, stock is consumed.
    """
)
async def update_order(order_id: int, update: OrderUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing order.

    Adjusts product stock based on the change in order quantity.
    """
    logger.info(f"Received request to update order ID: {order_id}")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        logger.warning(f"Attempted to update non-existent order with ID {order_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    prev_qty = order.quantity
    updated_fields = 0

    if update.quantity is not None:
        delta = update.quantity - prev_qty # Calculate change in quantity
        if delta != 0: # Only adjust stock if quantity actually changed
            logger.info(f"Order {order_id}: Quantity changed from {prev_qty} to {update.quantity}. Adjusting stock by {-delta}.")
            try:
                await adjust_product_stock(order.product_id, -delta) # Negative delta for increase in order quantity
                order.quantity = update.quantity
                updated_fields += 1
            except HTTPException:
                # Re-raise HTTPExceptions from stock adjustment
                raise
            except Exception as e:
                logger.error(f"Error during stock adjustment for order {order_id} update: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to adjust product stock during order update: {e}"
                )
        else:
            logger.info(f"Order {order_id}: Quantity remains unchanged at {prev_qty}.")

    if update.customer_name is not None: # Use is not None for Optional fields
        if order.customer_name != update.customer_name: # Only update if different
            order.customer_name = update.customer_name
            updated_fields += 1
            logger.info(f"Order {order_id}: Customer name updated to '{update.customer_name}'.")
        else:
            logger.info(f"Order {order_id}: Customer name remains unchanged.")

    if updated_fields > 0:
        try:
            db.commit()
            db.refresh(order)
            logger.info(f"Order {order_id} updated successfully. Fields changed: {updated_fields}.")
        except SQLAlchemyError as e:
            db.rollback() # Rollback changes in case of DB error
            logger.error(f"Database error while updating order {order_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while updating the order."
            )
    else:
        logger.info(f"No valid fields provided for update for order {order_id}. No database changes committed.")
    
    return order

@app.delete(
    "/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an order",
    description="""
    Deletes an order record. Upon deletion, the stock quantity of the associated
    product in the Product Service is increased by the ordered quantity,
    effectively returning the stock.
    """
)
async def delete_order(order_id: int, db: Session = Depends(get_db)):
    """
    Deletes an order by its ID, returning product stock to the Product Service.
    """
    logger.info(f"Received request to delete order ID: {order_id}")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        logger.warning(f"Attempted to delete non-existent order with ID {order_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    try:
        # Step 1: Return product stock to the Product Service
        # Increase stock by the quantity of the deleted order
        await adjust_product_stock(order.product_id, order.quantity)
        
        # Step 2: Delete the order record from the database
        db.delete(order)
        db.commit()
        logger.info(f"Order {order_id} deleted successfully and {order.quantity} units of product {order.product_id} returned to stock.")
    except HTTPException:
        # Re-raise HTTPExceptions from adjust_product_stock
        raise
    except SQLAlchemyError as e:
        db.rollback() # Rollback changes in case of DB error
        logger.error(f"Database error while deleting order {order_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while deleting the order."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during order deletion for ID {order_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )
    
    # For a 204 No Content response, typically no body is returned.
    return {"detail": "Order deleted successfully"}
