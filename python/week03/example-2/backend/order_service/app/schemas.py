# week03/example-1/backend/order_service/app/schemas.py

"""
Pydantic schemas for the Order Service API.

These schemas define the data structures used for validating incoming requests
(e.g., creating or updating orders) and for serializing outgoing responses
(e.g., returning order details). They ensure data integrity and provide
clear API contracts for the Order microservice.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

# --- OrderItem Schemas ---

class OrderItemBase(BaseModel):
    """
    Base schema for an individual item within an order.
    Used for common fields across creation and response.
    """
    product_id: int = Field(..., ge=1, description="ID of the product from the Product Service.")
    quantity: int = Field(..., ge=1, description="Quantity of the product ordered.")
    price_at_purchase: float = Field(..., gt=0, description="Price of the product at the time of purchase.")

class OrderItemCreate(OrderItemBase):
    """
    Schema for creating an order item.
    Note: item_total will be calculated by the service, not provided by client.
    """
    pass

class OrderItemResponse(OrderItemBase):
    """
    Schema for responding with an order item.
    Includes auto-generated fields like order_item_id and timestamps.
    """
    order_item_id: int
    order_id: int # The ID of the parent order
    item_total: float # Calculated total for this specific item
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode for Pydantic V2

# --- Order Schemas ---

class OrderBase(BaseModel):
    """
    Base schema for an order.
    Used for common fields across creation and response.
    """
    user_id: int = Field(..., ge=1, description="ID of the user placing the order.")
    shipping_address: Optional[str] = Field(None, max_length=1000, description="Shipping address for the order.")
    status: Optional[str] = Field("pending", max_length=50, description="Current status of the order (e.g., pending, processing, shipped).")

class OrderCreate(OrderBase):
    """
    Schema for creating a new order.
    Requires a list of items to be purchased.
    Total amount will be calculated by the service.
    """
    items: List[OrderItemCreate] = Field(..., min_length=1, description="List of items in the order.")

class OrderUpdate(OrderBase):
    """
    Schema for updating an existing order.
    All fields are optional for partial updates.
    """
    user_id: Optional[int] = Field(None, ge=1)
    # Status can be updated
    # items are generally not updated directly via PUT for an order;
    # rather, new orders or cancellations would handle changes.
    # total_amount is calculated, not directly updated.

class OrderResponse(OrderBase):
    """
    Schema for responding with order details.
    Includes auto-generated fields, calculated total, and a list of order items.
    """
    order_id: int
    order_date: datetime
    total_amount: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse] = [] # Nested items for detailed order response

    model_config = ConfigDict(from_attributes=True) # Enable ORM mode for Pydantic V2