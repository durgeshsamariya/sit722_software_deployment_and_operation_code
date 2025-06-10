# week03/example-3/backend/customer_service/app/main.py

"""
FastAPI Customer Service with CRUD operations and password hashing.

This service manages customer data, including creation, retrieval, updates, and deletion.
It's designed to be a dedicated microservice for all customer-related functionalities.
"""

import sys
import logging
import time
from typing import Optional, List

import os

from fastapi import FastAPI, HTTPException, Depends, status, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError

from .db import engine, Base, get_db
from .models import Customer
from .schemas import CustomerCreate, CustomerUpdate, CustomerResponse


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

# --- FastAPI Application Setup ---
app = FastAPI(
    title="Customer Service API",
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

# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():
    """
    Handles application startup events.
    Ensures database tables are created (if not exist) for the Customer Service.
    Includes a retry mechanism for database connection robustness.
    """
    max_retries = 10
    retry_delay_seconds = 5
    for i in range(max_retries):
        try:
            logger.info(f"Customer Service: Attempting to connect to PostgreSQL and create tables (attempt {i+1}/{max_retries})...")
            Base.metadata.create_all(bind=engine)
            logger.info("Customer Service: Successfully connected to PostgreSQL and ensured tables exist.")
            break # Exit loop if successful
        except OperationalError as e:
            logger.warning(f"Customer Service: Failed to connect to PostgreSQL: {e}")
            if i < max_retries - 1:
                logger.info(f"Customer Service: Retrying in {retry_delay_seconds} seconds...")
                time.sleep(retry_delay_seconds)
            else:
                logger.critical(f"Customer Service: Failed to connect to PostgreSQL after {max_retries} attempts. Exiting application.")
                sys.exit(1) # Critical failure: exit if DB connection is unavailable
        except Exception as e:
            logger.critical(f"Customer Service: An unexpected error occurred during database startup: {e}", exc_info=True)
            sys.exit(1)


# --- Root Endpoint ---
@app.get("/", status_code=status.HTTP_200_OK, summary="Root endpoint")
async def read_root():
    """
    Returns a welcome message for the Customer Service.
    """
    return {"message": "Welcome to the Customer Service!"}


# --- Health Check Endpoint ---
@app.get("/health", status_code=status.HTTP_200_OK, summary="Health check endpoint")
async def health_check():
    """
    A simple health check endpoint to verify the service is running.
    Returns 200 OK if the service is alive.
    """
    return {"status": "ok", "service": "customer-service"}


# --- CRUD Endpoints for Customers ---

@app.post(
    "/customers/",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer"
)
async def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db)
):
    """
    Creates a new customer in the database.
    Raises 400 if email already exists.
    """
    logger.info(f"Customer Service: Creating customer with email: {customer.email}")
    # NO PASSWORD HASHING
    # In a real application, ALWAYS hash and salt passwords before storing.
    db_customer = Customer(
        email=customer.email,
        password_hash=customer.password, # Storing raw password for simplicity in this example
        first_name=customer.first_name,
        last_name=customer.last_name,
        phone_number=customer.phone_number,
        shipping_address=customer.shipping_address
    )

    try:
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        logger.info(f"Customer Service: Customer '{db_customer.email}' (ID: {db_customer.customer_id}) created successfully.")
        return db_customer
    except IntegrityError:
        db.rollback()
        logger.warning(f"Customer Service: Attempted to create customer with existing email: {customer.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Customer Service: Error creating customer: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create customer.")

@app.get(
    "/customers/",
    response_model=List[CustomerResponse],
    summary="Retrieve a list of all customers"
)
def list_customers(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=255)
):
    """
    Lists customers with optional pagination and search by name or email.
    """
    logger.info(f"Customer Service: Listing customers with skip={skip}, limit={limit}, search='{search}'")
    query = db.query(Customer)
    if search:
        search_pattern = f"%{search}%"
        logger.info(f"Customer Service: Applying search filter for term: {search}")
        query = query.filter(
            (Customer.first_name.ilike(search_pattern)) |
            (Customer.last_name.ilike(search_pattern)) |
            (Customer.email.ilike(search_pattern))
        )
    customers = query.offset(skip).limit(limit).all()

    logger.info(f"Customer Service: Retrieved {len(customers)} customers (skip={skip}, limit={limit}).")
    return customers


@app.get("/customers/{customer_id}", response_model=CustomerResponse, summary="Retrieve a single customer by ID")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """
    Retrieves details for a specific customer using their unique ID.
    """
    logger.info(f"Customer Service: Fetching customer with ID: {customer_id}")
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        logger.warning(f"Customer Service: Customer with ID {customer_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    logger.info(f"Customer Service: Retrieved customer with ID {customer_id}. Email: {customer.email}")
    return customer


@app.put("/customers/{customer_id}", response_model=CustomerResponse, summary="Update an existing customer by ID")
async def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates an existing customer's details. Only provided fields will be updated.
    Does not allow password update via this endpoint for security (use a dedicated endpoint if needed).
    """
    logger.info(f"Customer Service: Updating customer with ID: {customer_id} with data: {customer_data.model_dump(exclude_unset=True)}")
    db_customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not db_customer:
        logger.warning(f"Customer Service: Attempted to update non-existent customer with ID {customer_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    update_data = customer_data.model_dump(exclude_unset=True)
    
    # Prevent direct update of password_hash via this endpoint
    if 'password' in update_data: # If 'password' was somehow passed, remove it
        logger.warning(f"Customer Service: Attempted password update via general /customers/{{id}} endpoint for customer {customer_id}. This is disallowed.")
        del update_data['password'] # Remove password if present

    for key, value in update_data.items():
        setattr(db_customer, key, value)
    
    try:
        db.add(db_customer) # Mark for update
        db.commit()
        db.refresh(db_customer)
        logger.info(f"Customer Service: Customer {customer_id} updated successfully.")
        return db_customer
    except IntegrityError:
        db.rollback()
        # This could happen if a user tries to change email to one that already exists
        logger.warning(f"Customer Service: Attempted to update customer {customer_id} to an existing email.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Updated email already registered by another customer."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Customer Service: Error updating customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update customer.")


@app.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a customer by ID")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """
    Deletes a customer record from the database.
    """
    logger.info(f"Customer Service: Attempting to delete customer with ID: {customer_id}")
    customer = db.query(Customer).filter(Customer.customer_id == customer_id).first()
    if not customer:
        logger.warning(f"Customer Service: Attempted to delete non-existent customer with ID {customer_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    try:
        db.delete(customer)
        db.commit()
        logger.info(f"Customer Service: Customer {customer_id} deleted successfully. Email: {customer.email}")
    except Exception as e:
        db.rollback()
        logger.error(f"Customer Service: Error deleting customer {customer_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the customer."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)