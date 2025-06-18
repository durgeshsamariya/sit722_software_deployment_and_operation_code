# week05/example-1/backend/customer_service/app/schemas.py

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    email: EmailStr = Field(..., description="Unique email address of the customer.")
    first_name: str = Field(
        ..., min_length=1, max_length=255, description="First name of the customer."
    )
    last_name: str = Field(
        ..., min_length=1, max_length=255, description="Last name of the customer."
    )
    phone_number: Optional[str] = Field(
        None, max_length=50, description="Customer's phone number."
    )
    shipping_address: Optional[str] = Field(
        None, max_length=1000, description="Customer's primary shipping address."
    )


class CustomerCreate(CustomerBase):
    password: str = Field(..., min_length=8, description="Customer's password.")


# Schema for updating an existing Customer (all fields optional for partial update)
class CustomerUpdate(BaseModel):
    email: Optional[EmailStr] = Field(
        None, description="Unique email address of the customer."
    )
    first_name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="First name of the customer."
    )
    last_name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Last name of the customer."
    )
    phone_number: Optional[str] = Field(
        None, max_length=50, description="Customer's phone number."
    )
    shipping_address: Optional[str] = Field(
        None, max_length=1000, description="Customer's primary shipping address."
    )


# Schema for responding with Customer data
class CustomerResponse(CustomerBase):
    customer_id: int = Field(..., description="Unique ID of the customer.")
    created_at: datetime = Field(
        ..., description="Timestamp of when the customer record was created."
    )
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp of the last update to the customer record."
    )

    model_config = ConfigDict(from_attributes=True)  # Enable ORM mode for Pydantic V2
