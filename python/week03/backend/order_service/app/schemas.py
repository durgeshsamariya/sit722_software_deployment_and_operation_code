# backend/order_service/app/schemas.py

"""
Pydantic schemas for the Order Service API.

These schemas define the data structures used for validating incoming requests
(e.g., creating or updating orders) and for serializing outgoing responses
(e.g., returning order details). They ensure data integrity and provide
clear API contracts for the Order microservice.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="ID of the product ordered")
    quantity: int = Field(..., gt=0, description="Quantity of the product ordered")
    customer_name: str = Field(..., min_length=1, max_length=255, description="Customer's name")


class OrderUpdate(BaseModel):
    quantity: int = Field(None, gt=0, description="New quantity for the order")
    customer_name: str = Field(None, min_length=1, max_length=255, description="Customer's name")


class OrderResponse(OrderCreate):
    order_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
