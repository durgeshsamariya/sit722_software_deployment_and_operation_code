# week03/example-3/backend/customer_service/app/schemas.py

"""
Pydantic schemas for the Order Service API.

These schemas define the data structures used for validating incoming requests
(e.g., creating or updating orders) and for serializing outgoing responses
(e.g., returning order details). They ensure data integrity and provide
clear API contracts for the Order microservice.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, EmailStr

# Base schema for a Customer (common fields)
class CustomerBase(BaseModel):
    email: EmailStr = Field(..., description="Unique email address of the customer.")
    first_name: str = Field(..., min_length=1, max_length=255, description="First name of the customer.")
    last_name: str = Field(..., min_length=1, max_length=255, description="Last name of the customer.")
    phone_number: Optional[str] = Field(None, max_length=50, description="Customer's phone number.")
    shipping_address: Optional[str] = Field(None, max_length=1000, description="Customer's primary shipping address.")

# Schema for creating a new Customer
class CustomerCreate(CustomerBase):
    # Password is required for creation
    password: str = Field(..., min_length=8, description="Customer's password.")

# Schema for updating an existing Customer (all fields optional for partial update)
class CustomerUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, description="Unique email address of the customer.")
    # Password can be updated separately if needed, but not part of a general update
    # password: Optional[str] = Field(None, min_length=8, description="New password for the customer.")
    first_name: Optional[str] = Field(None, min_length=1, max_length=255, description="First name of the customer.")
    last_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Last name of the customer.")
    phone_number: Optional[str] = Field(None, max_length=50, description="Customer's phone number.")
    shipping_address: Optional[str] = Field(None, max_length=1000, description="Customer's primary shipping address.")

# Schema for responding with Customer data
class CustomerResponse(CustomerBase):
    customer_id: int = Field(..., description="Unique ID of the customer.")
    created_at: datetime = Field(..., description="Timestamp of when the customer record was created.")
    updated_at: Optional[datetime] = Field(None, description="Timestamp of the last update to the customer record.")

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode for Pydantic V2
